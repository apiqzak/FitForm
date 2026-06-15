# FitForm Assistant

FitForm Assistant is an OpenClaw-first computer vision skill for checking workout posture from an uploaded image or short video. A user uploads workout media in OpenClaw, enters a simple prompt such as `analyze squat`, and receives an annotated output plus a posture feedback report.

## Primary Workflow

```text
User uploads image/video + enters prompt in OpenClaw
-> OpenClaw FitForm skill
-> analyze_cli.py
-> test_pose.py image backend or video_analyzer.py video bridge
-> annotated image/video + text report + JSON output
```

OpenClaw is the main assignment demo interface. Telegram is kept only as an optional/legacy extra integration.

## Supported Exercises

- Squat
- Pushup
- Plank
- Pullup

## Scope

FitForm Assistant is limited to sports science and workout posture analysis. It only supports exercise-form feedback for the four supported exercises listed above.

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

If a user asks about something outside sports science, FitForm should politely explain that it only supports sports-science-related workout posture analysis.

Recommended response:

```text
FitForm only supports sports-science-related workout posture analysis.

I can help analyze squat, pushup, plank, or pullup form from a clear image or short video.
```

## Target User

The target users are fitness beginners, physical education students, sports club members, and non-technical users who want quick visual feedback on basic workout form.

## Real-World Problem

Beginners often cannot tell whether their body alignment, joint angles, or exercise depth are correct from a photo or short clip. FitForm helps users inspect their form quickly using computer vision and gives simple corrective feedback.

## Computer Vision Method

The system uses MediaPipe Pose Landmarker for pose estimation. MediaPipe detects human body landmarks such as shoulders, elbows, hips, knees, ankles, and wrists. The project then calculates joint angles using vector geometry and applies rule-based exercise form checks.

Main CV concepts used:

- Image/video acquisition from uploaded or local files
- Person pose detection
- Keypoint and pose feature extraction
- Joint angle calculation
- Visual localization using skeleton overlays
- Media-to-report conversion

## Project Files

- `test_pose.py`: reusable CV/posture analysis backend
- `analyze_cli.py`: official integration bridge for OpenClaw and other tools
- `video_analyzer.py`: video frame sampling, annotation, and summary generation
- `skills/fitform/SKILL.md`: OpenClaw FitForm skill instructions
- `docs/OPENCLAW_SKILL_PROMPT.md`: standalone OpenClaw prompt/reference
- `pose_landmarker.task`: MediaPipe pose model
- `requirements.txt`: Python dependencies
- `optional_integrations/telegram_bot.py`: optional/legacy Telegram integration
- `docs/WORKOUT_POSTURE_SKILL.md`: assignment skill design document
- `docs/PHASE_5_TESTING_GUIDE.md`: testing and demo checklist
- `docs/PRESENTATION_OUTLINE.md`: slide-by-slide presentation guide
- `docs/DEMO_EVIDENCE.md`: evidence and test result log
- `samples/images/`: sample workout images
- `samples/videos/`: sample workout videos
- `outputs/final_demo/`: selected final demo evidence files

## Setup

This project is tested on Windows PowerShell. In OpenClaw or PowerShell, do not use Linux Bash heredoc syntax such as `python - <<'PY'`; PowerShell treats `<` differently and the command will fail.

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

If you are using the project virtual environment, prefer:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Check core dependencies with a PowerShell-safe command:

```powershell
.\venv\Scripts\python.exe -c "import importlib.util; mods=['cv2','mediapipe','numpy']; [print(m, bool(importlib.util.find_spec(m))) for m in mods]"
```

## Test The CLI Bridge

Run this from the project folder:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\images\squat.jpg --exercise squat --media-type auto --output outputs\temp\openclaw_output.jpg --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --quiet
```

Expected output files:

- `outputs/temp/openclaw_output.jpg`
- `outputs/temp/openclaw_report.txt`
- `outputs/temp/openclaw_report.json`

This confirms the OpenClaw integration bridge can call the posture analysis backend.

For video input, use a short clip first:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\videos\squat\squat_27.mp4 --exercise squat --media-type auto --output outputs\temp\openclaw_output.mp4 --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --representative-frame outputs\temp\openclaw_keyframe.jpg --frame-step 5 --max-seconds 30 --quiet
```

Expected video output files:

- `outputs/temp/openclaw_output.mp4`
- `outputs/temp/openclaw_keyframe.jpg`
- `outputs/temp/openclaw_report.txt`
- `outputs/temp/openclaw_report.json`

Check video metadata with OpenCV, not `ffprobe`:

```powershell
.\venv\Scripts\python.exe -c "import cv2; p='samples/videos/squat/squat_27.mp4'; cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS); frames=cap.get(cv2.CAP_PROP_FRAME_COUNT); w=cap.get(cv2.CAP_PROP_FRAME_WIDTH); h=cap.get(cv2.CAP_PROP_FRAME_HEIGHT); print('fps=', fps); print('frames=', frames); print('width=', w); print('height=', h); print('duration_sec=', frames/fps if fps else 0); cap.release()"
```

`ffmpeg` and `ffprobe` are not required for the main workflow. Video processing uses OpenCV through `video_analyzer.py`.

## OpenClaw Demo Quick Start

1. Start or repair OpenClaw local mode if needed:

```powershell
openclaw onboard --mode local
```

2. Start the OpenClaw gateway:

```powershell
openclaw gateway --port 18789
```

Keep this terminal open.

3. Open the dashboard in another terminal:

```powershell
openclaw dashboard
```

4. Make sure the FitForm skill is available:

```powershell
openclaw skills check
```

