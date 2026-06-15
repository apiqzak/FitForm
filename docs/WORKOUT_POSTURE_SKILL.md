# Workout Posture Analysis Skill

## Skill Name

Workout Posture Analysis Assistant

## Target User

Fitness beginners, physical education students, sports club members, and non-technical users who want quick feedback on basic workout form from a photo or short video.

## Scope

This skill is limited to sports science and workout posture analysis. It supports exercise-form feedback for squat, pushup, plank, and pullup only.

In scope:

- Analyzing squat, pushup, plank, and pullup posture
- Explaining joint angles, exercise phase, score, and posture feedback
- Giving camera-angle guidance for workout analysis
- Explaining previous FitForm results in beginner-friendly language
- Producing annotated image/video outputs and reports

Out of scope:

- Exercises other than squat, pushup, plank, and pullup
- Non-sports-science school subjects
- General chatbot or entertainment requests
- Nutrition planning or diet advice
- Medical diagnosis, injury diagnosis, or treatment advice
- Identifying people or judging body appearance
- General image/video analysis that is not workout posture related

Requests outside sports science or workout posture should be politely redirected back to supported workout posture analysis.

## Real-World Problem

Many beginners practice exercises without knowing whether their joint alignment, body posture, or movement depth is correct. They may not have immediate access to a coach. This skill helps users inspect their workout form from an image or sampled video frames and receive understandable feedback.

## Input Format

The skill accepts a workout image or short video showing one person performing one supported exercise.

Supported exercises:

- Squat
- Pushup
- Plank
- Pullup

Accepted input sources:

- OpenClaw uploaded image/video or file path through `analyze_cli.py` (primary workflow)
- Local image file for `test_pose.py` (backend/debug workflow)
- Telegram photo upload for `optional_integrations/telegram_bot.py` (optional legacy extra)

The user must also provide or select the exercise type.

## OpenClaw Tool Interface

OpenClaw is the main user interface for the assignment demo. It should use `skills/fitform/SKILL.md` or `docs/OPENCLAW_SKILL_PROMPT.md` as the skill instructions and call `analyze_cli.py` as the backend tool bridge.

The skill should accept natural user wording, not only fixed commands. Examples include:

- `Can you check my squat form?`
- `Is my pushup okay?`
- `Analyze this plank video`
- `Please review my pullup`
- `What should I fix first?`
- `Explain my result in simple words`

If the exercise is clear, the skill should normalize it and run the CLI. If the exercise is missing, it should ask which supported exercise to analyze. If the file is missing, it should ask the user to upload an image or short video. If the user asks about a previous result, it should explain the latest report in beginner-friendly language instead of rerunning analysis unnecessarily.

Preferred flow:

```text
User uploads image/video + enters prompt in OpenClaw
-> FitForm skill
-> analyze_cli.py
-> test_pose.py or video_analyzer.py
-> annotated image/video + report + JSON
```

Example command:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input "samples\images\squat.jpg" --exercise "squat" --media-type auto --output "outputs\temp\openclaw_output.jpg" --report "outputs\temp\openclaw_report.txt" --json "outputs\temp\openclaw_report.json" --quiet
```

Example video command:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input "samples\videos\squat\squat_27.mp4" --exercise "squat" --media-type auto --output "outputs\temp\openclaw_output.mp4" --report "outputs\temp\openclaw_report.txt" --json "outputs\temp\openclaw_report.json" --representative-frame "outputs\temp\openclaw_keyframe.jpg" --frame-step 5 --max-seconds 30 --quiet
```

The OpenClaw response should return or display the annotated image, annotated video, or representative keyframe and summarize the generated text report.

The OpenClaw response should be user-facing and clean. It should not expose internal PowerShell commands, file-search commands, workspace scans, raw stdout/stderr, raw JSON, full tracebacks, or full local paths unless the user explicitly asks for debugging details. Detailed debug information belongs in `outputs/temp/fitform_debug.log`.

For Telegram or chat-style use, the skill should be final-answer-only. The user should receive a short acknowledgement, final FitForm summary, generated media, and friendly errors only. Intermediate OpenClaw events such as tool calls, tool results, command output, `Tidepooling`, Python snippets, and workspace scans should be ignored or logged internally.

The project is tested on Windows PowerShell. OpenClaw instructions should not use Linux Bash heredocs such as `python - <<'PY'`. Video metadata should be read with OpenCV through Python, not `ffprobe`. `ffmpeg` and `ffprobe` are optional external tools and are not required for the main FitForm workflow.

