# Conjunto de datos real etiquetado para evaluar el motor de precisión

Este directorio debe contener imágenes de planos arquitectónicos reales
(AI-generated, escaneados, fotos) con sus correspondientes anotaciones
manuales (ground truth) en formato JSON.

## Estructura esperada

```
dataset/
├── plano_a.png          # imagen del plano (PNG o JPG)
├── plano_a.json         # ground truth correspondiente
├── plano_b.png
├── plano_b.json
└── ...
```

## Formato del archivo JSON de ground truth

```json
{
  "walls": [
    {"x1": 100.0, "y1": 200.0, "x2": 800.0, "y2": 200.0},
    {"x1": 200.0, "y1": 100.0, "x2": 200.0, "y2": 700.0}
  ],
  "doors": [
    {"x": 300.0, "y": 200.0, "width": 80.0, "type": "single"}
  ],
  "windows": [
    {"x": 500.0, "y": 200.0, "width": 100.0, "type": "sliding"}
  ]
}
```

- **walls**: coordenadas en píxeles del centro de la línea del muro (no
  el borde). La imagen de referencia es la imagen original.
- **doors**: coordenadas del centro del hueco de la puerta, ancho del
  hueco en píxeles y tipo (`single`, `double`, `sliding`).
- **windows**: coordenadas del centro del hueco, ancho en píxeles y
  tipo (`sliding`, `fixed`, `casement`).

## Cómo ejecutar la evaluación

```bash
python -m scripts.evaluate_dataset /ruta/al/dataset
```

Esto corre el pipeline de detección sobre cada imagen, calcula
precisión/recall de muros (matching por centro ±12px + solape >50%),
IoU píxel-real de cobertura de muros, IoU de posición de puertas/ventanas
y exactitud de tipo.

## Por qué es crítico este dataset

Los tests existentes (`test_detection_stress.py`, `test_detection_precision.py`)
miden precisión sobre planos **sintéticos** — perfectos, sin texturas,
sin muebles reales, sin sombras, sin curvas complejas. El dataset real
es lo único que puede demostrar que el motor funciona en producción
y es el verdadero diferenciador de mercado.
