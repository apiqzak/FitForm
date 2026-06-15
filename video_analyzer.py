import json
from collections import Counter
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from test_pose import (
    VALID_EXERCISES,
    analyze_landmarks_for_exercise,
    build_status_map,
    create_landmarker,
    draw_angles_for_exercise,
    draw_feedback_panel,
    draw_skeleton,
    explain_score,
)


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def _create_video_writer(output_path, fps, frame_size):
    output_ext = Path(output_path).suffix.lower()
    codec = "mp4v" if output_ext in {"", ".mp4", ".mov", ".mkv"} else "XVID"
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    if not writer.isOpened() and codec != "XVID":
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)

    if not writer.isOpened():
        raise RuntimeError(f"Could not create output video writer for {output_path}")

    return writer


def _overlay_no_pose(frame):
    cv2.rectangle(frame, (12, 12), (260, 54), (25, 25, 25), -1)
    cv2.putText(
        frame,
        "No pose detected",
        (22, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 180, 255),
        2,
    )
    return frame


def _annotate_frame(frame, landmarks, analysis):
    h, w = frame.shape[:2]
    exercise = analysis["exercise"]
    statuses = analysis["statuses"]
    angles = analysis["angles"]
    feedback = analysis["feedback"]
    phase = analysis["phase"]
    phase_desc = analysis["phase_desc"]

    status_map = build_status_map(exercise, angles, statuses[1:])
    draw_skeleton(frame, landmarks, w, h, status_map)
    draw_angles_for_exercise(frame, landmarks, exercise, w, h)
    return draw_feedback_panel(
        frame,
        exercise,
        feedback,
        angles,
        statuses,
        h,
        w,
        phase=phase,
        phase_desc=phase_desc,
    )


def _compact_frame_report(frame_index, timestamp_sec, analysis):
    return {
        "frame_index": frame_index,
        "timestamp_sec": round(timestamp_sec, 2),
        "phase": analysis["phase"],
        "score": analysis["score"],
        "total": analysis["total"],
        "angles": analysis["angles"],
        "feedback": analysis["feedback"],
    }


def _format_video_report(summary):
    lines = [
        "Workout Video Posture Analysis",
        f"Exercise: {summary['exercise'].upper()}",
        f"Input: {summary['input_path']}",
        f"Output video: {summary['output_video_path']}",
        f"Frames processed: {summary['processed_frames']}",
        f"Frames with pose: {summary['frames_with_pose']}",
        f"Frames without pose: {summary['frames_without_pose']}",
        f"Average score: {summary['average_score']}/{summary['total_checks']} checks passed",
        f"Score Explanation: {summary['score_explanation']}",
        f"Most common phase: {summary['most_common_phase']}",
        "",
        "Common Feedback:",
    ]

    if summary["common_feedback"]:
        lines.extend(f"- {item}" for item in summary["common_feedback"])
    else:
        lines.append("- No repeated feedback available")

    if summary["warnings"]:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item}" for item in summary["warnings"])

    return "\n".join(lines)


