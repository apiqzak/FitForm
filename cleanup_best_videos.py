import argparse
import csv
import json
import re
import shutil
from pathlib import Path


EXERCISES = ("squat", "pushup", "plank", "pullup")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
EXERCISE_FOLDER_ALIASES = {
    "squat": ("squat",),
    "pushup": ("pushup", "push up", "push-up"),
    "plank": ("plank",),
    "pullup": ("pullup", "pull up", "pull-up"),
}
RESULT_EXTENSIONS = {".mp4", ".jpg", ".jpeg", ".png", ".txt", ".json"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Safely delete non-best workout videos and generated batch results."
    )
    parser.add_argument(
        "--input-dir",
        default="samples/videos",
        help="Folder containing exercise video subfolders.",
    )
    parser.add_argument(
        "--results-dir",
        default="outputs/batch_video_results",
        help="Folder containing batch video result summaries and outputs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without deleting anything.",
    )
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="Actually delete non-best files. Required for deletion.",
    )
    parser.add_argument(
        "--move-best-to-final-demo",
        action="store_true",
        help="Copy kept best files into outputs/final_demo/<exercise>/ for presentation use.",
    )
    parser.add_argument(
        "--final-demo-dir",
        default="outputs/final_demo",
        help="Destination folder used with --move-best-to-final-demo.",
    )
    return parser.parse_args()


