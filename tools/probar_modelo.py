"""Diagnóstico: ¿el modelo acierta con las imágenes de referencia (static/alfabeto)?
Ejecuta desde la carpeta del proyecto:  python tools/probar_modelo.py
"""
from pathlib import Path
from PIL import Image, ImageOps
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent.parent
model = YOLO(str(BASE / "model" / "best.pt"))
print("Clases del modelo:", list(model.names.values()), "\n")


def predecir(img):
    r = model.predict(img, imgsz=250, verbose=False)[0]
    return r.names[int(r.probs.top1)], float(r.probs.top1conf)


normal = espejo = total = 0
for f in sorted((BASE / "static" / "alfabeto").glob("*.jpg")):
    real = f.stem
    img = Image.open(f).convert("RGB")
    p1, c1 = predecir(img)
    p2, c2 = predecir(ImageOps.mirror(img))
    normal += p1.upper() == real
    espejo += p2.upper() == real
    total += 1
    print(f"{real}: normal -> {p1} ({c1:.0%}) | espejo -> {p2} ({c2:.0%})")

print(f"\nAciertos normal: {normal}/{total}   |   Aciertos espejo: {espejo}/{total}")