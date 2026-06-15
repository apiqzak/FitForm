# Demo Evidence and Evaluation Log

Use this file to record screenshots, test cases, and presentation evidence.

## Test Environment

- Operating system:
- Python version:
- Main libraries:
  - MediaPipe
  - OpenCV
  - NumPy
- Main demo interface:
  - OpenClaw FitForm skill
- Backend/integration:
  - `analyze_cli.py`
  - `test_pose.py`
  - `video_analyzer.py`
- Optional extra interface:
  - Telegram bot

## Test Case Summary

| Test ID | Exercise | Input Media | Interface | Expected Output | Result | Notes |
|---|---|---|---|---|---|---|
| T1 | Squat | `samples/images/squat.jpg` | CLI bridge | Annotated image + squat report + JSON | Pass |  |
| T2 | Squat | uploaded photo | OpenClaw | Annotated image + squat report | Pass |  |
| T3 | Pushup | uploaded photo | OpenClaw | Annotated image + pushup report | Pending |  |
| T4 | Pullup | uploaded photo | OpenClaw | Annotated image + pullup report | Pending |  |
| T5 | Squat | short video | CLI bridge | Annotated video + keyframe + video report + JSON | Pending |  |
| T6 | Squat | uploaded short video | OpenClaw | Annotated video/keyframe + squat summary | Pending |  |
| T7 | Multiple videos | `samples/videos/` folders | Batch tester | Best demo video selected for each exercise | Pending |  |
| T8 | Natural prompt | uploaded media | OpenClaw | Exercise extracted and analysis runs | Pending | `Can you check my squat form?` |
| T9 | Missing exercise | uploaded media | OpenClaw | Asks which exercise to analyze | Pending | `I uploaded a video, can you analyze it?` |
| T10 | Previous result question | latest report | OpenClaw | Explains report without rerunning | Pending | `What should I fix first?` |
| T11 | Unsupported exercise | uploaded media | OpenClaw | Offers supported exercises only | Pending | `Can you check my deadlift?` |
| T12 | Invalid/unclear media | uploaded file | OpenClaw | No-pose or visibility warning | Pending |  |
| T13 | Follow-up suggestions | any clean response | OpenClaw | Shows short suggested next questions | Pending | `You can also ask me:` |

## CLI Bridge Evidence

Use Windows PowerShell commands. Do not use Bash heredoc syntax such as `python - <<'PY'`. Video metadata checks should use OpenCV, not `ffprobe`.

