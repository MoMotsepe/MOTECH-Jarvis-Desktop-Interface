import cv2
import mediapipe as mp
import os
import time
import platform
import subprocess
from collections import deque

# blah blah
os.environ['GLOG_minloglevel'] = '2'

# mediapipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)

# set up webcam
if platform.system() == 'Darwin':
    cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
else:
    cap = cv2.VideoCapture(0)  # for Windows/Linux

if not cap.isOpened():
    print("Cannot open camera")
    exit()

# app icons
icons = [
    {"rect": (50, 50, 150, 100), "name": "Chrome", "cmd": "open -a 'Google Chrome'"},
    {"rect": (250, 50, 150, 100), "name": "Calculator", "cmd": "open -a Calculator"},
    {"rect": (450, 50, 150, 100), "name": "Notes", "cmd": "open -a Notes"},
    {"rect": (650, 50, 150, 100), "name": "Exit", "cmd": "exit"}
]

# variables
hover_start = None
hover_icon = None
hover_time_required = 0.7  # seconds
click_debounce = False
click_debounce_time = 0
prev_time = time.time()
fps_buffer = deque(maxlen=30)  # Store last 30 FPS values
frame_count = 0
skip_frames = 2  # Process every 3rd frame for hand tracking

print("Jarvis Desktop Interface Started")
print("Instructions:")
print("1. Hover over an icon for 0.7 seconds to launch")
print("2. Pinch thumb and index finger to click instantly")
print("3. Hover over 'Exit' to quit")
print("Press 'q' to quit anytime")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    frame = cv2.flip(frame, 1)  # Mirror the frame for more intuitive control
    frame_count += 1

    pointer = None
    pinch_active = False

    #  Hand Tracking
    if frame_count % (skip_frames + 1) == 0:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]

            # Map normalized coordinates to screen pixels
            h, w, _ = frame.shape
            pointer = (int(index_tip.x * w), int(index_tip.y * h))

            # Calculate pinch distance
            pinch_dist = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5
            pinch_active = pinch_dist < 0.05

            #  hand landmarks
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)
            )

            #  thumb and index finger tips
            thumb_pixel = (int(thumb_tip.x * w), int(thumb_tip.y * h))
            cv2.circle(frame, thumb_pixel, 8, (0, 255, 255), -1)

    # icon designz
    for icon in icons:
        x, y, width, height = icon["rect"]
        is_hovered = False
        color = (0, 200, 0)

        # pointer
        if pointer:
            px, py = pointer
            if x < px < x + width and y < py < y + height:
                is_hovered = True
                color = (0, 0, 255)

                # Handle hover activation
                if hover_icon != icon:
                    hover_start = time.time()
                    hover_icon = icon
                elif time.time() - hover_start > hover_time_required:
                    # Launch app or exit
                    if icon["name"] == "Exit":
                        print("Exiting Jarvis Desktop Interface...")
                        cap.release()
                        cv2.destroyAllWindows()
                        exit(0)
                    else:
                        try:
                            print(f"Launching {icon['name']}...")
                            # Launch in background
                            subprocess.Popen(icon["cmd"], shell=True,
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)

                            # Visual feedback
                            cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 0), -1)
                            cv2.putText(frame, "Launching!", (x + 10, y + 60),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                            cv2.imshow("Jarvis Desktop Interface", frame)
                            cv2.waitKey(300)

                        except Exception as e:
                            print(f"Failed to launch {icon['name']}: {e}")

                        # Reset hover state
                        hover_icon = None
                        hover_start = None
                        time.sleep(0.5)  # Prevent immediate re-trigger

                # Handle pinch click
                if pinch_active and not click_debounce:
                    click_debounce = True
                    click_debounce_time = time.time()
                    if icon["name"] == "Exit":
                        print("Exiting via pinch click...")
                        cap.release()
                        cv2.destroyAllWindows()
                        exit(0)
                    else:
                        try:
                            print(f"Click launching {icon['name']}...")
                            subprocess.Popen(icon["cmd"], shell=True,
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL)
                        except Exception as e:
                            print(f"Failed to launch {icon['name']}: {e}")
        else:
            # make hover if no pointer
            if hover_icon == icon:
                hover_icon = None
                hover_start = None

        # icon with semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + width, y + height), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        #icon border
        border_thickness = 3 if is_hovered else 2
        cv2.rectangle(frame, (x, y), (x + width, y + height), color, border_thickness)


        font_scale = 0.7
        font_thickness = 2
        (text_width, text_height), baseline = cv2.getTextSize(
            icon["name"], cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
        )
        text_x = x + (width - text_width) // 2
        text_y = y + (height + text_height) // 2
        cv2.putText(frame, icon["name"], (text_x, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness)

        # Draw hover progress bar if hovering
        if is_hovered and hover_icon == icon:
            elapsed = time.time() - hover_start
            progress = min(elapsed / hover_time_required, 1.0)
            bar_width = int(width * progress)
            cv2.rectangle(frame, (x, y - 15), (x + bar_width, y - 5), (0, 255, 255), -1)
            cv2.rectangle(frame, (x, y - 15), (x + width, y - 5), (100, 100, 100), 1)

    # --- Draw pointer ---
    if pointer:
        pointer_color = (0, 0, 255) if pinch_active else (255, 0, 0)
        pointer_size = 15 if pinch_active else 10
        cv2.circle(frame, pointer, pointer_size, pointer_color, -1)
        cv2.circle(frame, pointer, pointer_size + 5, (255, 255, 255), 2)

    #  FPS counter
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if curr_time != prev_time else 0
    fps_buffer.append(fps)
    avg_fps = sum(fps_buffer) / len(fps_buffer) if fps_buffer else fps
    prev_time = curr_time

    # FPS display color
    fps_color = (0, 255, 0) if avg_fps > 20 else (0, 255, 255) if avg_fps > 10 else (0, 0, 255)
    cv2.putText(frame, f"FPS: {int(avg_fps)}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, fps_color, 2)

    # --- Draw instructions ---
    instructions = [
        "Hover: Launch app (0.7s)",
        "Pinch: Instant click",
        "'Q' key: To Quit"
    ]

    for i, instruction in enumerate(instructions):
        cv2.putText(frame, instruction, (10, 480 - i * 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # pinch indicator
    if pinch_active:
        cv2.putText(frame, "PINCH ACTIVE", (500, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    # click
    if click_debounce and time.time() - click_debounce_time > 1.0:
        click_debounce = False

    # show frame
    cv2.imshow("Jarvis Desktop Interface", frame)

    # --- Keyboard controls ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        print("Exiting via keyboard...")
        break
    elif key == ord('h'):
        # Toggle help display
        pass


cap.release()
cv2.destroyAllWindows()
print("Jarvis Desktop Interface closed")