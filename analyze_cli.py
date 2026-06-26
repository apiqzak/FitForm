import argparse
import contextlib
import json
import logging
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("ABSL_MIN_LOG_LEVEL", "2")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from test_pose import VALID_EXERCISES, analyze_image_file, format_report


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
DEBUG_LOG_PATH = Path("outputs") / "temp" / "fitform_debug.log"
DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


logging.basicConfig(
    filename=DEBUG_LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def is_image_file(input_path):
    return Path(input_path).suffix.lower() in IMAGE_EXTENSIONS


def is_video_file(input_path):
    return Path(input_path).suffix.lower() in VIDEO_EXTENSIONS


def infer_media_type(input_path):
    suffix = Path(input_path).suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"

    supported = ", ".join(sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS))
    raise ValueError(f"Unsupported file type '{suffix}'. Supported extensions: {supported}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Command-line bridge for Workout Posture Analysis."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the workout image or video.",
    )
    parser.add_argument(
        "--exercise",
        required=True,
        help="Exercise type to analyze: squat, pushup, plank, or pullup.",
    )
    parser.add_argument(
        "--media-type",
        choices=["image", "video", "auto"],
        default="auto",
        help="Input media type. Use auto to infer from file extension.",
    )
    parser.add_argument(
        "--output",
        default="output.jpg",
        help="Path where the annotated image or video will be saved.",
    )
    parser.add_argument(
        "--report",
        default="report.txt",
        help="Path where the text report will be saved.",
    )
    parser.add_argument(
        "--json",
        default="report.json",
        help="Path where the structured JSON report will be saved.",
    )
    parser.add_argument(
        "--representative-frame",
        default=None,
        help="Optional path for a representative annotated frame when analyzing video.",
    )
    parser.add_argument(
        "--frame-step",
        type=int,
        default=5,
        help="Analyze every Nth frame for video inputs.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=None,
        help="Optional maximum video duration to analyze in seconds.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Hide detailed internal output and print only a short summary.",
    )
    return parser.parse_args()


def normalize_exercise(exercise):
    normalized = exercise.strip().lower().replace("-", "").replace(" ", "")
    if normalized == "pushups":
        return "pushup"
    if normalized == "pullups":
        return "pullup"
    return normalized


def validate_exercise(exercise):
    normalized = normalize_exercise(exercise)
    if normalized not in VALID_EXERCISES:
        raise ValueError(f"Unsupported exercise: {exercise}")
    return normalized


def ensure_parent_dir(path):
    if path:
        parent = Path(path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)


def ensure_output_paths(args):
    ensure_parent_dir(args.output)
    ensure_parent_dir(args.report)
    ensure_parent_dir(args.json)
    ensure_parent_dir(args.representative_frame)


@contextlib.contextmanager
def capture_internal_output(enabled):
    if not enabled:
        yield
        return

    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n--- Captured FitForm CLI output ---\n")
        log_file.flush()

        saved_stdout_fd = os.dup(1)
        saved_stderr_fd = os.dup(2)
        try:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(log_file.fileno(), 1)
            os.dup2(log_file.fileno(), 2)
            with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
                yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_stdout_fd, 1)
            os.dup2(saved_stderr_fd, 2)
            os.close(saved_stdout_fd)
            os.close(saved_stderr_fd)


def clean_feedback(feedback_item):
    for prefix in ("[GOOD] ", "[WARN] ", "[BAD] "):
        if feedback_item.startswith(prefix):
            return feedback_item[len(prefix):]
    return feedback_item


def display_exercise_name(exercise):
    if not exercise:
        return "exercise"
    if exercise == "pullup":
        return "pull-up"
    return exercise


def print_followup_suggestions(exercise=None, context="analysis"):
    if context == "missing_exercise":
        suggestions = [
            "Analyze squat",
            "Analyze pushup",
            "Analyze plank",
            "Analyze pullup",
        ]
        heading = "You can reply with:"
    elif context == "missing_file":
        suggestions = [
            "What kind of image works best?",
            "What camera angle should I use?",
            "What exercises are supported?",
        ]
        heading = "You can also ask:"
    elif context == "unsupported":
        suggestions = [
            "Can you check my squat instead?",
            "Can you check my pushup instead?",
            "What exercises do you support?",
        ]
        heading = "You can ask:"
    else:
        exercise_name = display_exercise_name(exercise)
        suggestions = [
            "What should I fix first?",
            "Why did I get this warning?",
            "Can you explain my score?",
            f"How can I improve my {exercise_name} form?",
            "Can I try another image or video?",
        ]
        heading = "You can also ask me:"

    print()
    print(f"💬 {heading}")
    for suggestion in suggestions:
        print(f"• {suggestion}")


def print_quiet_image_summary(report, args):
    print("✅ Analysis complete!")
    print()
    print(f"🏋️ Exercise: {report['exercise'].title()}")
    print("🖼️ Media type: Image")
    print(f"📍 Phase: {report['phase']}")
    print(f"⭐ Score: {report['score']}/{report['total']}")
    print("📝 Main feedback:")
    for item in report["feedback"][:3]:
        print(f"• {clean_feedback(item)}")
    print_followup_suggestions(report.get("exercise"), "analysis")


def print_quiet_video_summary(report, args):
    print("✅ Analysis complete!")
    print()
    print(f"🏋️ Exercise: {report['exercise'].title()}")
    print("🎥 Media type: Video")
    print(f"⭐ Score: {report['average_score']}/{report['total_checks']}")
    print(f"✅ Frames with pose: {report['frames_with_pose']}")
    if report.get("frames_without_pose"):
        print(f"⚠️ Frames without pose: {report['frames_without_pose']}")
    print(f"📍 Most common phase: {report['most_common_phase']}")
    print("📝 Main feedback:")
    feedback_items = report.get("common_feedback", [])[:3]
    if not feedback_items and report.get("warnings"):
        feedback_items = report.get("warnings", [])[:3]
    if not feedback_items:
        feedback_items = ["No repeated feedback was available from the sampled frames."]
    for item in feedback_items:
        print(f"• {clean_feedback(item)}")
    print_followup_suggestions(report.get("exercise"), "analysis")


