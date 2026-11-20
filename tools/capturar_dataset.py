"""Captura fotos de tu cámara para mejorar el modelo.
Uso:  python tools/capturar_dataset.py A      (una letra a la vez)
 - ESPACIO: inicia / pausa la captura automática (1 foto cada 0.2 s)
 - q: salir
"""
import sys, time
from pathlib import Path
import cv2

if len(sys.argv) < 2:
    sys.exit("Uso: python tools/capturar_dataset.py A")
letra = sys.argv[1].upper()
carpeta = Path(__file__).resolve().parent.parent / "mis_datos" / letra
carpeta.mkdir(parents=True, exist_ok=True)
n = len(list(carpeta.glob("*.jpg")))

CROP, SIZE, INTERVALO = 0.82, 256, 0.2   # igual que app.js
cap = cv2.VideoCapture(0)
capturando, ultimo = False, 0.0

while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        break
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    lado = int(min(w, h) * CROP)
    x1, y1 = (w - lado) // 2, (h - lado) // 2
    recorte = frame[y1:y1 + lado, x1:x1 + lado]

    if capturando and time.time() - ultimo >= INTERVALO:
        cv2.imwrite(str(carpeta / f"cam_{int(time.time()*1000)}.jpg"), cv2.resize(recorte, (SIZE, SIZE)))
        n += 1
        ultimo = time.time()

    color = (0, 0, 255) if capturando else (0, 255, 0)
    cv2.rectangle(frame, (x1, y1), (x1 + lado, y1 + lado), color, 2)
    estado = "GRABANDO" if capturando else "PAUSA (ESPACIO para grabar)"
    cv2.putText(frame, f"Letra {letra} | fotos: {n} | {estado}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    cv2.imshow("Captura de datos", frame)

    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"):
        break
    if k == 32:
        capturando = not capturando

cap.release()
cv2.destroyAllWindows()
print(f"Total en {carpeta}: {n} fotos")