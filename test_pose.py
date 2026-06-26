import cv2
import mediapipe as mp
import numpy as np

VALID_EXERCISES = ["squat", "pushup", "plank", "pullup"]
IDEAL_CAMERA_ANGLES = {
    "squat": "front",
    "pushup": "side",
    "plank": "side",
    "pullup": "front"
}

STATUS_COLORS = {
    "good": (0, 220, 100),
    "warning": (0, 200, 255),
    "bad": (60, 80, 255),
    "neutral": (190, 190, 190),
}

STATUS_LABELS = {
    "good": "GOOD",
    "warning": "WARN",
    "bad": "BAD",
    "neutral": "INFO",
}

# -----------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------

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

def get_status_color(status):
    return STATUS_COLORS.get(status, STATUS_COLORS["neutral"])

def put_text_with_outline(image, text, position, scale, color, thickness=2):
    cv2.putText(
        image, text, position, cv2.FONT_HERSHEY_SIMPLEX,
        scale, (20, 20, 20), thickness + 3, cv2.LINE_AA
    )
    cv2.putText(
        image, text, position, cv2.FONT_HERSHEY_SIMPLEX,
        scale, color, thickness, cv2.LINE_AA
    )

# -----------------------------------------
# DRAWING FUNCTIONS
# -----------------------------------------

def draw_skeleton(image, landmarks, w, h, status_map):
    """
    Draw skeleton with color-coded joints based on feedback status.
    status_map: dict of keypoint_index -> 'good'/'warning'/'bad'
    """
    connections = [
        (11, 12),           # shoulders
        (11, 13), (13, 15), # left arm
        (12, 14), (14, 16), # right arm
        (11, 23), (12, 24), # torso sides
        (23, 24),           # hips
        (23, 25), (25, 27), # left leg
        (24, 26), (26, 28), # right leg
    ]

    for start, end in connections:
        p1 = get_pixel(landmarks, start, w, h)
        p2 = get_pixel(landmarks, end, w, h)
        cv2.line(image, p1, p2, (35, 35, 35), 6, cv2.LINE_AA)
        cv2.line(image, p1, p2, (235, 235, 235), 3, cv2.LINE_AA)

    for i in range(33):
        px, py = get_pixel(landmarks, i, w, h)
        s = status_map.get(i, "neutral")
        color = get_status_color(s)
        radius = 9 if s != "neutral" else 7
        cv2.circle(image, (px, py), radius + 2, (30, 30, 30), -1, cv2.LINE_AA)
        cv2.circle(image, (px, py), radius, color, -1, cv2.LINE_AA)
        cv2.circle(image, (px, py), radius, (255, 255, 255), 2, cv2.LINE_AA)

def draw_angle_on_joint(image, landmarks, a, b, c, w, h, offset=(8, -8)):
    angle = calculate_angle(
        get_keypoint(landmarks, a),
        get_keypoint(landmarks, b),
        get_keypoint(landmarks, c)
    )
    px, py = get_pixel(landmarks, b, w, h)
    put_text_with_outline(
        image,
        f"{angle:.0f}deg",
        (px + offset[0], py + offset[1]),
        0.78,
        (0, 255, 255),
        2,
    )
    return angle

def draw_angles_for_exercise(image, landmarks, exercise, w, h):
    """Draw relevant joint angles depending on exercise"""
    if exercise == "squat":
        draw_angle_on_joint(image, landmarks, 23, 25, 27, w, h)  # left knee
        draw_angle_on_joint(image, landmarks, 24, 26, 28, w, h)  # right knee
        draw_angle_on_joint(image, landmarks, 11, 23, 25, w, h)  # hip hinge
        draw_angle_on_joint(image, landmarks, 11, 23, 27, w, h, offset=(8, 20))

    elif exercise == "pushup":
        draw_angle_on_joint(image, landmarks, 11, 13, 15, w, h)  # left elbow
        draw_angle_on_joint(image, landmarks, 12, 14, 16, w, h)  # right elbow
        draw_angle_on_joint(image, landmarks, 11, 23, 27, w, h)  # body line
        draw_angle_on_joint(image, landmarks, 13, 11, 23, w, h)  # elbow flare

    elif exercise == "plank":
        draw_angle_on_joint(image, landmarks, 11, 23, 27, w, h)  # body line
        draw_angle_on_joint(image, landmarks, 11, 23, 25, w, h)  # hip position
        draw_angle_on_joint(image, landmarks, 13, 11, 23, w, h)  # shoulder angle

    elif exercise == "pullup":
        draw_angle_on_joint(image, landmarks, 11, 13, 15, w, h)  # left elbow
        draw_angle_on_joint(image, landmarks, 12, 14, 16, w, h)  # right elbow
        draw_angle_on_joint(image, landmarks, 13, 11, 23, w, h)  # shoulder elevation
        draw_angle_on_joint(image, landmarks, 11, 23, 27, w, h)  # body alignment

