# Video Support Implementation Plan

This is a planning document only. Video processing is not implemented yet.

## Current Working Flow

```text
OpenClaw upload + prompt
-> skills/fitform/SKILL.md
-> analyze_cli.py
-> test_pose.py
-> annotated image + text report + JSON report
```

## Reusable Image Analysis Parts

The following parts of `test_pose.py` can be reused for video frames:

- `VALID_EXERCISES`
- `IDEAL_CAMERA_ANGLES`
- `calculate_angle`
- `get_keypoint`
- `get_pixel`
- `draw_skeleton`
- `draw_angle_on_joint`
- `draw_angles_for_exercise`
- `build_status_map`
- `draw_feedback_panel`
- `analyze_squat`
- `analyze_pushup`
- `analyze_plank`
- `analyze_pullup`
- `detect_camera_angle`
- `get_angle_tip`
- `format_report`
- `create_landmarker`

## Image-Specific Parts To Refactor Later

`analyze_pose(...)` currently does too much for frame-by-frame video use:

- prints terminal output
- writes an output image path using `cv2.imwrite`
- optionally opens a GUI window
- combines analysis logic with drawing/output saving
- returns one image report only

For video, the analysis logic should be separated from image saving so each frame can be analyzed and annotated without writing thousands of temporary image files.

## Recommended Architecture

Keep `test_pose.py` as the posture-analysis backend, but add a small internal helper in a later phase:

```text
analyze_landmarks_for_exercise(landmarks, exercise)
```

This helper should return:

- exercise
- phase
- phase description
- camera angle
- angles
- feedback
- statuses
- score
- total

Then both image and video workflows can reuse the same analysis result.

Create a new file for video:

```text
video_analyzer.py
```

Recommended responsibility:

- open video with OpenCV
- sample frames
- run MediaPipe pose detection per selected frame
- call reusable posture-analysis helper
- draw skeleton and feedback on frames
- write annotated video
- aggregate frame reports into video summary
- save text and JSON reports

Avoid putting all video logic into `test_pose.py`, because that file is already large and should stay focused on shared posture rules.

## Future CLI Design

Extend `analyze_cli.py` without breaking current image commands.

Recommended arguments:

```powershell
python analyze_cli.py --input squat.jpg --exercise squat --media-type image --output output.jpg --report report.txt --json report.json
```

```powershell
python analyze_cli.py --input squat_video.mp4 --exercise squat --media-type video --output output.mp4 --report report.txt --json report.json --frame-step 5 --max-seconds 30
```

Recommended behavior:

- `--media-type image`: call `analyze_image_file(...)`
- `--media-type video`: call future `analyze_video_file(...)`
- `--media-type auto`: infer from file extension

Supported image extensions:

- `.jpg`
- `.jpeg`
- `.png`

Supported video extensions:

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`

## Proposed Video Output

For video analysis, produce:

- annotated video path, for example `fitform_video_output.mp4`
- text summary report, for example `fitform_video_report.txt`
- JSON report, for example `fitform_video_report.json`
- optional representative frame image, for example `fitform_video_keyframe.jpg`

## Proposed Video JSON Structure

```json
{
  "media_type": "video",
  "input_path": "squat_video.mp4",
  "exercise": "squat",
  "output_video_path": "fitform_video_output.mp4",
  "representative_frame_path": "fitform_video_keyframe.jpg",
  "report_path": "fitform_video_report.txt",
  "frame_step": 5,
  "fps": 30.0,
  "total_frames": 300,
  "processed_frames": 60,
  "frames_with_pose": 55,
  "frames_without_pose": 5,
  "average_score": 3.8,
  "total_checks": 5,
  "phase_counts": {
    "BOTTOM POSITION": 20,
    "MID POSITION": 25,
    "STANDING POSITION": 10
  },
  "common_feedback": [
    "[WARN] Camera angle: DIAGONAL view detected, FRONT view recommended for squat",
    "[GOOD] Hip hinge: Good forward lean"
  ],
  "warnings": [
    "Some frames had no detectable pose",
    "Video was sampled every 5 frames"
  ],
  "frame_reports": [
    {
      "frame_index": 5,
      "timestamp_sec": 0.17,
      "phase": "BOTTOM POSITION",
      "score": 3,
      "total": 5,
      "angles": {
        "Left Knee": 95.3,
        "Right Knee": 97.4
      },
      "feedback": []
    }
  ]
}
```

## Risks

- Video processing can be slow, especially with long clips.
- Large files may be awkward in OpenClaw workspace.
- Some frames may not detect body landmarks.
- Motion blur can reduce pose accuracy.
- Camera angle may change across the clip.
- Output video encoding may fail if codec/container settings are unsupported.
- Annotated feedback panel may make video width larger than original.
- Running MediaPipe on every frame may be unnecessary; frame sampling is safer.

## Files To Change In Later Phases

- `test_pose.py`: refactor shared landmark analysis into a reusable helper.
- `video_analyzer.py`: new file for video reading, frame analysis, video writing, and aggregation.
- `analyze_cli.py`: add `--media-type`, video extensions, and video output routing.
- `skills/fitform/SKILL.md`: update OpenClaw instructions to accept images or videos.
- `OPENCLAW_SKILL_PROMPT.md`: update standalone skill prompt for video.
- `README.md`: document video commands and limitations.
- `PHASE_5_TESTING_GUIDE.md`: add video test cases.
- `DEMO_EVIDENCE.md`: add video evidence fields.
- `.gitignore`: ignore generated video outputs.

## Recommended Next Phase

Phase 2 should refactor `test_pose.py` lightly by extracting the pure analysis part from `analyze_pose(...)` into a reusable helper. Do not implement video processing until that helper exists.
