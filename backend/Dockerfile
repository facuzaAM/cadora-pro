FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    poppler-utils \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN wget -q https://github.com/LibreDWG/libredwg/releases/download/0.13.4/libredwg-0.13.4.tar.xz -O /tmp/libredwg.tar.xz \
    && tar -xf /tmp/libredwg.tar.xz -C /tmp \
    && cd /tmp/libredwg-0.13.4 \
    && ./configure --prefix=/usr/local --disable-bindings --disable-python \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/libredwg*

FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/dxf2dwg /usr/local/bin/dxf2dwg
COPY --from=builder /usr/local/lib/libredwg* /usr/local/lib/

RUN ldconfig

RUN groupadd -r plan2cad && useradd -r -g plan2cad -d /app plan2cad

COPY --chown=plan2cad:plan2cad . .

RUN mkdir -p /app/logs /app/uploads \
    && chown -R plan2cad:plan2cad /app/logs /app/uploads /app/alembic

USER plan2cad

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

ENTRYPOINT ["/app/entrypoint.sh"]