def build_status_map(exercise, angles, statuses):
    """
    Map joint indices to their status for color-coded skeleton.
    Returns dict: { keypoint_index: 'good'/'warning'/'bad' }
    """
    mapping = {}

    if exercise == "squat":
        knee_status = statuses[0]   # left knee
        hip_status  = statuses[1]   # hip hinge
        back_status = statuses[2]   # back alignment
        mapping.update({
            25: knee_status, 27: knee_status,  # left knee/ankle
            26: knee_status, 28: knee_status,  # right knee/ankle
            23: hip_status,  24: hip_status,   # hips
            11: back_status, 12: back_status,  # shoulders
        })

    elif exercise == "pushup":
        elbow_status = statuses[0]  # elbow bend
        body_status  = statuses[1]  # body line
        flare_status = statuses[2]  # elbow flare
        mapping.update({
            13: elbow_status, 15: elbow_status,  # left elbow/wrist
            14: elbow_status, 16: elbow_status,  # right elbow/wrist
            23: body_status,  24: body_status,   # hips
            11: flare_status, 12: flare_status,  # shoulders
        })

    elif exercise == "plank":
        body_status     = statuses[0]  # body line
        hip_status      = statuses[1]  # hip position
        shoulder_status = statuses[2]  # shoulder angle
        mapping.update({
            23: hip_status,      24: hip_status,      # hips
            25: body_status,     27: body_status,     # knees/ankles
            11: shoulder_status, 12: shoulder_status, # shoulders
        })

    elif exercise == "pullup":
        pull_status     = statuses[0]  # pull height
        shoulder_status = statuses[1]  # shoulder elevation
        body_status     = statuses[2]  # body alignment
        mapping.update({
            13: pull_status,     15: pull_status,     # left elbow/wrist
            14: pull_status,     16: pull_status,     # right elbow/wrist
            11: shoulder_status, 12: shoulder_status, # shoulders
            23: body_status,     24: body_status,     # hips
        })

    return mapping

def explain_score(score, total):
    if total <= 0:
        return "No posture checks were scored because no reliable pose was detected."
    return (
        f"The score means {score} out of {total} posture checks passed. "
        "Each check is based on the camera angle and exercise-specific form rules. "
        "Items marked [GOOD] count as passed checks, while [WARN] and [BAD] show areas to improve."
    )

