import cv2
from ultralytics import YOLO
from collections import deque, Counter

# 1. Cargar el modelo
model = YOLO("best.pt")

# 2. Configuración de precisión y suavizado
CONF_THRESHOLD = 0.50   # Muestra la letra solo si la certeza es >= 50%
BUFFER_SIZE = 7         # Analiza los últimos 7 fotogramas para evitar parpadeos
historial_predicciones = deque(maxlen=BUFFER_SIZE)

# 3. Conectar la cámara
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    cap = cv2.VideoCapture(1)

print("✅ Cámara activada con filtro de precisión. Presiona 'q' para salir.")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret or frame is None:
        break

    # Efecto espejo
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # Recorte centrado para la mano (300x300 px)
    box_size = 300
    x1, y1 = max(0, int((w - box_size) / 2)), max(0, int((h - box_size) / 2))
    x2, y2 = min(w, x1 + box_size), min(h, y1 + box_size)

    hand_roi = frame[y1:y2, x1:x2]

    # Convertir de BGR (OpenCV) a RGB (YOLO)
    hand_roi_rgb = cv2.cvtColor(hand_roi, cv2.COLOR_BGR2RGB)

    # Inferencia con resolución estándar de clasificación (224x224)
    results = model.predict(hand_roi_rgb, verbose=False, imgsz=224)

    letra_detectada = None
    conf_detectada = 0.0

    if results and len(results) > 0:
        res = results[0]
        # Clasificación
        if hasattr(res, 'probs') and res.probs is not None:
            top1_idx = int(res.probs.top1)
            conf_detectada = float(res.probs.top1conf)
            if conf_detectada >= CONF_THRESHOLD:
                letra_detectada = res.names[top1_idx]
        # Detección
        elif hasattr(res, 'boxes') and res.boxes is not None and len(res.boxes) > 0:
            top_box = res.boxes[0]
            cls_id = int(top_box.cls[0])
            conf_detectada = float(top_box.conf[0])
            if conf_detectada >= CONF_THRESHOLD:
                letra_detectada = res.names[cls_id]

    # Guardar en el historial para suavizar la respuesta
    if letra_detectada:
        historial_predicciones.append(letra_detectada)
    else:
        historial_predicciones.append("Inseguro")

    # Voto mayoritario en el historial reciente
    conteo = Counter(historial_predicciones)
    letra_estable, repeticiones = conteo.most_common(1)[0]

    # Validar si la predicción es estable en más de la mitad del buffer
    if letra_estable != "Inseguro" and (repeticiones / len(historial_predicciones)) >= 0.5:
        label_text = f"Letra LSC: {letra_estable} ({conf_detectada * 100:.1f}%)"
        color_borde = (0, 255, 0) # Verde si es confiable
    else:
        label_text = "Acomoda la mano / Realiza la seña..."
        color_borde = (0, 165, 255) # Naranja si hay duda

    # Dibujar cuadro de enfoque
    cv2.rectangle(frame, (x1, y1), (x2, y2), color_borde, 2)
    cv2.putText(frame, "Posa tu mano aqui", (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_borde, 2)

    # Dibujar barra superior
    cv2.rectangle(frame, (10, 10), (520, 60), (0, 0, 0), -1)
    cv2.putText(frame, label_text, (20, 45), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color_borde, 2)

    cv2.imshow("Reconocimiento LSC en vivo - YOLO", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()