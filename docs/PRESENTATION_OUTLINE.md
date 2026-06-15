# Presentation Outline

Recommended duration: 8 to 10 minutes.

## Slide 1: Project Title

Workout Posture Analysis Assistant

Subtitle: A computer vision skill that checks exercise form from workout photos.

## Slide 2: Target User and Problem

Target users:

- Fitness beginners
- Physical education students
- Sports club members
- Non-technical users practicing basic workouts

Problem:

- Users may not know if their posture is correct.
- They may not have instant access to a coach.
- Poor form can become a habit and reduce training effectiveness.

## Slide 3: Why Computer Vision Is Needed

The task depends on visual body posture.

Computer vision is needed to:

- Detect human body landmarks
- Locate joints such as shoulders, elbows, hips, knees, and ankles
- Calculate joint angles from the image
- Show visual evidence through an annotated output image

Text-only input cannot measure posture from a workout photo.

## Slide 4: System Workflow

Pipeline:

```text
Workout photo
-> Exercise selection
-> MediaPipe pose detection
-> Keypoint extraction
-> Joint angle calculation
-> Form analysis rules
-> Annotated image and report
```

Demo interfaces:

- Main: OpenClaw FitForm skill
- Local script: `test_pose.py`
- OpenClaw bridge: `analyze_cli.py`
- Optional legacy extra: `optional_integrations/telegram_bot.py`

## Slide 5: CV Method Used

Method:

- MediaPipe Pose Landmarker detects 33 body landmarks.
- OpenCV reads the image and draws the result.
- NumPy calculates angles between three landmark points.
- Rule-based thresholds convert angles into feedback.

Examples:

- Knee angle checks squat depth.
- Elbow angle checks pushup depth.
- Body line angle checks plank and pushup alignment.
- Shoulder and elbow angles check pullup form.

Limitations:

- Camera angle affects accuracy.
- Full body must be visible.
- Single-image analysis cannot fully evaluate motion.

## Slide 6: Skill Design

Skill structure:

- Role: posture analysis assistant
- Input: workout image and exercise type
- Workflow: detect pose, calculate angles, analyze form, generate output
- Output: annotated image, score, joint angle table, feedback report
- Safety: educational only, not medical diagnosis

Supported exercises:

- Squat
- Pushup
- Plank
- Pullup

## Slide 7: Demo Input

Show sample input images:

- `samples/images/squat.jpg`
- `pushup.jpg`
- `pullup.jpg`
- `workout.jpg`

Explain ideal camera views:

- Front view for squat and pullup
- Side view for pushup and plank

## Slide 8: Demo Output

Show:

- `output.jpg`
- Skeleton overlay
- Joint angle labels
- Feedback side panel
- Score and phase detection

Explain how the report helps the user decide what to fix next.

## Slide 9: Live Demo

OpenClaw demo:

1. Open the FitForm Assistant skill.
2. Upload a workout image.
3. Type a simple prompt such as `analyze squat`.
4. Run the analysis through `analyze_cli.py`.
5. Show the annotated image and report.

Local demo:

```powershell
.\venv\Scripts\python.exe test_pose.py
```

Optional legacy Telegram demo:

```powershell
$env:TELEGRAM_BOT_TOKEN="paste-your-token-here"
.\venv\Scripts\python.exe optional_integrations\telegram_bot.py
```

Live Telegram steps, only if time permits:

1. Send `/start`.
2. Choose exercise.
3. Upload workout photo.
4. Show returned annotated image and report.

## Slide 10: Limitations and Future Work

Current limitations:

- Only supports four exercises.
- Works best with one clear full-body image.
- Camera angle can reduce accuracy.
- Does not analyze full movement over time.
- Not a replacement for professional coaching or medical advice.

Future work:

- Support video-based repetition tracking.
- Add more exercises.
- Add confidence score for landmark visibility.
- Generate PDF reports.
- Store progress history for users.
