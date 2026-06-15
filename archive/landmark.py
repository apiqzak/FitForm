import cv2
import mediapipe as mp
import numpy as np

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return round(angle, 2)

def get_keypoint(landmarks, index):
    lm = landmarks[index]
    return [lm.x, lm.y]

def get_pixel(landmarks, index, w, h):
    lm = landmarks[index]
    return (int(lm.x * w), int(lm.y * h))

# ─────────────────────────────────────────
# DRAWING FUNCTIONS
# ─────────────────────────────────────────

def draw_skeleton(image, landmarks, w, h):
    """Draw skeleton connections and keypoints"""
    connections = [
        (11, 12), (11, 13), (13, 15),  # left arm
        (12, 14), (14, 16),             # right arm
        (11, 23), (12, 24),             # torso
        (23, 24),                        # hips
        (23, 25), (25, 27),             # left leg
        (24, 26), (26, 28),             # right leg
    ]

    # Draw connections
    for start, end in connections:
        p1 = get_pixel(landmarks, start, w, h)
        p2 = get_pixel(landmarks, end, w, h)
        cv2.line(image, p1, p2, (0, 255, 255), 2)

    # Draw keypoints
    for i in range(33):
        px, py = get_pixel(landmarks, i, w, h)
        cv2.circle(image, (px, py), 5, (0, 0, 255), -1)
        cv2.circle(image, (px, py), 5, (255, 255, 255), 1)

