import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


EXERCISES = ("squat", "pushup", "plank", "pullup")
EXERCISE_FOLDER_ALIASES = {
    "squat": ("squat",),
    "pushup": ("pushup", "push up", "push-up"),
    "plank": ("plank",),
    "pullup": ("pullup", "pull up", "pull-up"),
}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch-test workout videos and select the best result per exercise."
    )
    parser.add_argument(
        "--input-dir",
        default="samples/videos",
        help="Folder containing exercise subfolders such as squat, pushup, plank, and pullup.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/batch_video_results",
        help="Folder where batch results will be saved.",
    )
    parser.add_argument(
        "--frame-step",
        type=int,
        default=5,
        help="Analyze every Nth frame.",
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=30,
        help="Maximum seconds to analyze from each video.",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable to use when running analyze_cli.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running video analysis.",
    )
    return parser.parse_args()


def find_videos(input_dir, exercise):
    videos = []
    for folder_name in EXERCISE_FOLDER_ALIASES[exercise]:
        exercise_dir = input_dir / folder_name
        if not exercise_dir.exists():
            continue

        videos.extend(
            path
            for path in exercise_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )

    return sorted(set(videos))


def build_command(args, video_path, exercise, output_video, report_txt, report_json, keyframe):
    command = [
        args.python,
        "analyze_cli.py",
        "--input",
        str(video_path),
        "--exercise",
        exercise,
        "--media-type",
        "video",
        "--output",
        str(output_video),
        "--report",
        str(report_txt),
        "--json",
        str(report_json),
        "--representative-frame",
        str(keyframe),
        "--frame-step",
        str(args.frame_step),
    ]

    if args.max_seconds is not None:
        command.extend(["--max-seconds", str(args.max_seconds)])

    return command


def read_json_report(report_json):
    with report_json.open("r", encoding="utf-8") as file:
        return json.load(file)


def row_from_success(exercise, video_path, output_video, keyframe, report_txt, report_json, data, duration):
    return {
        "exercise": exercise,
        "input_video": str(video_path),
        "output_video": str(output_video),
        "keyframe": str(keyframe) if keyframe.exists() else "",
        "report_txt": str(report_txt),
        "report_json": str(report_json),
        "average_score": data.get("average_score", 0),
        "frames_with_pose": data.get("frames_with_pose", 0),
        "frames_without_pose": data.get("frames_without_pose", 0),
        "processed_frames": data.get("processed_frames", 0),
        "most_common_phase": data.get("most_common_phase", "UNKNOWN"),
        "common_feedback": data.get("common_feedback", []),
        "warnings": data.get("warnings", []),
        "selected_as_best": False,
        "status": "success",
        "error": "",
        "processing_duration_sec": round(duration, 2),
        "input_name": video_path.name,
    }


def row_from_failure(exercise, video_path, output_video, keyframe, report_txt, report_json, error, duration):
    return {
        "exercise": exercise,
        "input_video": str(video_path),
        "output_video": str(output_video),
        "keyframe": str(keyframe) if keyframe.exists() else "",
        "report_txt": str(report_txt),
        "report_json": str(report_json),
        "average_score": 0,
        "frames_with_pose": 0,
        "frames_without_pose": 0,
        "processed_frames": 0,
        "most_common_phase": "ERROR",
        "common_feedback": [],
        "warnings": [],
        "selected_as_best": False,
        "status": "failed",
        "error": error,
        "processing_duration_sec": round(duration, 2),
        "input_name": video_path.name,
    }


def best_sort_key(row):
    return (
        -float(row["average_score"]),
        -int(row["frames_with_pose"]),
        int(row["frames_without_pose"]),
        float(row["processing_duration_sec"]),
        row["input_name"].lower(),
    )


def copy_best_outputs(best_row, exercise_dir):
    copies = [
        ("output_video", exercise_dir / "best_output.mp4"),
        ("keyframe", exercise_dir / "best_keyframe.jpg"),
        ("report_txt", exercise_dir / "best_report.txt"),
        ("report_json", exercise_dir / "best_report.json"),
    ]

    for field, destination in copies:
        source = best_row.get(field)
        if source and Path(source).exists():
            shutil.copy2(source, destination)


