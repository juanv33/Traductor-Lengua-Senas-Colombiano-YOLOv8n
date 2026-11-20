"""Manos que hablan · servidor Flask + YOLO. Ejecuta: python app.py"""
import base64, io
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from PIL import Image
from ultralytics import YOLO

BASE = Path(__file__).parent
ALPHABET = list("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")
IMG_SIZE = 256  

app = Flask(__name__)

# Se carga UNA sola vez al iniciar el servidor (no en cada petición)
MODEL = YOLO(str(BASE / "model" / "best.pt"))
print("Clases del modelo:", MODEL.names)

# Letras con imagen: se detectan solas leyendo static/alfabeto  ->  {"A": "A.jpg", ...}
AVAILABLE = {p.stem: p.name for p in sorted((BASE / "static/alfabeto").iterdir())}


@app.get("/")
def index():
    return render_template("index.html", alphabet=ALPHABET, available=AVAILABLE, demo=False)


@app.post("/api/predict")
def predict():
    try:
        raw = base64.b64decode(request.get_json()["image"].split(",", 1)[1])
        img = Image.open(io.BytesIO(raw)).convert("RGB")  # PIL ya viene en RGB, YOLO lo acepta directo
    except Exception:
        return jsonify(error="Imagen inválida"), 400

    res = MODEL.predict(img, imgsz=IMG_SIZE, verbose=False)[0]

    # Modelo de CLASIFICACIÓN (yolov8n-cls): usa res.probs
    if res.probs is not None:
        letter, conf = res.names[int(res.probs.top1)], float(res.probs.top1conf)
        print(f"Predicción: {letter} ({conf:.0%})")  # para depurar: se ve en la terminal
        return jsonify(letter=letter, confidence=conf)

    # Por si algún día usas un modelo de DETECCIÓN
    if res.boxes is not None and len(res.boxes) > 0:
        best = max(res.boxes, key=lambda b: float(b.conf[0]))
        return jsonify(letter=res.names[int(best.cls[0])], confidence=float(best.conf[0]))

    return jsonify(letter=None, confidence=0.0)


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)  # use_reloader=False evita cargar el modelo dos veces