## Computer Vision or Image-Processing Method

The skill uses MediaPipe Pose Landmarker to detect human pose landmarks. These landmarks are normalized body keypoints such as shoulders, elbows, hips, knees, ankles, and wrists.

After landmark detection, the system performs:

- Pose keypoint extraction
- Joint angle calculation using three landmark points
- Camera angle estimation using shoulder and hip spacing
- Exercise phase detection
- Rule-based form analysis
- Skeleton and feedback visualization on the output image or sampled video frames

## Step-by-Step Workflow

1. Receive image/video and exercise type.
2. Load the media using OpenCV through the CLI bridge.
3. Run MediaPipe Pose Landmarker on the image or sampled video frame.
4. If no pose is detected, return a full-body visibility warning.
5. Extract body landmarks for the first detected person.
6. Detect approximate camera angle.
7. Calculate exercise-specific joint angles:
   - Squat: knees, hip hinge, back alignment
   - Pushup: elbows, body line, elbow flare
   - Plank: body line, hip position, shoulder angle
   - Pullup: elbows, shoulder elevation, body alignment
8. Detect exercise phase, such as bottom position, top position, hold position, or mid-rep.
9. Compare angles against rule-based thresholds.
10. Generate feedback messages and pass/fail status.
11. Draw skeleton, joint angle labels, and feedback panel.
12. Save and return the annotated image or annotated video.
13. For video, save an optional representative annotated frame.
14. Return a structured text report with score, joint angles, feedback, and limitations.

## Output Format

The skill outputs:

- Annotated image or video with skeleton and joint angles
- Representative annotated frame for video input, if generated
- Exercise name
- Detected phase
- Camera angle recommendation
- Joint angle table
- Feedback list
- Score such as `3/5 checks passed`
- Score explanation showing how passed checks are counted
- Limitation or visibility warning when needed

## Annotated Output Design

The annotated media is designed to be readable in OpenClaw or Telegram-style demos. It uses:

- Green landmarks/feedback for passed checks
- Yellow landmarks/feedback for warnings or minor adjustments
- Red landmarks/feedback for poor posture checks
- White/gray landmarks for neutral body points
- Thicker skeleton lines with visible angle labels
- A bottom report panel with phase, legend, check counts, joint angles, feedback, and score

## Score Calculation

FitForm uses a transparent rule-based score:

```text
score = passed posture checks / total posture checks
```

Each `[GOOD]` feedback item counts as one passed check. `[WARN]` and `[BAD]` items do not count as passed because they indicate possible form issues or limitations.

The total includes the camera-angle check and the exercise-specific posture checks. For video analysis, the system scores each sampled frame with detected pose landmarks and reports the average score.

Example output summary:

```text
Exercise: SQUAT
Phase: BOTTOM POSITION
Score: 4/5 checks passed

Joint Angles:
- Left Knee: 95 deg
- Right Knee: 101 deg
- Hip Hinge: 82 deg
- Back Alignment: 158 deg

Feedback:
- [GOOD] Camera angle: FRONT view, ideal for squat
- [GOOD] Knee depth: Full squat depth achieved
- [WARN] Knee symmetry: Uneven, check for knee caving
```

## Limitation Handling

The skill handles limitations by giving warnings when:

- No pose is detected
- The image/video does not show the full body
- The camera angle is not ideal for the selected exercise
- The photo captures a mid-repetition position
- The video has frames where no pose is detected
- The video is long, blurry, or sampled rather than analyzed frame-by-frame
- The result may be affected by an angled shot

The system is designed to fail gracefully with a clear user-facing message instead of producing silent or confusing output.

## Ethical Boundary

The skill does not identify the person, judge body appearance, rate attractiveness, infer private attributes, diagnose injuries, or replace medical advice. It only evaluates visible exercise posture using body landmarks.

The feedback should be treated as educational guidance. Users with pain, injury, or medical concerns should consult a qualified coach, trainer, doctor, or physiotherapist.

The skill should also stay within its sports science scope. It should not answer unrelated topics outside workout posture analysis.

## Why Computer Vision Is Needed

The input is visual body posture. Plain text processing cannot measure joint alignment or body angles from a workout photo or video. Pose estimation is needed to locate body joints, and media annotation is needed to show the user where the analysis comes from.

## Practical Recommendation

The output helps users decide what to adjust next, such as:

- Squat deeper
- Keep chest up
- Tighten core
- Tuck elbows closer
- Keep hips level
- Control swinging during pullups

This turns the visual input into actionable exercise feedback.
