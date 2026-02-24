import mediapipe as mp
import cv2
import os
import time 
p= 1
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

with mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5, max_num_hands =1) as hands:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP].y
                index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP].y
                middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y
                middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y
                ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP].y
                ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP].y
                pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP].y
                pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP].y

                middle_mcp_y = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].y
                middle_mcp_X = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP].x

                thumb_tip_y = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].y
                thumb_tip_X = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP].x

                if (middle_tip < middle_pip and 
                    index_tip < index_pip and 
                    ring_tip > ring_pip and 
                    pinky_tip > pinky_pip):
                    cv2.putText(frame, "bajar", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    if p == 1:
                        p = 0
                #input tres
                elif (middle_tip<middle_pip and
                      index_tip<index_pip and
                      ring_tip<ring_pip and
                      pinky_tip>pinky_pip):
                    cv2.putText(frame, "subir",(50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    if p == 1:
                        p = 0

                elif (index_tip<index_pip and
                      middle_tip> middle_pip and
                      ring_tip< ring_pip and
                      pinky_tip> pinky_pip):
                    cv2.putText(frame, "like",(50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    if p == 1:
                        p = 0


                elif (middle_mcp_X < thumb_tip_X and 
                      middle_mcp_y < thumb_tip_y and
                      middle_tip < middle_pip and
                      index_tip < index_pip and
                      ring_tip < ring_pip and
                      pinky_tip < pinky_pip):
                    cv2.putText(frame, "Cuatro de asada", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

                    
                    #os.system("shutdown /s /t 1")
                else:
                    cv2.putText(frame, "No Saludo", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    p = 1
                

        cv2.imshow("Boton con MediaPipe", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()