def draw_feedback_panel(image, exercise, feedback, angles, statuses, h, w, phase="", phase_desc=""):
    """Draw a full-width report panel below the image for chat readability."""
    panel_w = max(w, 900)
    margin = 24
    wrap_chars = max(52, int((panel_w - margin * 2) / 13))

    def wrap_lines(text):
        words = str(text).split()
        lines, current = [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= wrap_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    phase_lines = wrap_lines(phase_desc)
    feedback_lines = []
    for i, fb in enumerate(feedback):
        status = statuses[i] if i < len(statuses) else "neutral"
        feedback_lines.append((status, wrap_lines(fb)))

    good_count = sum(1 for s in statuses if s == "good")
    warning_count = sum(1 for s in statuses if s == "warning")
    bad_count = sum(1 for s in statuses if s == "bad")
    total = len(statuses)

    panel_h = 190
    panel_h += len(phase_lines) * 26
    panel_h += 68
    panel_h += len(angles) * 32
    panel_h += 70
    panel_h += sum(len(lines) * 28 + 14 for _, lines in feedback_lines)
    panel_h += 220
    panel_h = max(panel_h, 560)

    panel = np.zeros((panel_h, panel_w, 3), dtype=np.uint8)
    panel[:] = (25, 25, 25)

    def put(text, x, y, color, scale=0.78, thickness=2):
        if y < panel_h - 10:  # only draw if within bounds
            cv2.putText(panel, text, (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)

    def divider(y):
        if y < panel_h - 10:
            cv2.line(panel, (margin, y), (panel_w - margin, y), (70, 70, 70), 2)

    def legend_item(x, y, status):
        color = get_status_color(status)
        label = STATUS_LABELS.get(status, "INFO")
        cv2.circle(panel, (x, y - 6), 10, color, -1, cv2.LINE_AA)
        cv2.circle(panel, (x, y - 6), 10, (255, 255, 255), 1, cv2.LINE_AA)
        put(label, x + 18, y, color, 0.58, 2)

    put("POSTURE ANALYSIS", margin, 48, (0, 210, 255), 1.0, 3)
    put(f"Exercise: {exercise.upper()}", margin, 90, (235, 235, 235), 0.78, 2)
    put(f"Phase: {phase}", margin, 128, (0, 255, 180), 0.78, 2)
    y = 164
    for line in phase_lines:
        put(line, margin, y, (200, 200, 200), 0.62, 1)
        y += 26
    y += 10
    legend_item(margin, y, "good")
    legend_item(margin + 150, y, "warning")
    legend_item(margin + 300, y, "bad")
    y += 32
    put(
        f"Checks: {good_count} good | {warning_count} warning | {bad_count} bad",
        margin,
        y,
        (230, 230, 230),
        0.62,
        1,
    )
    y += 18
    divider(y + 8)
    y += 42

    put("JOINT ANGLES", margin, y, (190, 190, 190), 0.7, 2)
    y += 34
    for joint, angle in angles.items():
        put(f"{joint}: {angle} deg", margin + 16, y, (255, 230, 90), 0.68, 2)
        y += 32
    divider(y + 8)
    y += 42

    put("FEEDBACK", margin, y, (190, 190, 190), 0.7, 2)
    y += 36
    for status, lines in feedback_lines:
        color = get_status_color(status)
        label = STATUS_LABELS.get(status, "INFO")
        for line in lines:
            put(f"[{label}] {line}" if line and not line.startswith("[") else line, margin + 16, y, color, 0.68, 2)
            y += 28
        y += 14

    divider(y + 8)
    y += 42

    put(f"Score: {good_count}/{total} checks passed", margin, y, (235, 235, 235), 0.82, 2)
    y += 44

    if bad_count == 0 and warning_count == 0:
        result, color = "EXCELLENT FORM", (0, 255, 100)
    elif bad_count == 0:
        result, color = "GOOD, MINOR ADJUSTMENTS", (0, 200, 255)
    elif bad_count <= total // 2:
        result, color = "NEEDS IMPROVEMENT", (0, 140, 255)
    else:
        result, color = "POOR FORM, REVIEW NEEDED", (0, 60, 255)

    put(result, margin, y, color, 0.88, 3)

    if w < panel_w:
        pad = panel_w - w
        image = cv2.copyMakeBorder(image, 0, 0, 0, pad, cv2.BORDER_CONSTANT, value=(0, 0, 0))
    elif w > panel_w:
        panel = cv2.copyMakeBorder(panel, 0, 0, 0, w - panel_w, cv2.BORDER_CONSTANT, value=(25, 25, 25))

    combined = np.vstack([image, panel])
    return combined

# -----------------------------------------
# EXERCISE ANALYSIS FUNCTIONS
# -----------------------------------------

def detect_squat_phase(left_knee):
    if left_knee <= 110:
        return "BOTTOM POSITION", "Deep squat, bottom of rep"
    elif left_knee >= 155:
        return "STANDING POSITION", "Fully standing, top of rep"
    else:
        return "MID POSITION", "Descending or ascending"

def analyze_squat(landmarks):
    feedback, status = [], []

    left_knee = calculate_angle(
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 25),
        get_keypoint(landmarks, 27)
    )
    right_knee = calculate_angle(
        get_keypoint(landmarks, 24),
        get_keypoint(landmarks, 26),
        get_keypoint(landmarks, 28)
    )
    hip_hinge = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 25)
    )
    back_alignment = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 27)
    )

    # Detect phase
    phase, phase_desc = detect_squat_phase(left_knee)

    # Phase-specific knee feedback
    if phase == "BOTTOM POSITION":
        if left_knee <= 100:
            feedback.append("[GOOD] Knee depth: Full squat depth achieved")
            status.append("good")
        else:
            feedback.append("[WARN] Knee depth: Squat deeper at bottom position")
            status.append("warning")

    elif phase == "STANDING POSITION":
        if left_knee >= 155:
            feedback.append("[GOOD] Standing: Fully extended at top")
            status.append("good")
        else:
            feedback.append("[WARN] Standing: Fully extend legs at top of rep")
            status.append("warning")

    else:  # MID
        feedback.append("[WARN] Mid-rep captured, try photo at top or bottom")
        status.append("warning")

    # Hip hinge
    if 40 <= hip_hinge <= 110:
        feedback.append("[GOOD] Hip hinge: Good forward lean")
        status.append("good")
    elif hip_hinge < 40:
        feedback.append("[WARN] Hip hinge: Leaning too far forward")
        status.append("warning")
    else:
        feedback.append("[BAD] Hip hinge: Not hinging enough at hips")
        status.append("bad")

    # Back
    if back_alignment >= 150:
        feedback.append("[GOOD] Back: Spine reasonably straight")
        status.append("good")
    elif back_alignment >= 130:
        feedback.append("[WARN] Back: Slight forward lean, keep chest up")
        status.append("warning")
    else:
        feedback.append("[BAD] Back: Excessive lean, straighten spine")
        status.append("bad")

    # Knee symmetry
    if abs(left_knee - right_knee) <= 20:
        feedback.append("[GOOD] Knee symmetry: Both knees balanced")
        status.append("good")
    else:
        feedback.append("[WARN] Knee symmetry: Uneven, check for knee caving")
        status.append("warning")

    return feedback, status, {
        "Left Knee": left_knee,
        "Right Knee": right_knee,
        "Hip Hinge": hip_hinge,
        "Back Alignment": back_alignment
    }, phase, phase_desc

