# Phase 5 Testing, Refinement, and Presentation Prep

Related documents:

- `README.md`: project overview and setup
- `docs/WORKOUT_POSTURE_SKILL.md`: formal skill file for assignment requirements
- `docs/OPENCLAW_SKILL_PROMPT.md`: OpenClaw skill prompt and command workflow
- `docs/PRESENTATION_OUTLINE.md`: slide-by-slide presentation plan
- `docs/DEMO_EVIDENCE.md`: testing evidence and screenshot log

## Local Analyzer Test

All commands in this guide are Windows PowerShell-compatible. Do not use Bash heredoc commands such as `python - <<'PY'` in OpenClaw or PowerShell. `ffmpeg` and `ffprobe` are optional tools and are not required for the main FitForm workflow.

Check dependencies:

```powershell
.\venv\Scripts\python.exe -c "import importlib.util; mods=['cv2','mediapipe','numpy']; [print(m, bool(importlib.util.find_spec(m))) for m in mods]"
```

Run the original analyzer flow:

```powershell
.\venv\Scripts\python.exe test_pose.py
```

Try each sample image:

- `samples/images/squat.jpg` with `squat`
- `samples/images/pushup.jpg` with `pushup`
- `samples/images/pullup.jpg` with `pullup`
- `samples/images/workout.jpg` with the matching exercise you want to demonstrate

Expected result:

- `output.jpg` is generated
- pose skeleton and joint angles are visible
- bottom panel shows exercise, phase, color legend, check counts, score, joint angles, and feedback
- angle labels and skeleton should remain readable in a Telegram/OpenClaw screenshot

## OpenClaw Bridge Test

Run the command-line bridge that OpenClaw will call for image input:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\images\squat.jpg --exercise squat --media-type auto --output outputs\temp\openclaw_output.jpg --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --quiet
```

Expected result:

- `outputs/temp/openclaw_output.jpg` is generated
- `outputs/temp/openclaw_report.txt` contains the readable report
- `outputs/temp/openclaw_report.json` contains structured output
- The terminal prints only a short clean summary

Run the bridge for video input with a short clip:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\videos\squat\squat_27.mp4 --exercise squat --media-type auto --output outputs\temp\openclaw_output.mp4 --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --representative-frame outputs\temp\openclaw_keyframe.jpg --frame-step 5 --max-seconds 30 --quiet
```

Expected result:

- `outputs/temp/openclaw_output.mp4` is generated
- `outputs/temp/openclaw_keyframe.jpg` is generated when at least one representative frame is available
- `outputs/temp/openclaw_report.txt` contains the readable video summary
- `outputs/temp/openclaw_report.json` contains structured video output

Check video metadata using OpenCV:

```powershell
.\venv\Scripts\python.exe -c "import cv2; p='samples/videos/squat/squat_27.mp4'; cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS); frames=cap.get(cv2.CAP_PROP_FRAME_COUNT); w=cap.get(cv2.CAP_PROP_FRAME_WIDTH); h=cap.get(cv2.CAP_PROP_FRAME_HEIGHT); print('fps=', fps); print('frames=', frames); print('width=', w); print('height=', h); print('duration_sec=', frames/fps if fps else 0); cap.release()"
```

## Clean Response Test

During OpenClaw or Telegram-style demos, the user-facing chat should show only the final FitForm result. It should not show PowerShell commands, `Get-ChildItem`, workspace scanning output, raw stdout/stderr, raw JSON dumps, or full tracebacks.

Final-answer-only means the user should see only:

- a short processing acknowledgement
- the final FitForm summary
- annotated image/video/keyframe if available
- a friendly error message if analysis fails

Intermediate OpenClaw/tool events should be ignored or saved to `outputs/temp/openclaw_telegram_debug.log`, not forwarded to Telegram/chat. Analyzer stdout/stderr can stay in `outputs/temp/fitform_debug.log`.

Expected clean response shape:

```text
Analysis complete!

Exercise: Squat
Media type: Video
Score: 3/5

Main feedback:
- Good knee depth
- Slight forward lean detected
- Camera angle may affect accuracy

You can also ask me:
- What should I fix first?
- Why did I get this warning?
- Can you explain my score?
- How can I improve my squat form?
```

If analysis fails, the response should be short and friendly. Detailed debug information should stay in `outputs/temp/fitform_debug.log`.

Legacy Telegram trace debug mode is off by default. Only enable raw trace behavior while developing:

```powershell
$env:FITFORM_DEBUG_TELEGRAM="1"
```

For normal demos, leave `FITFORM_DEBUG_TELEGRAM` unset.

## OpenClaw Skill Demo Test

After installing or copying the FitForm skill into OpenClaw, upload a clear workout image or short video and use a simple prompt in the OpenClaw dashboard:

```text
analyze squat
```

Expected result:

- OpenClaw runs `analyze_cli.py`
- `openclaw_output.jpg` is created for image input, or `openclaw_output.mp4` is created for video input
- `openclaw_keyframe.jpg` is created for video input when possible
- `openclaw_report.txt` is created
- `openclaw_report.json` is created
- OpenClaw replies with exercise, phase, score, main feedback, and ethical note
- OpenClaw includes a short `You can also ask me:` follow-up section

Successful sample result:

```text
Exercise: squat
Phase: BOTTOM POSITION
Score: 3/5 checks passed
```

## Open-Ended Prompt Test

Test that FitForm behaves like a helpful assistant, not only a fixed-command bot.

Try these prompts in OpenClaw:

- `Can you check my squat form?`
- `I uploaded a video, can you analyze it?`
- `What should I fix first?`
- `Explain my result`
- `Can you check my deadlift?`
- `Can you solve my math homework?`
- `Help`

Expected behavior:

- If the prompt clearly mentions `squat`, `pushup`, `plank`, or `pullup`, FitForm uses that exercise.
- If analysis is requested but the exercise is missing, FitForm asks: `Which exercise should I analyze: squat, pushup, plank, or pullup?`
- If the exercise is given but no image/video is uploaded, FitForm asks for a clear full-body photo or short video.
- If the user asks about a previous result, FitForm explains the report in simple words instead of rerunning analysis.
- If the user asks `Can you explain my score?`, FitForm explains that the score is passed posture checks divided by total checks.
- If the user asks for an unsupported exercise such as deadlift, FitForm offers only squat, pushup, plank, and pullup.
- If the user asks about a topic outside sports science or workout posture, such as math homework, FitForm explains that it only supports sports-science-related workout posture analysis.
- If the uploaded file is missing, unsupported, mismatched, or has no detectable pose, FitForm gives a short friendly error instead of a traceback.
- If the user asks for help, FitForm briefly explains supported inputs, exercises, outputs, and limitations.
- Clean responses end with short suggested follow-up questions such as explaining warnings, explaining the score, choosing what to fix first, or trying another image/video.

## Batch Video Demo Selection Test

Use this when you have several candidate videos and want to automatically select the strongest demo evidence for each exercise. This is only for testing and demo selection, not for training a model.

Expected input structure:

```text
samples/videos/
├── squat/
├── pushup/
├── plank/
└── pullup/
```

The script also accepts common folder aliases such as `push up/` and `pull up/`, but the cleaned project uses `pushup/` and `pullup/`.

Run:

```powershell
.\venv\Scripts\python.exe batch_video_test.py --input-dir samples\videos --output-dir outputs\batch_video_results --frame-step 5 --max-seconds 30
```

The script runs `analyze_cli.py` for every supported video file and saves:

- every individual result under `outputs/batch_video_results/<exercise>/all_results/`
- the selected best result under `outputs/batch_video_results/<exercise>/best_output.mp4`
- `outputs/batch_video_results/<exercise>/best_keyframe.jpg`
- `outputs/batch_video_results/<exercise>/best_report.txt`
- `outputs/batch_video_results/<exercise>/best_report.json`
- `outputs/batch_video_results/batch_summary.csv`
- `outputs/batch_video_results/batch_summary.json`
- `outputs/batch_video_results/best_results.md`