def analyze_video_file(
    input_path,
    exercise,
    output_path,
    report_path=None,
    json_path=None,
    representative_frame_path=None,
    frame_step=5,
    max_seconds=None,
):
    input_path = str(input_path)
    output_path = str(output_path)
    exercise = exercise.strip().lower()

    if exercise not in VALID_EXERCISES:
        raise ValueError(f"Invalid exercise '{exercise}'. Choose: {', '.join(VALID_EXERCISES)}")

    input_ext = Path(input_path).suffix.lower()
    if input_ext not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported video format '{input_ext}'. Supported: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
        )

    if frame_step < 1:
        raise ValueError("frame_step must be 1 or higher")

    if max_seconds is not None and max_seconds <= 0:
        raise ValueError("max_seconds must be greater than 0")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration_sec = round(total_frames / fps, 2) if fps and total_frames else None
    max_frame_index = int(max_seconds * fps) if max_seconds else None

    if width <= 0 or height <= 0:
        cap.release()
        raise ValueError("Could not read video dimensions")

    writer = None
    processed_frames = 0
    frames_with_pose = 0
    frames_without_pose = 0
    frame_reports = []
    phase_counts = Counter()
    feedback_counts = Counter()
    warnings = []
    best_frame = None
    best_score = None
    first_processed_frame = None
    output_size = None

    try:
        with create_landmarker() as landmarker:
            frame_index = -1

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_index += 1

                if max_frame_index is not None and frame_index > max_frame_index:
                    break

                if frame_index % frame_step != 0:
                    continue

                processed_frames += 1
                timestamp_sec = frame_index / fps if fps else 0
                annotated_frame = frame.copy()

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb_frame))
                results = landmarker.detect(mp_image)

                if results.pose_landmarks:
                    frames_with_pose += 1
                    landmarks = results.pose_landmarks[0]
                    analysis = analyze_landmarks_for_exercise(landmarks, width, height, exercise)
                    annotated_frame = _annotate_frame(annotated_frame, landmarks, analysis)

                    phase_counts[analysis["phase"]] += 1
                    feedback_counts.update(analysis["feedback"])
                    frame_reports.append(_compact_frame_report(frame_index, timestamp_sec, analysis))

                    if best_score is None or analysis["score"] > best_score:
                        best_score = analysis["score"]
                        best_frame = annotated_frame.copy()
                else:
                    frames_without_pose += 1
                    annotated_frame = _overlay_no_pose(annotated_frame)

                if first_processed_frame is None:
                    first_processed_frame = annotated_frame.copy()

                if writer is None:
                    output_size = (annotated_frame.shape[1], annotated_frame.shape[0])
                    writer = _create_video_writer(output_path, fps / frame_step, output_size)

                if (annotated_frame.shape[1], annotated_frame.shape[0]) != output_size:
                    annotated_frame = cv2.resize(annotated_frame, output_size)

                writer.write(annotated_frame)
    finally:
        cap.release()
        if writer is not None:
            writer.release()

    if processed_frames == 0:
        warnings.append("No frames were processed. Check frame_step and max_seconds.")

    if frames_without_pose:
        warnings.append(f"{frames_without_pose} processed frame(s) had no detectable pose.")

    if processed_frames > 0 and frames_with_pose == 0:
        warnings.append(
            "No clear body pose was detected in the sampled frames. Try a clearer full-body video with one person visible."
        )

    if max_seconds is not None:
        warnings.append(f"Video analysis was limited to the first {max_seconds} second(s).")

    if frame_step > 1:
        warnings.append(f"Video was sampled every {frame_step} frame(s).")

    if writer is None:
        raise ValueError("No output video was written because no frames were processed")

    representative_frame_saved = None
    representative_frame = best_frame if best_frame is not None else first_processed_frame
    if representative_frame_path and representative_frame is not None:
        if cv2.imwrite(str(representative_frame_path), representative_frame):
            representative_frame_saved = str(representative_frame_path)
        else:
            warnings.append(f"Could not save representative frame to {representative_frame_path}.")
    elif representative_frame_path:
        warnings.append("No representative frame was available to save.")

    score_total = sum(report["score"] for report in frame_reports)
    total_checks = frame_reports[0]["total"] if frame_reports else 0
    average_score = round(score_total / len(frame_reports), 2) if frame_reports else 0
    most_common_phase = phase_counts.most_common(1)[0][0] if phase_counts else "UNKNOWN"
    common_feedback = [item for item, _ in feedback_counts.most_common(8)]

    summary = {
        "media_type": "video",
        "input_path": input_path,
        "exercise": exercise,
        "output_video_path": output_path,
        "representative_frame_path": representative_frame_saved,
        "report_path": str(report_path) if report_path else None,
        "json_path": str(json_path) if json_path else None,
        "fps": round(float(fps), 2),
        "total_frames": total_frames,
        "width": width,
        "height": height,
        "duration_sec": duration_sec,
        "processed_frames": processed_frames,
        "frames_with_pose": frames_with_pose,
        "frames_without_pose": frames_without_pose,
        "frame_step": frame_step,
        "max_seconds": max_seconds,
        "average_score": average_score,
        "total_checks": total_checks,
        "score_explanation": (
            explain_score(average_score, total_checks)
            + " For video, this is the average score across sampled frames where a pose was detected."
        ),
        "most_common_phase": most_common_phase,
        "phase_counts": dict(phase_counts),
        "common_feedback": common_feedback,
        "warnings": warnings,
        "frame_reports": frame_reports,
    }

    if report_path:
        Path(report_path).write_text(_format_video_report(summary), encoding="utf-8")

    if json_path:
        Path(json_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary
