# Cadora.pro

Convierte planos arquitectónicos (PDF / PNG / JPG / TIFF) en archivos CAD editables
(DXF / DWG). Detección de muros, puertas y ventanas con OpenCV, OCR con Tesseract,
editor CAD en línea y exportación DXF/DWG.

## Arquitectura

| Capa      | Tecnología                                                    |
|-----------|---------------------------------------------------------------|
| Frontend  | Next.js 15 + React 19 + Tailwind + shadcn/ui (output standalone) |
| Backend   | FastAPI + SQLAlchemy 2 (asyncio) + Postgres 16                  |
| Detección | OpenCV (muros/puertas/ventanas) + Tesseract OCR (es)            |
| CAD       | ezdxf (DXF) + libredwg (DWG)                                   |
| Pagos     | Paddle (webhooks firmados)                                     |
| Storage   | Supabase Storage con fallback a disco                          |
| Deploy    | Docker Compose + nginx + Certbot en un VPS                     |

```
nginx ── /api/v1/* ──> api (uvicorn x4)
   └──── /          ─> frontend (Next standalone)
                       api ──> db (Postgres) / supabase / paddle
                       api + detection worker in-process (FOR UPDATE SKIP LOCKED)
```

## Estructura

```
backend/   API, detección IA, OCR, CAD, auth, pagos, worker, tests
frontend/  Aplicación web Next.js
nginx/     Configuración de proxy, TLS, rate limit y health
backup/    Script + contenedor de backup con copia offsite y GPG
deploy.sh  Despliegue remoto (pull + build + health checks)
docker-compose.yml
```

## Desarrollo local

Asegurate de tener las dependencias de detección (OpenCV, Tesseract, poppler)
y Python 3.12+.

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e ".[dev]"
cp .env.example .env            # ajustá DATABASE_URL y secretos
alembic upgrade head
make dev                        # uvicorn en http://localhost:8000
make test                       # pytest
make lint                       # ruff
make typecheck                  # mypy

# Frontend (en otra terminal)
cd frontend
npm install
cp .env.example .env            # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

## Despliegue

El deploy se ejecuta desde el VPS en `/opt/cadora`:

```bash
./deploy.sh main                 # pull + backup de DB + build + health checks
```

`deploy.sh` hace snapshot de la base antes de migrar, reconstruye los contenedores
y verifica `/` y `/api/v1/readyz`. También existe CI (lint/typecheck/tests) y un
workflow de despliegue automático en `.github/workflows/`.

Variables de entorno requeridas en producción (ver `backend/.env.production.example`
y `.env.example` en la raíz): `DATABASE_URL`, `JWT_SECRET`, `ENVIRONMENT=production`,
`POSTGRES_PASSWORD`, credenciales de Supabase, `SMTP_*` (emails), `PADDLE_*` (pagos)
y opcionalmente `SENTRY_DSN` / `GA_ID`.

## Monitoreo

- Sentry (backend + frontend) registra errores y trazas.
- Health/readiness: `GET /api/v1/health` (DB+storage) y `GET /api/v1/readyz`
  (DB, devuelve 503 si no está listo) — también usado por los healthchecks de
  los contenedores.
- Para detección de caídas externa, configurá un uptime check apuntando a
  `https://cadora.pro/api/v1/readyz` (p. ej. UptimeRobot / Better Stack) con
  alerta por email/Slack.

## Entregabilidad de email (to-do en DNS)

La app envía códigos de verificación/reset vía Resend desde `@cadora.pro`. Para
que esos mails no caigan en spam, hay que configurar en el registrar (Namecheap):

- **DKIM**: agregar el registro TXT `*._domainkey` que muestra el panel de
  Resend para el dominio.
- **SPF**: incluir a Resend en el SPF actual. Ej. para Resend se usa
  `v=spf1 include:spf.efwd.registrar-servers.com include:amazonses.com ~all`
  (confirmar el `include` que indique Resend). El SPF actual solo autoriza el
  forwarding del registrar, no a Resend.
- **DMARC**: crear `_dmarc.cadora.pro` TXT `v=DMARC1; p=none; rua=mailto:...`
  y luego subir la política a `p=quarantine` cuando las tasas bajen.
- MX: el actual es solo forwarding de Namecheap; si no se usan buzones propios
  está bien, pero no es un servidor de email real.

## Mantenimiento

- **Backups**: cron diario (03:00) vía `backup/backup.sh`: `pg_dump` verificado,
  encriptación AES-256 con GPG opcional y subida offsite a Supabase.
- **Migraciones**: Alembic (`make migration message="..."` en backend).
- **Workers**: la detección corre en un worker asíncrono in-process con reclaim
  de jobs estancados (heartbeat). Para alto caudal, migrar a una cola/worker dedicado.

## Testing de detección

El harness `backend/scripts/validate_detection.py` renderiza planos sintéticos con
ground truth y reporta precisión/recall de muros, puertas y ventanas. Los tests
`backend/tests/unit/test_detection_stress.py` degradan esos planos (blur/JPG/ruido/
rotación) para imitar imágenes de IA y evitan regresiones.
