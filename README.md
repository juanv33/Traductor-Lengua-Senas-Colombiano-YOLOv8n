Traductor de Lengua de Señas Colombiana (LSC) en Tiempo Real
Proyecto universitario que utiliza la arquitectura YOLOv8n-cls para clasificar 22 letras del abecedario de la LSC a través de la cámara web, aislando el fondo mediante una región de interés (ROI).

Archivos del Repositorio
Entrenamiento_YOLO.ipynb: Script de Google Colab detallando la importación del dataset desde Kaggle, partición de datos (80% entrenamiento / 20% validación) y entrenamiento de la red neuronal durante 15 épocas.

best.pt: Archivo con los pesos del modelo final entrenado.

camara.py: Script de Python que utiliza OpenCV para capturar video en tiempo real, dibujar la región de interés y realizar la inferencia.