def detect_pushup_phase(left_elbow, right_elbow):
    avg_elbow = (left_elbow + right_elbow) / 2

    if avg_elbow <= 120:
        return "DOWN POSITION", "Chest near floor - bottom of rep"
    elif avg_elbow >= 150:
        return "UP POSITION", "Arms extended - top of rep"
    else:
        return "MID POSITION", "Mid-rep transition"

def analyze_pushup(landmarks):
    feedback, status = [], []

    left_elbow = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 13),
        get_keypoint(landmarks, 15)
    )
    right_elbow = calculate_angle(
        get_keypoint(landmarks, 12),
        get_keypoint(landmarks, 14),
        get_keypoint(landmarks, 16)
    )
    body_line = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 27)
    )
    elbow_flare = calculate_angle(
        get_keypoint(landmarks, 13),
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23)
    )

    # Detect phase
    phase, phase_desc = detect_pushup_phase(left_elbow, right_elbow)

    # Phase-specific thresholds
    if phase == "DOWN POSITION":
        # Strict at bottom, elbow must be properly bent
        if 60 <= left_elbow <= 110:
            feedback.append("[GOOD] Elbow bend: Good depth at bottom")
            status.append("good")
        else:
            feedback.append("[BAD] Elbow bend: Lower your chest more at bottom")
            status.append("bad")

    elif phase == "UP POSITION":
        # At top, arms should be extended
        if left_elbow >= 155:
            feedback.append("[GOOD] Elbow: Arms fully extended at top")
            status.append("good")
        else:
            feedback.append("[WARN] Elbow: Fully extend arms at top of rep")
            status.append("warning")

    else:  # MID POSITION
        feedback.append("[WARN] Mid-rep captured, try photo at top or bottom")
        status.append("warning")

    # Body line, same for all phases
    if phase == "UP POSITION":
        # At top, body must be very straight
        if body_line >= 160:
            feedback.append("[GOOD] Body line: Straight - core engaged")
            status.append("good")
        elif body_line >= 145:
            feedback.append("[WARN] Body line: Slight sag - tighten core at top")
            status.append("warning")
        else:
            feedback.append("[BAD] Body line: Hips sagging at top - engage core")
            status.append("bad")

    elif phase == "DOWN POSITION":
        # At bottom, slight body angle is acceptable
        if body_line >= 145:
            feedback.append("[GOOD] Body line: Good alignment at bottom")
            status.append("good")
        elif body_line >= 125:
            feedback.append("[WARN] Body line: Slight sag - keep core tight")
            status.append("warning")
        else:
            feedback.append("[BAD] Body line: Hips sagging badly - reset form")
            status.append("bad")

    else:  # MID
        if body_line >= 160:
            feedback.append("[GOOD] Body line: Straight - core engaged")
            status.append("good")
        else:
            feedback.append("[WARN] Body line: Keep body straight throughout rep")
            status.append("warning")

    # Elbow flare
    if elbow_flare <= 55:
        feedback.append("[GOOD] Elbow flare: Good, elbows close to body")
        status.append("good")
    elif elbow_flare <= 70:
        feedback.append("[WARN] Elbow flare: Slightly wide, tuck elbows in")
        status.append("warning")
    else:
        feedback.append("[BAD] Elbow flare: Too wide, shoulder injury risk")
        status.append("bad")

    # Arm symmetry
    if abs(left_elbow - right_elbow) <= 25:
        feedback.append("[GOOD] Arm symmetry: Both arms balanced")
        status.append("good")
    else:
        feedback.append("[WARN] Arm symmetry: Uneven, may be camera angle")
        status.append("warning")

    return feedback, status, {
        "Left Elbow": left_elbow,
        "Right Elbow": right_elbow,
        "Body Line": body_line,
        "Elbow Flare": elbow_flare
    }, phase, phase_desc

