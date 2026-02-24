import mediapipe as mp
import cv2
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

custom_Conectors=[
    (4,8),
    (4,12),
    (4,16),
    (4,20),
]
custom_Landmarks = [4, 8, 12, 16, 20]

with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_hands =1) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)
        height, width, _ = frame.shape

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                
                index = [
                    mp_hands.HandLandmark.THUMB_TIP,
                    mp_hands.HandLandmark.INDEX_FINGER_TIP,
                    mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                    mp_hands.HandLandmark.RING_FINGER_TIP,
                    mp_hands.HandLandmark.PINKY_TIP
                ]

                for tip in index:
                    point = hand_landmarks.landmark[tip]
                    x = int(point.x * width)
                    y = int(point.y * height)
                    cv2.rectangle(frame, (x-15, y-15), (x+15, y+15) , (255, 0, 255), 2)
                    

                # 🔴 Dibujar conectores personalizados
                for connection in custom_Conectors:
                    start_idx, end_idx = connection

                    start_point = hand_landmarks.landmark[start_idx]
                    end_point = hand_landmarks.landmark[end_idx]

                    x1 = int(start_point.x * width)
                    y1 = int(start_point.y * height)

                    x2 = int(end_point.x * width)
                    y2 = int(end_point.y * height)

                    cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

        cv2.imshow("Boton con MediaPipe", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()