def draw_angle(image, landmarks, a, b, c, w, h):
    """Draw angle value at joint b"""
    angle = calculate_angle(
        get_keypoint(landmarks, a),
        get_keypoint(landmarks, b),
        get_keypoint(landmarks, c)
    )
    px, py = get_pixel(landmarks, b, w, h)
    cv2.putText(image, f"{angle}", (px - 30, py - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
    return angle

def draw_feedback_panel(image, exercise, feedback, angles, h, w):
    """Draw feedback panel on the right side of image"""
    panel_width = 320
    panel = np.zeros((h, panel_width, 3), dtype=np.uint8)
    panel[:] = (30, 30, 30)

    # Title
    cv2.putText(panel, "POSTURE ANALYSIS", (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    cv2.putText(panel, f"Exercise: {exercise.upper()}", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.line(panel, (10, 75), (panel_width - 10, 75), (80, 80, 80), 1)

    # Joint Angles
    cv2.putText(panel, "Joint Angles:", (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y = 125
    for joint, angle in angles.items():
        cv2.putText(panel, f"  {joint}: {angle}deg", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 100), 1)
        y += 22

    cv2.line(panel, (10, y + 5), (panel_width - 10, y + 5), (80, 80, 80), 1)
    y += 25

    # Feedback
    cv2.putText(panel, "Feedback:", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    y += 25
    for line in feedback:
        color = (0, 255, 100) if "✅" in line else (0, 140, 255) if "⚠️" in line else (0, 60, 255)
        # Word wrap for long feedback
        words = line.split()
        current_line = ""
        for word in words:
            if len(current_line + word) < 32:
                current_line += word + " "
            else:
                cv2.putText(panel, current_line, (10, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
                y += 18
                current_line = word + " "
        if current_line:
            cv2.putText(panel, current_line, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            y += 22

    # Overall result
    good_count = sum(1 for f in feedback if "✅" in f)
    total = len(feedback)
    overall = "GOOD FORM" if good_count == total else "NEEDS IMPROVEMENT"
    color = (0, 255, 100) if good_count == total else (0, 60, 255)
    cv2.line(panel, (10, h - 50), (panel_width - 10, h - 50), (80, 80, 80), 1)
    cv2.putText(panel, overall, (10, h - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    # Combine image + panel
    combined = np.hstack([image, panel])
    return combined

# ─────────────────────────────────────────
# EXERCISE ANALYSIS FUNCTIONS
# ─────────────────────────────────────────

def get_keypoint(landmarks, index):
    lm = landmarks[index]
    return [lm.x, lm.y]

def analyze_squat(landmarks, image, w, h):
    left_knee  = draw_angle(image, landmarks, 23, 25, 27, w, h)
    right_knee = draw_angle(image, landmarks, 24, 26, 28, w, h)
    hip        = draw_angle(image, landmarks, 11, 23, 25, w, h)

    feedback = []
    if left_knee < 90:
        feedback.append("✅ Knee bend depth: Good")
    elif left_knee < 120:
        feedback.append("⚠️ Knee bend: Slightly shallow")
    else:
        feedback.append("❌ Knee bend: Too shallow")

    if hip < 100:
        feedback.append("✅ Hip hinge: Good")
    else:
        feedback.append("❌ Hip: Lean forward more")

    return feedback, {"Left Knee": left_knee, "Right Knee": right_knee, "Hip": hip}

def analyze_pushup(landmarks, image, w, h):
    left_elbow  = draw_angle(image, landmarks, 11, 13, 15, w, h)
    right_elbow = draw_angle(image, landmarks, 12, 14, 16, w, h)
    body        = draw_angle(image, landmarks, 11, 23, 27, w, h)

    feedback = []
    if left_elbow < 90:
        feedback.append("✅ Elbow bend: Good depth")
    elif left_elbow < 120:
        feedback.append("⚠️ Elbow: Go a bit lower")
    else:
        feedback.append("❌ Elbow: Lower your chest")

    if 160 <= body <= 180:
        feedback.append("✅ Body alignment: Straight")
    else:
        feedback.append("❌ Body: Keep hips straight")

    return feedback, {"Left Elbow": left_elbow, "Right Elbow": right_elbow, "Body Line": body}

def analyze_plank(landmarks, image, w, h):
    body = draw_angle(image, landmarks, 11, 23, 27, w, h)
    hip  = draw_angle(image, landmarks, 12, 24, 26, w, h)

    feedback = []
    if 160 <= body <= 180:
        feedback.append("✅ Body line: Perfect")
    else:
        feedback.append("❌ Body: Straighten your body")

    if 170 <= hip <= 180:
        feedback.append("✅ Hip position: Good")
    else:
        feedback.append("⚠️ Hip: Level with shoulders")

    return feedback, {"Body Alignment": body, "Hip Position": hip}

def analyze_pullup(landmarks, image, w, h):
    left_elbow  = draw_angle(image, landmarks, 11, 13, 15, w, h)
    right_elbow = draw_angle(image, landmarks, 12, 14, 16, w, h)
    shoulder    = draw_angle(image, landmarks, 13, 11, 23, w, h)

    feedback = []
    if left_elbow < 90:
        feedback.append("✅ Pull height: Good")
    elif left_elbow < 120:
        feedback.append("⚠️ Pull: Slightly higher")
    else:
        feedback.append("❌ Pull: Not high enough")

    if shoulder < 90:
        feedback.append("✅ Shoulder: Good engagement")
    else:
        feedback.append("❌ Shoulder: Engage lats more")

    return feedback, {"Left Elbow": left_elbow, "Right Elbow": right_elbow, "Shoulder": shoulder}

def classify_exercise(landmarks):
    wrist_y    = get_keypoint(landmarks, 15)[1]
    shoulder_y = get_keypoint(landmarks, 11)[1]
    ankle_y    = get_keypoint(landmarks, 27)[1]
    knee_angle = calculate_angle(
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 25),
        get_keypoint(landmarks, 27)
    )

    if wrist_y < shoulder_y:
        return "pullup"
    if knee_angle < 140 and shoulder_y < ankle_y * 0.8:
        return "squat"
    if abs(shoulder_y - ankle_y) < 0.25:
        elbow_angle = calculate_angle(
            get_keypoint(landmarks, 11),
            get_keypoint(landmarks, 13),
            get_keypoint(landmarks, 15)
        )
        return "pushup" if elbow_angle < 120 else "plank"
    return "unknown"

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="pose_landmarker.task"),
    running_mode=VisionRunningMode.IMAGE
)

with PoseLandmarker.create_from_options(options) as landmarker:
    mp_image = mp.Image.create_from_file("pushup.jpg")
    results = landmarker.detect(mp_image)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks[0]

        # Load image for drawing
        image = cv2.imread("pushup.jpg")
        h, w = image.shape[:2]

        # Draw skeleton
        draw_skeleton(image, landmarks, w, h)

        # Classify & analyze
        exercise = classify_exercise(landmarks)
        print(f"\n🏋️ Exercise Detected: {exercise.upper()}")

        if exercise == "squat":
            feedback, angles = analyze_squat(landmarks, image, w, h)
        elif exercise == "pushup":
            feedback, angles = analyze_pushup(landmarks, image, w, h)
        elif exercise == "plank":
            feedback, angles = analyze_plank(landmarks, image, w, h)
        elif exercise == "pullup":
            feedback, angles = analyze_pullup(landmarks, image, w, h)
        else:
            feedback, angles = ["❌ Exercise not recognized"], {}

        # Draw feedback panel
        output = draw_feedback_panel(image, exercise, feedback, angles, h, w)

        # Save & show
        cv2.imwrite("output.jpg", output)
        cv2.imshow("Workout Posture Analysis", output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print("✅ Output saved as output.jpg")

    else:
        print("❌ No pose detected")