def analyze_plank(landmarks):
    feedback, status = [], []

    body_line = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 27)
    )
    hip_position = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 25)
    )
    shoulder_angle = calculate_angle(
        get_keypoint(landmarks, 13),
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23)
    )
    nose_y     = get_keypoint(landmarks, 0)[1]
    shoulder_y = get_keypoint(landmarks, 11)[1]
    neck_diff  = abs(nose_y - shoulder_y)

    if body_line >= 148:
        feedback.append("[GOOD] Body line: Good plank alignment")
        status.append("good")
    elif body_line >= 130:
        feedback.append("[WARN] Body line: Slight sag, squeeze glutes and core")
        status.append("warning")
    else:
        feedback.append("[BAD] Body line: Hips sagging badly, reset position")
        status.append("bad")

    if hip_position >= 155:
        feedback.append("[GOOD] Hip position: Level and stable")
        status.append("good")
    elif hip_position >= 135:
        feedback.append("[WARN] Hip position: Slightly off, adjust hips level")
        status.append("warning")
    else:
        feedback.append("[BAD] Hip position: Hips misaligned significantly")
        status.append("bad")

    if 75 <= shoulder_angle <= 105:
        feedback.append("[GOOD] Shoulder: Elbows well positioned")
        status.append("good")
    else:
        feedback.append("[WARN] Shoulder: Shift elbows closer under shoulders")
        status.append("warning")

    if neck_diff <= 0.12:
        feedback.append("[GOOD] Neck: Neutral alignment")
        status.append("good")
    else:
        feedback.append("[WARN] Neck: Keep head neutral, eyes toward floor")
        status.append("warning")

    phase      = "HOLD POSITION"
    phase_desc = "Static plank, maintain alignment"

    return feedback, status, {
        "Body Line": body_line,
        "Hip Position": hip_position,
        "Shoulder Angle": shoulder_angle
    }, phase, phase_desc

def detect_pullup_phase(left_elbow):
    if left_elbow <= 100:
        return "TOP POSITION", "Chin at or above bar, top of rep"
    elif left_elbow >= 155:
        return "DEAD HANG", "Arms fully extended, bottom of rep"
    else:
        return "MID POSITION", "Pulling up or lowering down"