def write_csv(rows, csv_path):
    fieldnames = [
        "exercise",
        "input_video",
        "output_video",
        "keyframe",
        "report_txt",
        "report_json",
        "average_score",
        "frames_with_pose",
        "frames_without_pose",
        "processed_frames",
        "most_common_phase",
        "selected_as_best",
        "warnings",
        "status",
        "error",
        "processing_duration_sec",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output_row = {key: row.get(key, "") for key in fieldnames}
            output_row["warnings"] = "; ".join(row.get("warnings", []))
            writer.writerow(output_row)


def write_json(rows, json_path):
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(rows, file, indent=2)


def write_best_markdown(best_rows, md_path):
    lines = [
        "# Best Batch Video Results",
        "",
        "These results are for selecting strong demo evidence videos, not for training a model.",
        "",
    ]

    if not best_rows:
        lines.append("No successful videos were selected.")
    else:
        for row in best_rows:
            lines.extend(
                [
                    f"## {row['exercise'].title()}",
                    "",
                    f"- Input video: `{row['input_video']}`",
                    f"- Best output: `{row['output_video']}`",
                    f"- Best keyframe: `{row['keyframe']}`",
                    f"- Text report: `{row['report_txt']}`",
                    f"- JSON report: `{row['report_json']}`",
                    f"- Average score: {row['average_score']}",
                    f"- Frames with pose: {row['frames_with_pose']}",
                    f"- Frames without pose: {row['frames_without_pose']}",
                    f"- Processed frames: {row['processed_frames']}",
                    f"- Most common phase: {row['most_common_phase']}",
                    "",
                ]
            )

            if row.get("common_feedback"):
                lines.append("Common feedback:")
                lines.extend(f"- {item}" for item in row["common_feedback"][:5])
                lines.append("")

            if row.get("warnings"):
                lines.append("Warnings:")
                lines.extend(f"- {item}" for item in row["warnings"])
                lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def print_command(command):
    print(" ".join(f'"{part}"' if " " in part else part for part in command))


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    cli_path = Path("analyze_cli.py")

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if not cli_path.exists():
        raise FileNotFoundError("analyze_cli.py was not found in the current project folder")
    if args.frame_step < 1:
        raise ValueError("--frame-step must be 1 or higher")

    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    best_rows = []

    for exercise in EXERCISES:
        videos = find_videos(input_dir, exercise)
        exercise_dir = output_dir / exercise
        all_results_dir = exercise_dir / "all_results"
        if not args.dry_run:
            all_results_dir.mkdir(parents=True, exist_ok=True)

        if not videos:
            print(f"[WARN] No videos found for {exercise} in {input_dir / exercise}")
            continue

        exercise_rows = []
        for video_path in videos:
            stem = video_path.stem
            output_video = all_results_dir / f"{stem}_output.mp4"
            keyframe = all_results_dir / f"{stem}_keyframe.jpg"
            report_txt = all_results_dir / f"{stem}_report.txt"
            report_json = all_results_dir / f"{stem}_report.json"
            command = build_command(
                args,
                video_path,
                exercise,
                output_video,
                report_txt,
                report_json,
                keyframe,
            )

            print(f"[INFO] Testing {exercise}: {video_path}")
            if args.dry_run:
                print_command(command)
                continue

            start = time.perf_counter()
            result = subprocess.run(command, text=True, capture_output=True)
            duration = time.perf_counter() - start

            if result.returncode != 0:
                error = (result.stderr or result.stdout or "Unknown error").strip()
                print(f"[ERROR] Failed: {video_path}")
                print(error)
                row = row_from_failure(
                    exercise,
                    video_path,
                    output_video,
                    keyframe,
                    report_txt,
                    report_json,
                    error,
                    duration,
                )
            else:
                try:
                    data = read_json_report(report_json)
                    row = row_from_success(
                        exercise,
                        video_path,
                        output_video,
                        keyframe,
                        report_txt,
                        report_json,
                        data,
                        duration,
                    )
                    print(f"[OK] Score {row['average_score']} | Pose frames {row['frames_with_pose']}")
                except Exception as exc:
                    row = row_from_failure(
                        exercise,
                        video_path,
                        output_video,
                        keyframe,
                        report_txt,
                        report_json,
                        f"Could not read generated JSON report: {exc}",
                        duration,
                    )
                    print(f"[ERROR] Could not read JSON report for {video_path}: {exc}")

            all_rows.append(row)
            exercise_rows.append(row)

        successful_rows = [row for row in exercise_rows if row["status"] == "success"]
        if successful_rows:
            best_row = sorted(successful_rows, key=best_sort_key)[0]
            best_row["selected_as_best"] = True
            copy_best_outputs(best_row, exercise_dir)

            best_row = dict(best_row)
            best_row["output_video"] = str(exercise_dir / "best_output.mp4")
            best_row["keyframe"] = str(exercise_dir / "best_keyframe.jpg")
            best_row["report_txt"] = str(exercise_dir / "best_report.txt")
            best_row["report_json"] = str(exercise_dir / "best_report.json")
            best_rows.append(best_row)
            print(f"[BEST] {exercise}: {best_row['input_name']}")

    if args.dry_run:
        print("[DRY RUN] No files were generated.")
        return

    write_csv(all_rows, output_dir / "batch_summary.csv")
    write_json(all_rows, output_dir / "batch_summary.json")
    write_best_markdown(best_rows, output_dir / "best_results.md")

    print()
    print("[DONE] Batch video testing complete.")
    print(f"Summary CSV: {output_dir / 'batch_summary.csv'}")
    print(f"Summary JSON: {output_dir / 'batch_summary.json'}")
    print(f"Best results: {output_dir / 'best_results.md'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1)