Command:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\images\squat.jpg --exercise squat --media-type auto --output outputs\temp\openclaw_output.jpg --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --quiet
```

Evidence to capture:

- Terminal report
- `outputs/temp/openclaw_output.jpg`
- `outputs/temp/openclaw_report.txt`
- `outputs/temp/openclaw_report.json`

Video command:

```powershell
.\venv\Scripts\python.exe analyze_cli.py --input samples\videos\squat\squat_27.mp4 --exercise squat --media-type auto --output outputs\temp\openclaw_output.mp4 --report outputs\temp\openclaw_report.txt --json outputs\temp\openclaw_report.json --representative-frame outputs\temp\openclaw_keyframe.jpg --frame-step 5 --max-seconds 30 --quiet
```

Video evidence to capture:

- Terminal summary
- `outputs/temp/openclaw_output.mp4`
- `outputs/temp/openclaw_keyframe.jpg`
- `outputs/temp/openclaw_report.txt`
- `outputs/temp/openclaw_report.json`

Video metadata command:

```powershell
.\venv\Scripts\python.exe -c "import cv2; p='samples/videos/squat/squat_27.mp4'; cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS); frames=cap.get(cv2.CAP_PROP_FRAME_COUNT); w=cap.get(cv2.CAP_PROP_FRAME_WIDTH); h=cap.get(cv2.CAP_PROP_FRAME_HEIGHT); print('fps=', fps); print('frames=', frames); print('width=', w); print('height=', h); print('duration_sec=', frames/fps if fps else 0); cap.release()"
```

## Batch Video Testing Evidence

Use batch testing to compare multiple candidate videos and select the best demo evidence for each exercise. This is for evaluation and presentation selection only, not for training a model.

Command:

```powershell
.\venv\Scripts\python.exe batch_video_test.py --input-dir samples\videos --output-dir outputs\batch_video_results --frame-step 5 --max-seconds 30
```

Folder aliases such as `push up/` and `pull up/` are accepted, but the cleaned project uses `pushup/` and `pullup/`.

Evidence to capture:

- Terminal batch summary
- `outputs/batch_video_results/batch_summary.csv`
- `outputs/batch_video_results/batch_summary.json`
- `outputs/batch_video_results/best_results.md`
- `outputs/batch_video_results/squat/best_output.mp4`
- `outputs/batch_video_results/squat/best_keyframe.jpg`
- best output files for any other exercise used in the presentation

Best-result rule:

1. Highest average score
2. Highest frames with pose
3. Lowest frames without pose
4. Shorter processing duration
5. Alphabetical filename

## Cleanup Evidence

After selecting the best result for each exercise, preview cleanup first:

```powershell
.\venv\Scripts\python.exe cleanup_best_videos.py --input-dir samples\videos --results-dir outputs\batch_video_results --dry-run
```

Actual cleanup command:

```powershell
.\venv\Scripts\python.exe cleanup_best_videos.py --input-dir samples\videos --results-dir outputs\batch_video_results --confirm-delete
```

Evidence to capture:

- Dry-run terminal output
- Actual cleanup terminal output if deletion is performed
- `outputs/batch_video_results/cleanup_summary.md`
- Remaining `best_output.mp4`, `best_keyframe.jpg`, `best_report.txt`, and `best_report.json` for each exercise

This cleanup is only for organizing final demo evidence. It does not train a model and does not change the posture analysis rules.

## OpenClaw Demo Evidence

OpenClaw is the main assignment demo interface.

OpenClaw steps:

1. Start OpenClaw gateway.
2. Open OpenClaw dashboard.
3. Upload a workout image or short video.
4. Type a simple prompt such as `analyze squat`.
5. Save screenshot of annotated image/video/keyframe response.
6. Save screenshot of text report response.

Screenshot filenames:

- `evidence/openclaw_start.png`
- `evidence/openclaw_upload.png`
- `evidence/openclaw_video_upload.png`
- `evidence/openclaw_annotated_result.png`
- `evidence/openclaw_video_result.png`
- `evidence/openclaw_text_report.png`

## Clean Response Evidence

Capture one screenshot proving that the user-facing response is clean. It should show the final FitForm result only, not internal command text.

The chat should be final-answer-only. The user may see a short processing acknowledgement, then the final FitForm summary and generated media. Intermediate OpenClaw/tool events should not be forwarded to Telegram or the user chat.

Check that the response does not include:

- PowerShell commands
- `Get-ChildItem`
- `Command "..."`
- `Tidepooling`
- Python snippets such as `import cv2`
- workspace scanning logs
- raw stdout/stderr
- raw JSON dumps
- full local paths unless debugging was requested
- Python tracebacks

Also check that the response ends with a short follow-up section such as:

```text
You can also ask me:
- What should I fix first?
- Why did I get this warning?
- Can you explain my score?
```

If an error occurs, capture the friendly error message and keep technical details in `outputs/temp/fitform_debug.log`. Raw debug output should only be visible when debug mode is explicitly enabled.

Suppressed OpenClaw/Telegram trace messages should be saved locally in `outputs/temp/openclaw_telegram_debug.log`, not shown to the user. Keep `FITFORM_DEBUG_TELEGRAM` unset during the demo.

## Open-Ended Prompt Evidence

Capture screenshots showing that OpenClaw understands flexible user wording:

- `Can you check my squat form?`
- `I uploaded a video, can you analyze it?`
- `What should I fix first?`
- `Explain my result`
- `Can you check my deadlift?`
- `Help`

Expected evidence:

- Exercise is extracted when clearly mentioned.
- Missing exercise triggers a short clarification.
- Missing file triggers an upload request.
- Previous-result questions are explained in simple words.
- Unsupported exercises are handled politely.
- Responses suggest useful follow-up questions without exposing tool logs.
- Ethical boundary remains non-medical and posture-focused.

## Successful OpenClaw Result

Observed output:

```text
Analysis complete.

Exercise: squat
Phase: BOTTOM POSITION
Score: 3/5 checks passed

Main feedback:
- [WARN] Camera angle: DIAGONAL view detected, FRONT view recommended for squat
- [GOOD] Knee depth: Full squat depth achieved
- [GOOD] Hip hinge: Good forward lean
- [WARN] Back: Slight forward lean, keep chest up
- [GOOD] Knee symmetry: Both knees balanced

Annotated image: openclaw_output.jpg
Report file: openclaw_report.txt
JSON report: openclaw_report.json
```

Result:

```text
Pass
```

Conclusion:

OpenClaw successfully acted as the skill interface and called `analyze_cli.py`, which connected to the MediaPipe posture analysis backend in `test_pose.py`.

For video input, `analyze_cli.py` should route to `video_analyzer.py`, sample frames, reuse the same posture rules from `test_pose.py`, and generate an annotated video plus a representative frame.

## Optional Legacy Telegram Evidence

Telegram is optional/legacy and is not the main assignment workflow.

Command:

```powershell
$env:TELEGRAM_BOT_TOKEN="paste-your-token-here"
.\venv\Scripts\python.exe optional_integrations\telegram_bot.py
```

Never commit or share a real Telegram token. If a token was exposed, revoke/regenerate it in BotFather.

## Evaluation Questions

Answer these after testing:

1. Did the system detect the body landmarks correctly?
2. Were the skeleton and angle labels visible?
3. Did the feedback match the visible posture?
4. Was the camera angle warning useful?
5. Did the output help the user decide what to adjust?
6. Did the system handle unclear or invalid input properly?
7. For video, did the summary reflect the sampled frames clearly?
8. Did OpenClaw handle natural prompts and follow-up questions correctly?

## Known Limitations Observed

-

## Improvements Made After Testing

-

## Final Demo Checklist

- CLI bridge works.
- OpenClaw FitForm skill works.
- OpenClaw receives or uses image/video input.
- OpenClaw asks for or accepts exercise type.
- OpenClaw returns annotated image/video or generated media path.
- OpenClaw returns text report.
- OpenClaw handles natural prompts, missing information, and report explanation questions.
- OpenClaw keeps internal commands/logs out of the user-facing response.
- Limitations and ethical boundary are explained in presentation.