def analyze_image(args):
    with capture_internal_output(args.quiet):
        report = analyze_image_file(
            args.input,
            args.exercise,
            output_path=args.output,
            show_window=False,
        )

    text_report = format_report(report)
    Path(args.report).write_text(text_report, encoding="utf-8")
    Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.quiet:
        print_quiet_image_summary(report, args)
        return report

    print(text_report)
    print()
    print(f"Annotated image: {args.output}")
    print(f"Text report: {args.report}")
    print(f"JSON report: {args.json}")
    return report


def analyze_video(args):
    try:
        from video_analyzer import analyze_video_file
    except ImportError as exc:
        raise RuntimeError(f"Video analyzer could not be imported: {exc}") from exc

    with capture_internal_output(args.quiet):
        report = analyze_video_file(
            args.input,
            args.exercise,
            args.output,
            report_path=args.report,
            json_path=args.json,
            representative_frame_path=args.representative_frame,
            frame_step=args.frame_step,
            max_seconds=args.max_seconds,
        )

    if args.quiet:
        print_quiet_video_summary(report, args)
        return report

    print("Workout Video Posture Analysis")
    print(f"Exercise: {report['exercise'].upper()}")
    print(f"Frames processed: {report['processed_frames']}")
    print(f"Frames with pose: {report['frames_with_pose']}")
    print(f"Frames without pose: {report['frames_without_pose']}")
    print(f"Average score: {report['average_score']}/{report['total_checks']} checks passed")
    print(f"Most common phase: {report['most_common_phase']}")
    print()
    print(f"Annotated video: {args.output}")
    if report.get("representative_frame_path"):
        print(f"Representative frame: {report['representative_frame_path']}")
    print(f"Text report: {args.report}")
    print(f"JSON report: {args.json}")
    return report


def main():
    args = parse_args()

    args.exercise = validate_exercise(args.exercise)
    ensure_output_paths(args)

    input_path = Path(args.input)
    media_type = infer_media_type(input_path) if args.media_type == "auto" else args.media_type

    if media_type == "image" and not is_image_file(input_path):
        raise ValueError(f"Media type is image, but input does not look like an image: {args.input}")
    if media_type == "video" and not is_video_file(input_path):
        raise ValueError(f"Media type is video, but input does not look like a supported video: {args.input}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    if media_type == "image":
        analyze_image(args)
    elif media_type == "video":
        analyze_video(args)
    else:
        raise ValueError(f"Unsupported media type: {media_type}")


def print_missing_file_error():
    print("Please upload a workout image or short video first.")
    print()
    print("Make sure the file path is correct and the file is inside the project or OpenClaw workspace.")
    print_followup_suggestions(context="missing_file")


def print_unsupported_file_error():
    print("Sorry, I could not analyze this file type.")
    print("Please use a supported workout image or video file.")
    print()
    print("Supported images: .jpg, .jpeg, .png")
    print("Supported videos: .mp4, .mov, .avi, .mkv")
    print_followup_suggestions(context="missing_file")


def print_unsupported_exercise_error():
    print("Currently I support squat, pushup, plank, and pullup.")
    print("Please choose one of these exercises for analysis.")
    print_followup_suggestions(context="unsupported")


def print_no_pose_error():
    print("Sorry, I could not detect a clear body pose in this file.")
    print("Please try again with:")
    print("- full body visible")
    print("- one person in frame")
    print("- good lighting")
    print("- less motion blur")
    print_followup_suggestions(context="missing_file")


def print_media_mismatch_error():
    print("Sorry, the selected media type does not match the uploaded file.")
    print("Please use --media-type auto, or upload a supported image or video.")
    print_followup_suggestions(context="missing_file")


def print_video_settings_error():
    print("Sorry, the video analysis settings are invalid.")
    print("Please make sure:")
    print("- --frame-step is 1 or higher")
    print("- --max-seconds is greater than 0 if you use it")
    print()
    print("For demos, a safe setting is --frame-step 5 --max-seconds 30.")
    print_followup_suggestions(context="missing_file")


def print_generic_analysis_error():
    print("Sorry, I could not analyze this file clearly. Please make sure:")
    print("- the file is a supported image or video")
    print("- the full body is visible")
    print("- there is one person in frame")
    print("- the exercise is squat, pushup, plank, or pullup")
    print_followup_suggestions(context="missing_file")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.error("FitForm CLI failed:\n%s", traceback.format_exc())
        message = str(exc)
        if isinstance(exc, FileNotFoundError):
            print_missing_file_error()
        elif isinstance(exc, ValueError) and (
            "Unsupported file type" in message
            or "Unsupported video format" in message
        ):
            print_unsupported_file_error()
        elif isinstance(exc, ValueError) and (
            "Unsupported exercise" in message
            or "Invalid exercise" in message
        ):
            print_unsupported_exercise_error()
        elif isinstance(exc, ValueError) and (
            "Media type is image" in message
            or "Media type is video" in message
        ):
            print_media_mismatch_error()
        elif isinstance(exc, ValueError) and (
            "frame_step" in message
            or "max_seconds" in message
        ):
            print_video_settings_error()
        elif isinstance(exc, ValueError) and "No pose detected" in message:
            print_no_pose_error()
        else:
            print_generic_analysis_error()
        raise SystemExit(1)