Best video selection priority:

1. Highest average score
2. Highest frames with pose
3. Lowest frames without pose
4. Shorter processing duration
5. Alphabetical filename

## Cleanup Non-Best Videos

After checking `outputs/batch_video_results/best_results.md`, you can remove non-best test videos and non-best generated outputs. Start with a dry run:

```powershell
.\venv\Scripts\python.exe cleanup_best_videos.py --input-dir samples\videos --results-dir outputs\batch_video_results --dry-run
```

Only after confirming the dry-run output, delete the non-best files:

```powershell
.\venv\Scripts\python.exe cleanup_best_videos.py --input-dir samples\videos --results-dir outputs\batch_video_results --confirm-delete
```

Optional final demo copy:

```powershell
.\venv\Scripts\python.exe cleanup_best_videos.py --input-dir samples\videos --results-dir outputs\batch_video_results --confirm-delete --move-best-to-final-demo
```

The cleanup script is cautious: if the best selection is missing, unclear, outside the selected folders, or missing required files, it skips that exercise.
## Refinement Checklist

- Use clear full-body photos with all major joints visible.
- Use short videos first, ideally under 30 seconds for the demo.
- Use front view for `squat` and `pullup`.
- Use side view for `pushup` and `plank`.
- Keep one person in the image/video.
- Test at least one good-form and one bad-form image for each exercise.
- Test at least one short video for one supported exercise.
- Test open-ended prompts, missing exercise handling, missing file handling, and unsupported exercise handling.
- Test `Can you explain my score?` after one successful analysis.
- Test one bad input case, such as an unsupported file type or a photo where no full body is visible.
- Test one unrelated non-sports-science prompt to confirm FitForm redirects back to workout posture analysis.
- Confirm OpenClaw does not expose command lines, file-search logs, raw JSON, or tracebacks in the chat response.
- Confirm OpenClaw/Telegram does not forward intermediate tool events such as `Tidepooling`, `Command "..."`, Python snippets, or workspace scans.
- Use `batch_video_test.py` to select the best demo video when several candidates are available.
- Save 2-3 successful OpenClaw screenshots for the presentation.

## Presentation Flow

1. Show Phase 1-3 result from `test_pose.py`.
2. Explain the four supported exercises and joint angles used.
3. Open the OpenClaw dashboard.
4. Upload a workout photo or short video and type a simple prompt such as `analyze squat`.
5. Show annotated image/video, report, score, and form feedback from OpenClaw.
6. Mention limitations: image analysis checks one moment, video analysis samples frames, camera angle sensitivity, and full-body visibility requirement.

## Submission Readiness Checklist

- `docs/WORKOUT_POSTURE_SKILL.md` explains skill name, target user, real problem, input, CV method, workflow, output, limitations, and ethical boundary.
- `docs/OPENCLAW_SKILL_PROMPT.md` explains how OpenClaw should call `analyze_cli.py`.
- `README.md` explains how to install and run the OpenClaw-first workflow.
- `docs/PRESENTATION_OUTLINE.md` follows the 10-slide structure from the instruction PDF.
- `docs/DEMO_EVIDENCE.md` contains test cases and screenshot placeholders.
- OpenClaw demo has been tested with at least one real photo.
- OpenClaw video path has been tested with at least one short clip if available.
- Annotated image/video output is shown in the presentation.

## Optional Legacy Telegram Test

Telegram is kept as an optional extra interface, not the main assignment demo.

```powershell
$env:TELEGRAM_BOT_TOKEN="paste-your-token-here"
.\venv\Scripts\python.exe optional_integrations\telegram_bot.py
```

Never commit or share a real Telegram token. If one was exposed, revoke/regenerate it in BotFather.
