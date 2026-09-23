import mediapipe as mp
import cv2
import mouse
import ctypes
import math
import json
import os
import pyautogui
import subprocess

# ════════════════════════════════════════════════════
#  Carga de configuracion de gestos
# ════════════════════════════════════════════════════
CONFIG_FILE = "gestos.json"

def cargar_gestos():
    if not os.path.exists(CONFIG_FILE):
        print(f"[AVISO] No se encontró {CONFIG_FILE}. Los gestos de mano izquierda están desactivados.")
        return [], 0.05
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    gestos = [g for g in data.get("gestos", []) if g.get("activo", True)]
    umbral = data.get("umbral", 0.05)
    print(f"[GESTOS] {len(gestos)} gesto(s) activos cargados. Umbral: {umbral}")
    return gestos, umbral

gestos_config, UMBRAL_GESTOS = cargar_gestos()

# Estado de activacion por gesto (evita disparos repetidos)
estado_gestos = {g["id"]: False for g in gestos_config}

def ejecutar_gesto(gesto):
    """Ejecuta la accion del gesto: hotkey o comando del sistema."""
    tipo   = gesto.get("tipo", "hotkey")
    accion = gesto.get("accion", [])
    nombre = gesto.get("nombre", gesto["id"])
    try:
        if tipo == "hotkey":
            if isinstance(accion, list) and accion:
                pyautogui.hotkey(*accion)
                print(f"[GESTO] {nombre} → {'+'.join(accion)}")
        elif tipo == "comando":
            if accion:
                subprocess.Popen(accion, shell=True)
                print(f"[GESTO] {nombre} → {accion}")
    except Exception as e:
        print(f"[ERROR] Gesto '{nombre}': {e}")

# ════════════════════════════════════════════════════
#  Variables de estado para click (mano derecha)
# ════════════════════════════════════════════════════
click_izq_activo = False
click_der_activo = False

# ════════════════════════════════════════════════════
#  Contador de frames
# ════════════════════════════════════════════════════
frame_count = 0
deadzone = 5

mp_hands = mp.solutions.hands
mp_draw  = mp.solutions.drawing_utils

# ════════════════════════════════════════════════════
#  Camara — captura directamente a 320x240
# ════════════════════════════════════════════════════
cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
cap.set(3, 640)
cap.set(4, 480)

if not cap.isOpened():
    print("Error: no se pudo abrir la cámara")
    exit(1)

# ════════════════════════════════════════════════════
#  Constantes
# ════════════════════════════════════════════════════
custom_Conectors = [(4,8),(4,12),(4,16),(4,20)]
custom_Landmarks = [4, 8, 12, 16, 20]

INDEX_TIPS = [
    mp_hands.HandLandmark.THUMB_TIP,
    mp_hands.HandLandmark.INDEX_FINGER_TIP,
    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
    mp_hands.HandLandmark.RING_FINGER_TIP,
    mp_hands.HandLandmark.PINKY_TIP,
]

user32        = ctypes.windll.user32
screen_width  = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)

prev_x, prev_y = 0, 0
smooth = 2

MARGIN  = 50
CAM_W, CAM_H = 640, 480
XMIN    = MARGIN
XMAX    = CAM_W - MARGIN
YMIN    = MARGIN
YMAX    = CAM_H - MARGIN
ZONE_W  = XMAX - XMIN
ZONE_H  = YMAX - YMIN
UMBRAL  = 0.04

# ════════════════════════════════════════════════════
#  Utilidades
# ════════════════════════════════════════════════════
def distancia(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def es_mano_derecha(handedness):
    """MediaPipe etiqueta las manos en espejo; Right = mano derecha del usuario."""
    return handedness.classification[0].label == "Right"

# ════════════════════════════════════════════════════
#  Bucle principal
# ════════════════════════════════════════════════════
with mp_hands.Hands(
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7,
    max_num_hands=2                    # ahora detectamos ambas manos
) as hands:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        frame.flags.writeable = False
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results   = hands.process(frame_rgb)
        frame.flags.writeable = True

        if results.multi_hand_landmarks and results.multi_handedness:

            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                mano_derecha = es_mano_derecha(handedness)

                # ════════════════════════════════════
                #  MANO DERECHA — control del mouse
                # ════════════════════════════════════
                if mano_derecha:

                    # Dibujar zona activa
                    cv2.rectangle(frame, (XMIN, YMIN), (XMAX, YMAX), (255, 0, 0), 2)

                    # Obtener posición del índice
                    cursor_x = int(hand_landmarks.landmark[8].x * CAM_W)
                    cursor_y = int(hand_landmarks.landmark[8].y * CAM_H)

                    cursor_x = max(XMIN, min(cursor_x, XMAX))
                    cursor_y = max(YMIN, min(cursor_y, YMAX))

                    screen_x = (cursor_x - XMIN) * screen_width  / ZONE_W
                    screen_y = (cursor_y - YMIN) * screen_height / ZONE_H

                    # Control de frames
                    frame_count = (frame_count + 1) % 1000

                    if frame_count % 2 == 0:
                        dx = screen_x - prev_x
                        dy = screen_y - prev_y

                        if abs(dx) < deadzone: dx = 0
                        if abs(dy) < deadzone: dy = 0

                        curr_x = prev_x + dx / smooth
                        curr_y = prev_y + dy / smooth

                        mouse.move(curr_x, curr_y)
                        prev_x, prev_y = curr_x, curr_y

                        # Distancias para clicks
                        d_izq = distancia(hand_landmarks.landmark[4],
                                          hand_landmarks.landmark[8])
                        d_der = distancia(hand_landmarks.landmark[4],
                                          hand_landmarks.landmark[12])

                        # Clic izquierdo (pulgar + índice)
                        if d_izq < UMBRAL:
                            if not click_izq_activo:
                                mouse.click('left')
                                click_izq_activo = True
                        else:
                            click_izq_activo = False

                        # Clic derecho (pulgar + medio)
                        if d_der < UMBRAL:
                            if not click_der_activo:
                                mouse.click('right')
                                click_der_activo = True
                        else:
                            click_der_activo = False

                    # Etiqueta visual
                    cv2.putText(frame, "MOUSE", (XMIN, YMIN - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 80, 80), 1)

                # ════════════════════════════════════
                #  MANO IZQUIERDA — gestos personalizados
                # ════════════════════════════════════
                else:
                    pulgar = hand_landmarks.landmark[4]

                    for gesto in gestos_config:
                        dedo_idx = gesto.get("dedo", 8)
                        dedo_lm  = hand_landmarks.landmark[dedo_idx]
                        dist     = distancia(pulgar, dedo_lm)

                        gid = gesto["id"]
                        if dist < UMBRAL_GESTOS:
                            if not estado_gestos[gid]:
                                ejecutar_gesto(gesto)
                                estado_gestos[gid] = True

                            # Indicador visual del gesto activo
                            px = int(dedo_lm.x * CAM_W)
                            py = int(dedo_lm.y * CAM_H)
                            cv2.circle(frame, (px, py), 10, (0, 255, 136), -1)
                            cv2.putText(frame, gesto.get("nombre", gid),
                                        (px + 12, py + 4),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                                        (0, 255, 136), 1)
                        else:
                            estado_gestos[gid] = False

                    # Etiqueta visual
                    cv2.putText(frame, "GESTOS", (4, 14),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        # ════════════════════════════════════════════
        #  Kill Switch
        # ════════════════════════════════════════════
        cv2.imshow("Hand Controller", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()