def analyze_pullup(landmarks):
    feedback, status = [], []

    left_elbow = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 13),
        get_keypoint(landmarks, 15)
    )
    right_elbow = calculate_angle(
        get_keypoint(landmarks, 12),
        get_keypoint(landmarks, 14),
        get_keypoint(landmarks, 16)
    )
    shoulder_elevation = calculate_angle(
        get_keypoint(landmarks, 13),
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23)
    )
    body_alignment = calculate_angle(
        get_keypoint(landmarks, 11),
        get_keypoint(landmarks, 23),
        get_keypoint(landmarks, 27)
    )

    # Detect phase
    phase, phase_desc = detect_pullup_phase(left_elbow)

    # Phase-specific elbow feedback
    if phase == "TOP POSITION":
        if left_elbow <= 100:
            feedback.append("[GOOD] Pull height: Chin at or above bar")
            status.append("good")
        else:
            feedback.append("[WARN] Pull height: Pull higher, chin must clear bar")
            status.append("warning")

    elif phase == "DEAD HANG":
        if right_elbow >= 160:
            feedback.append("[GOOD] Dead hang: Full arm extension at bottom")
            status.append("good")
        else:
            feedback.append("[WARN] Dead hang: Extend arms fully at bottom")
            status.append("warning")

    else:  # MID
        feedback.append("[WARN] Mid-rep captured, try photo at top or bottom")
        status.append("warning")

    # Shoulder engagement
    if shoulder_elevation <= 100:
        feedback.append("[GOOD] Shoulder: Lats engaged, not shrugging")
        status.append("good")
    elif shoulder_elevation <= 120:
        feedback.append("[WARN] Shoulder: Slight shrug, pull blades down")
        status.append("warning")
    else:
        feedback.append("[BAD] Shoulder: Shrugging, engage lats not traps")
        status.append("bad")

    # Body alignment
    if body_alignment >= 145:
        feedback.append("[GOOD] Body: Controlled, minimal swinging")
        status.append("good")
    else:
        feedback.append("[BAD] Body: Swinging detected, control movement")
        status.append("bad")

    return feedback, status, {
        "Left Elbow": left_elbow,
        "Right Elbow": right_elbow,
        "Shoulder Elevation": shoulder_elevation,
        "Body Alignment": body_alignment
    }, phase, phase_desc

# -----------------------------------------
# USER INPUT & MAIN ANALYZER
# -----------------------------------------

def get_exercise_from_user():
    while True:
        exercise = input("\nEnter exercise (squat / pushup / plank / pullup): ").strip().lower()
        if exercise in VALID_EXERCISES:
            return exercise
        print("[BAD] Invalid, please enter: squat, pushup, plank, or pullup")

def detect_camera_angle(landmarks):
    """
    Detects approximate camera viewing angle.
    Returns: 'front', 'side', 'diagonal', or 'unknown'
    """
    left_shoulder  = get_keypoint(landmarks, 11)
    right_shoulder = get_keypoint(landmarks, 12)
    left_hip       = get_keypoint(landmarks, 23)
    right_hip      = get_keypoint(landmarks, 24)

    shoulder_x_diff = abs(left_shoulder[0] - right_shoulder[0])
    hip_x_diff      = abs(left_hip[0] - right_hip[0])

    avg_diff = (shoulder_x_diff + hip_x_diff) / 2

    if avg_diff >= 0.15:
        return "front"
    elif avg_diff <= 0.06:
        return "side"
    else:
        return "diagonal"

def get_angle_tip(camera_angle, exercise):
    """Return best camera angle tip per exercise"""
    best = IDEAL_CAMERA_ANGLES.get(exercise, "front")

    if camera_angle == best:
        return f"[GOOD] Camera angle: {camera_angle.upper()} view, ideal for {exercise}"
    else:
        return f"[WARN] Camera angle: {camera_angle.upper()} view detected, {best.upper()} view recommended for {exercise}"

def analyze_landmarks_for_exercise(landmarks, image_width, image_height, exercise):
    """
    Analyze pose landmarks for one exercise without drawing or saving output.
    This pure analysis result can be reused by image and future video workflows.
    """
    exercise = exercise.strip().lower()
    if exercise not in VALID_EXERCISES:
        raise ValueError(f"Invalid exercise '{exercise}'. Choose: {', '.join(VALID_EXERCISES)}")

    camera_angle = detect_camera_angle(landmarks)
    camera_tip = get_angle_tip(camera_angle, exercise)

    if exercise == "squat":
        feedback, statuses, angles, phase, phase_desc = analyze_squat(landmarks)
    elif exercise == "pushup":
        feedback, statuses, angles, phase, phase_desc = analyze_pushup(landmarks)
    elif exercise == "plank":
        feedback, statuses, angles, phase, phase_desc = analyze_plank(landmarks)
    elif exercise == "pullup":
        feedback, statuses, angles, phase, phase_desc = analyze_pullup(landmarks)

    if camera_angle != IDEAL_CAMERA_ANGLES.get(exercise):
        phase_desc = phase_desc + " | NOTE: Angled shot may affect accuracy"

    feedback = [camera_tip] + feedback
    statuses = ["good" if "GOOD" in camera_tip else "warning"] + statuses
    score = sum(1 for s in statuses if s == "good")

    return {
        "exercise": exercise,
        "phase": phase,
        "phase_description": phase_desc,
        "phase_desc": phase_desc,
        "camera_angle": camera_angle,
        "camera_tip": camera_tip,
        "angles": angles,
        "feedback": feedback,
        "statuses": statuses,
        "score": score,
        "total": len(statuses),
        "score_explanation": explain_score(score, len(statuses)),
        "image_width": image_width,
        "image_height": image_height
    }