def is_relative_to(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_from_project(path_value):
    return Path(path_value).expanduser().resolve()


def load_summary(results_dir):
    json_path = results_dir / "batch_summary.json"
    csv_path = results_dir / "batch_summary.csv"
    md_path = results_dir / "best_results.md"

    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as file:
            rows = json.load(file)
        if not isinstance(rows, list):
            raise ValueError("batch_summary.json must contain a list of result rows")
        return rows, json_path

    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        return rows, csv_path

    if md_path.exists():
        return load_best_results_markdown(md_path), md_path

    raise FileNotFoundError(
        f"No batch summary found. Expected {json_path}, {csv_path}, or {md_path}."
    )


def load_best_results_markdown(md_path):
    rows = []
    current = None
    field_map = {
        "Input video": "input_video",
        "Best output": "output_video",
        "Best keyframe": "keyframe",
        "Text report": "report_txt",
        "JSON report": "report_json",
    }

    for line in md_path.read_text(encoding="utf-8").splitlines():
        header = re.match(r"^##\s+(.+)$", line.strip())
        if header:
            exercise = header.group(1).strip().lower()
            if exercise in EXERCISES:
                current = {
                    "exercise": exercise,
                    "selected_as_best": True,
                    "status": "success",
                }
                rows.append(current)
            else:
                current = None
            continue

        if current is None:
            continue

        item = re.match(r"^-\s+([^:]+):\s+`(.+)`$", line.strip())
        if item:
            label, value = item.group(1).strip(), item.group(2).strip()
            if label in field_map:
                current[field_map[label]] = value

    return rows


def selected_flag(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def find_selected_rows(rows):
    selected = {}
    for exercise in EXERCISES:
        matches = [
            row
            for row in rows
            if str(row.get("exercise", "")).lower() == exercise
            and selected_flag(row.get("selected_as_best", False))
            and str(row.get("status", "success")).lower() == "success"
        ]

        if len(matches) != 1:
            selected[exercise] = None
        else:
            selected[exercise] = matches[0]

    return selected


def exercise_video_dirs(input_dir, exercise):
    return [
        input_dir / folder_name
        for folder_name in EXERCISE_FOLDER_ALIASES[exercise]
        if (input_dir / folder_name).exists()
    ]


def collect_original_videos(input_dir, exercise):
    videos = []
    for folder in exercise_video_dirs(input_dir, exercise):
        videos.extend(
            path
            for path in folder.rglob("*")
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )
    return sorted(set(videos))


def collect_generated_result_files(results_dir, exercise):
    exercise_dir = results_dir / exercise
    if not exercise_dir.exists():
        return []

    return sorted(
        path
        for path in exercise_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in RESULT_EXTENSIONS
    )


def required_keep_paths(row, results_dir):
    exercise = str(row["exercise"]).lower()
    paths = {
        "kept_input_video": Path(row["input_video"]),
        "kept_output_video": results_dir / exercise / "best_output.mp4",
        "kept_keyframe": results_dir / exercise / "best_keyframe.jpg",
        "kept_report_txt": results_dir / exercise / "best_report.txt",
        "kept_report_json": results_dir / exercise / "best_report.json",
        "source_output_video": Path(row["output_video"]),
        "source_keyframe": Path(row["keyframe"]),
        "source_report_txt": Path(row["report_txt"]),
        "source_report_json": Path(row["report_json"]),
    }
    return {name: resolve_from_project(path) for name, path in paths.items() if str(path)}


def validate_keep_paths(keep_paths, input_root, results_root):
    warnings = []
    for name, path in keep_paths.items():
        if name.startswith("kept_input"):
            allowed = is_relative_to(path, input_root)
        else:
            allowed = is_relative_to(path, results_root)

        if not allowed:
            warnings.append(f"{name} is outside the allowed folders: {path}")
        elif not path.exists():
            warnings.append(f"{name} is missing: {path}")

    return warnings


def safe_delete(path, allowed_roots, dry_run):
    resolved = path.resolve()
    if not any(is_relative_to(resolved, root) for root in allowed_roots):
        return False, f"Skipped outside allowed folders: {resolved}"

    if not resolved.exists():
        return False, f"Skipped missing file: {resolved}"

    if dry_run:
        return True, f"[DRY RUN] Would delete: {resolved}"

    resolved.unlink()
    return True, f"Deleted: {resolved}"


def copy_final_demo_files(exercise, keep_paths, final_demo_dir):
    destination = final_demo_dir / exercise
    destination.mkdir(parents=True, exist_ok=True)

    copy_map = {
        "kept_input_video": destination / f"{exercise}_input{keep_paths['kept_input_video'].suffix}",
        "kept_output_video": destination / f"{exercise}_annotated.mp4",
        "kept_keyframe": destination / f"{exercise}_keyframe.jpg",
        "kept_report_txt": destination / f"{exercise}_report.txt",
        "kept_report_json": destination / f"{exercise}_report.json",
    }

    copied = []
    for source_key, destination_path in copy_map.items():
        source = keep_paths[source_key]
        if source.exists():
            shutil.copy2(source, destination_path)
            copied.append(destination_path)
    return copied


def write_cleanup_summary(records, summary_path):
    lines = [
        "# Cleanup Summary",
        "",
        "This cleanup keeps only the selected best demo evidence for each exercise.",
        "",
    ]

    for record in records:
        lines.extend(
            [
                f"## {record['exercise'].title()}",
                "",
                f"- Status: {record['status']}",
                f"- Kept input video: `{record.get('kept_input_video', '')}`",
                f"- Kept output video: `{record.get('kept_output_video', '')}`",
                f"- Kept keyframe: `{record.get('kept_keyframe', '')}`",
                f"- Kept text report: `{record.get('kept_report_txt', '')}`",
                f"- Kept JSON report: `{record.get('kept_report_json', '')}`",
                f"- Deleted files count: {record['deleted_files_count']}",
                f"- Skipped files count: {record['skipped_files_count']}",
                "",
            ]
        )

        if record["warnings"]:
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in record["warnings"])
            lines.append("")

        if record.get("final_demo_files"):
            lines.append("Final demo copies:")
            lines.extend(f"- `{path}`" for path in record["final_demo_files"])
            lines.append("")

    summary_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    args = parse_args()
    if args.confirm_delete and args.dry_run:
        raise ValueError("Use either --dry-run or --confirm-delete, not both.")
    if not args.confirm_delete and not args.dry_run:
        raise ValueError("Choose --dry-run to preview or --confirm-delete to delete files.")

    input_dir = Path(args.input_dir).resolve()
    results_dir = Path(args.results_dir).resolve()
    final_demo_dir = Path(args.final_demo_dir).resolve()

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if not results_dir.exists():
        raise FileNotFoundError(f"Results directory not found: {results_dir}")

    rows, source_summary = load_summary(results_dir)
    selected_rows = find_selected_rows(rows)
    cleanup_records = []
    allowed_roots = [input_dir, results_dir]

    print(f"[INFO] Loaded summary: {source_summary}")

    for exercise in EXERCISES:
        row = selected_rows[exercise]
        warnings = []
        deleted_count = 0
        skipped_count = 0
        final_demo_files = []

        if row is None:
            warnings.append(
                "Best selection is missing or unclear. Skipping deletion for this exercise."
            )
            cleanup_records.append(
                {
                    "exercise": exercise,
                    "status": "skipped",
                    "deleted_files_count": 0,
                    "skipped_files_count": 0,
                    "warnings": warnings,
                    "final_demo_files": [],
                }
            )
            print(f"[SKIP] {exercise}: unclear best selection")
            continue

        keep_paths = required_keep_paths(row, results_dir)
        validation_warnings = validate_keep_paths(keep_paths, input_dir, results_dir)
        warnings.extend(validation_warnings)

        if validation_warnings:
            cleanup_records.append(
                {
                    "exercise": exercise,
                    "status": "skipped",
                    "kept_input_video": str(keep_paths.get("kept_input_video", "")),
                    "kept_output_video": str(keep_paths.get("kept_output_video", "")),
                    "kept_keyframe": str(keep_paths.get("kept_keyframe", "")),
                    "kept_report_txt": str(keep_paths.get("kept_report_txt", "")),
                    "kept_report_json": str(keep_paths.get("kept_report_json", "")),
                    "deleted_files_count": 0,
                    "skipped_files_count": 0,
                    "warnings": warnings,
                    "final_demo_files": [],
                }
            )
            print(f"[SKIP] {exercise}: missing or unsafe keep file")
            continue

        keep_set = set(keep_paths.values())
        candidates = []
        candidates.extend(collect_original_videos(input_dir, exercise))
        candidates.extend(collect_generated_result_files(results_dir, exercise))
        candidates = sorted(set(path.resolve() for path in candidates))

        print(f"[INFO] Cleaning {exercise}: {len(candidates)} candidate file(s)")
        for candidate in candidates:
            if candidate in keep_set:
                continue

            deleted, message = safe_delete(candidate, allowed_roots, args.dry_run)
            print(message)
            if deleted:
                deleted_count += 1
            else:
                skipped_count += 1
                warnings.append(message)

        if args.move_best_to_final_demo and not args.dry_run:
            final_demo_files = [
                str(path)
                for path in copy_final_demo_files(exercise, keep_paths, final_demo_dir)
            ]
        elif args.move_best_to_final_demo and args.dry_run:
            final_demo_files = [
                str(final_demo_dir / exercise / f"{exercise}_input{keep_paths['kept_input_video'].suffix}"),
                str(final_demo_dir / exercise / f"{exercise}_annotated.mp4"),
                str(final_demo_dir / exercise / f"{exercise}_keyframe.jpg"),
                str(final_demo_dir / exercise / f"{exercise}_report.txt"),
                str(final_demo_dir / exercise / f"{exercise}_report.json"),
            ]

        cleanup_records.append(
            {
                "exercise": exercise,
                "status": "dry-run" if args.dry_run else "cleaned",
                "kept_input_video": str(keep_paths["kept_input_video"]),
                "kept_output_video": str(keep_paths["kept_output_video"]),
                "kept_keyframe": str(keep_paths["kept_keyframe"]),
                "kept_report_txt": str(keep_paths["kept_report_txt"]),
                "kept_report_json": str(keep_paths["kept_report_json"]),
                "deleted_files_count": deleted_count,
                "skipped_files_count": skipped_count,
                "warnings": warnings,
                "final_demo_files": final_demo_files,
            }
        )

    summary_path = results_dir / "cleanup_summary.md"
    write_cleanup_summary(cleanup_records, summary_path)

    print()
    print("[DONE] Cleanup preview complete." if args.dry_run else "[DONE] Cleanup complete.")
    print(f"Cleanup summary: {summary_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}")
        raise SystemExit(1)