If `fitform` does not appear, copy the workspace skill into OpenClaw's local skills folder:

```powershell
mkdir "$env:USERPROFILE\.openclaw\skills\fitform"
copy ".\skills\fitform\SKILL.md" "$env:USERPROFILE\.openclaw\skills\fitform\SKILL.md"
```

5. In OpenClaw, upload a clear workout image or short video and type a natural request:

```text
analyze squat
```

Other examples:

```text
analyze pushup
check my plank
analyze pullup
Can you check my squat form?
Is my pushup okay?
Analyze this plank video
What should I fix first?
Explain my result in simple words
```

FitForm should extract the exercise from natural wording when possible. If the exercise is missing, it asks which exercise to analyze. If the file is missing, it asks the user to upload a clear full-body photo or short video. If the user asks about a previous report, it explains the result in simple language instead of rerunning analysis unnecessarily.

Expected response:

- annotated posture image/video
- representative frame for video input
- exercise type
- detected phase
- score
- score explanation when requested
- main feedback
- suggested follow-up questions
- safety note

## Annotated Output Design

The annotated image/video uses a simple visual legend:

- Green = good posture check
- Yellow = warning or minor adjustment
- Red = poor posture check
- White/gray = neutral body landmark

The output shows:

- skeleton overlay on the person
- highlighted body landmarks
- joint angle labels
- exercise phase
- GOOD/WARN/BAD check counts
- joint angle table
- feedback list
- final score

## Score Calculation

FitForm uses a simple rule-based score:

```text
score = passed posture checks / total posture checks
```

A passed check is any item marked `[GOOD]`. Items marked `[WARN]` or `[BAD]` are not counted as passed because they show something the user may need to improve.

The total includes the camera-angle check plus the exercise-specific posture checks. For example, a `3/5` score means 3 out of 5 visible posture checks passed.

For video analysis, FitForm calculates a score for each sampled frame where a pose is detected, then reports the average score across those sampled frames.

OpenClaw responses should be clean and user-facing. Do not show internal PowerShell commands, workspace search logs, raw JSON, or tracebacks during the demo. The CLI supports `--quiet` for this purpose and writes debug details to `outputs/temp/fitform_debug.log` when needed.

For OpenClaw Telegram or any chat-style demo, use final-answer-only behavior: the user should see only the processing acknowledgement, final FitForm summary, generated media, and friendly errors. Intermediate OpenClaw/tool events such as PowerShell commands, `Get-ChildItem`, Python snippets, stdout/stderr, `Tidepooling`, and workspace scans should be hidden or logged internally.

The optional Telegram entrypoint suppresses internal OpenClaw-style traces by default and stores them in `outputs/temp/openclaw_telegram_debug.log`. This includes messages like `Using the fitform skill`, `Get-ChildItem`, `rg --files`, `Command "..."`, PowerShell snippets, and raw tool/status blocks.

Only enable Telegram trace debugging while developing:

```powershell
$env:FITFORM_DEBUG_TELEGRAM="1"
```

For normal demos, leave `FITFORM_DEBUG_TELEGRAM` unset.

FitForm should also keep the conversation open by ending clean responses with a short `You can also ask me:` section. Good follow-up prompts include:

- `What should I fix first?`
- `Why did I get this warning?`
- `Can you explain my score?`
- `How can I improve my squat form?`
- `Can I try another image or video?`

## Friendly Error Handling

FitForm should fail clearly and politely when the input is not suitable. It gives short user-facing messages for:

- missing file or inaccessible upload
- unsupported file type
- unsupported exercise
- image/video media-type mismatch
- no clear pose detected
- no sampled video frame with a detectable pose
- invalid video settings such as `--max-seconds 0`
- invalid frame sampling settings such as `--frame-step 0`

Detailed tracebacks and internal logs stay in `outputs/temp/fitform_debug.log` instead of being shown during the demo.

## Local Backend Test

You can still run the backend directly:

```powershell
.\venv\Scripts\python.exe test_pose.py
```

Enter an image filename such as:

```text
samples\images\squat.jpg
```

Then choose the exercise:

```text
squat
```

The output is saved as:

```text
output.jpg
```

## Optional Legacy Telegram Integration

`telegram_bot.py` is kept as an optional extra interface. It is not the primary assignment workflow.

To use it, create a Telegram bot token using BotFather and set it as an environment variable:

```powershell
pip install -r optional_integrations\requirements-telegram.txt
```

```powershell
$env:TELEGRAM_BOT_TOKEN="paste-your-token-here"
.\venv\Scripts\python.exe optional_integrations\telegram_bot.py
```

Never commit a real Telegram token. If a token was ever committed or shared, revoke/regenerate it in BotFather.

The legacy Telegram bot filters internal-looking messages by default. Analyzer output is captured in `outputs/temp/fitform_debug.log`, while suppressed OpenClaw/Telegram trace messages are stored in `outputs/temp/openclaw_telegram_debug.log`. To intentionally allow Telegram trace debugging while developing, set:

```powershell
$env:FITFORM_DEBUG_TELEGRAM="1"
```

## Limitations

- Works best with one person in the image/video.
- Needs clear visibility of the full body.
- Image analysis checks one moment only.
- Video analysis samples selected frames, so very long or blurry videos may be slower or less accurate.
- Camera angle can affect landmark accuracy.
- The system is limited to sports science and workout posture analysis only.
- The feedback is educational and should not replace a coach, trainer, doctor, or physiotherapist.

## Ethical Boundary

The system only analyzes exercise posture from visible body landmarks. It does not identify the person, judge attractiveness, infer health conditions, diagnose injuries, or provide medical advice.