def analyze_pose(landmarks, image, w, h, exercise=None, output_path="output.jpg", show_window=True):
    if exercise is None:
        exercise = get_exercise_from_user()

    report = analyze_landmarks_for_exercise(landmarks, w, h, exercise)
    exercise = report["exercise"]
    feedback = report["feedback"]
    status = report["statuses"]
    angles = report["angles"]
    phase = report["phase"]
    phase_desc = report["phase_desc"]

    print(f"\n{report['camera_tip']}")

    print(f"\nExercise: {exercise.upper()} | Phase: {phase}")
    print(f"({phase_desc})")
    print("\nJoint Angles:")
    for joint, angle in angles.items():
        print(f"  {joint}: {angle}")
    print("\nFeedback:")
    for f in feedback:
        print(f"  {f}")
    print(f"\nScore: {report['score']}/{report['total']} checks passed")

    status_map = build_status_map(exercise, angles, status[1:])
    draw_skeleton(image, landmarks, w, h, status_map)
    draw_angles_for_exercise(image, landmarks, exercise, w, h)
    output = draw_feedback_panel(
        image, exercise, feedback, angles, status, h, w,
        phase=phase, phase_desc=phase_desc
    )

    if not cv2.imwrite(output_path, output):
        raise RuntimeError(f"Could not save output image to {output_path}")

    if show_window:
        cv2.imshow("Workout Posture Analysis", output)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    print(f"\n[GOOD] Output saved as {output_path}")
    report["output_path"] = output_path
    return report

def format_report(report):
    lines = [
        "Workout Posture Analysis",
        f"Exercise: {report['exercise'].upper()}",
        f"Phase: {report['phase']}",
        f"Note: {report['phase_desc']}",
        f"Score: {report['score']}/{report['total']} checks passed",
        f"Score Explanation: {report.get('score_explanation', explain_score(report['score'], report['total']))}",
        "",
        "Joint Angles:"
    ]
    lines.extend(f"- {joint}: {angle} deg" for joint, angle in report["angles"].items())
    lines.extend(["", "Feedback:"])
    lines.extend(f"- {item}" for item in report["feedback"])
    return "\n".join(lines)

def create_landmarker(model_path="pose_landmarker.task"):
    BaseOptions           = mp.tasks.BaseOptions
    PoseLandmarker        = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode     = mp.tasks.vision.RunningMode

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.IMAGE
    )
    return PoseLandmarker.create_from_options(options)

def analyze_image_file(img_path, exercise, output_path="output.jpg", show_window=False, landmarker=None):
    close_landmarker = landmarker is None
    if landmarker is None:
        landmarker = create_landmarker()

    try:
        mp_image = mp.Image.create_from_file(img_path)
        results  = landmarker.detect(mp_image)

        if not results.pose_landmarks:
            raise ValueError("No pose detected, ensure full body is visible")

        image = cv2.imread(img_path)
        if image is None:
            raise ValueError(f"Could not read image file: {img_path}")

        h, w = image.shape[:2]
        return analyze_pose(
            results.pose_landmarks[0],
            image,
            w,
            h,
            exercise=exercise,
            output_path=output_path,
            show_window=show_window
        )
    finally:
        if close_landmarker:
            landmarker.close()

# -----------------------------------------
# MAIN ENTRY
# -----------------------------------------

if __name__ == "__main__":
    img_path = input("Enter image filename (e.g. workout.jpg): ").strip()
    exercise = get_exercise_from_user()
    analyze_image_file(img_path, exercise, output_path="output.jpg", show_window=True)

