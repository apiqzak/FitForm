import asyncio
import contextlib
import logging
import os
import sys
import tempfile
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_pose import VALID_EXERCISES, analyze_image_file


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
LOGGER = logging.getLogger(__name__)
DEBUG_LOG_PATH = PROJECT_ROOT / "outputs" / "temp" / "fitform_debug.log"
TELEGRAM_DEBUG_LOG_PATH = PROJECT_ROOT / "outputs" / "temp" / "openclaw_telegram_debug.log"
DEBUG_MODE = os.getenv("FITFORM_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
DEBUG_TELEGRAM = os.getenv("FITFORM_DEBUG_TELEGRAM", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
INTERNAL_LOG_PATTERNS = [
    "PowerShell",
    "powershell",
    "WindowsPowerShell",
    "Get-ChildItem",
    "Command ",
    'Command "',
    "rg --files",
    "Using the 'fitform' skill",
    "Using the fitform skill",
    "I'm checking where OpenClaw placed",
    "I’m checking where OpenClaw placed",
    "Tool:",
    "Tool error",
    "tool_call",
    "tool_result",
    "function_call",
    "function_result",
    "Traceback",
    "C:\\Windows\\System32",
    ".openclaw",
    "import cv2",
    "import cv2, os, json",
    "python -c",
    "python - <<",
    '"status": "failed"',
    "Tidepooling",
    "workspace scanning",
    "workspace file search",
    "file search",
    "stdout",
    "stderr",
]
FINAL_OPENCLAW_EVENT_TYPES = {
    "assistant_message",
    "final",
    "final_answer",
    "message",
}
INTERNAL_OPENCLAW_EVENT_TYPES = {
    "tool_call",
    "tool_result",
    "command",
    "stdout",
    "stderr",
    "debug",
    "status",
    "reasoning",
    "observation",
    "system",
    "developer",
    "function_call",
    "function_result",
}


def is_internal_openclaw_trace(text: str) -> bool:
    if not text:
        return False
    return any(pattern.lower() in text.lower() for pattern in INTERNAL_LOG_PATTERNS)


def is_internal_log_message(text: str) -> bool:
    return is_internal_openclaw_trace(text)


def should_forward_openclaw_event(event) -> bool:
    """Allow only final assistant-style events when an OpenClaw bridge exposes event types."""
    if not isinstance(event, dict):
        return False

    event_type = str(event.get("type") or event.get("event") or event.get("role") or "").lower()
    text = str(event.get("text") or event.get("content") or event.get("message") or "")

    if event_type in INTERNAL_OPENCLAW_EVENT_TYPES:
        log_internal_message(f"Suppressed event type={event_type}\n{text}")
        return False
    if is_internal_openclaw_trace(text):
        log_internal_message(f"Suppressed trace event type={event_type}\n{text}")
        return False
    if event_type and event_type not in FINAL_OPENCLAW_EVENT_TYPES:
        log_internal_message(f"Suppressed non-final event type={event_type}\n{text}")
        return False
    return bool(text.strip())


def log_internal_message(text: str):
    TELEGRAM_DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TELEGRAM_DEBUG_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n--- Suppressed Telegram/OpenClaw-facing message ---\n")
        log_file.write(text)
        log_file.write("\n")


async def safe_reply_text(message, text, **kwargs):
    if is_internal_openclaw_trace(text) and not DEBUG_TELEGRAM:
        log_internal_message(text)
        return None
    return await message.reply_text(text, **kwargs)


async def safe_edit_text(message, text, **kwargs):
    if is_internal_openclaw_trace(text) and not DEBUG_TELEGRAM:
        log_internal_message(text)
        return None
    return await message.edit_text(text, **kwargs)


@contextlib.contextmanager
def capture_internal_output():
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write("\n--- Captured Telegram analysis output ---\n")
        with contextlib.redirect_stdout(log_file), contextlib.redirect_stderr(log_file):
            yield


def clean_feedback(feedback_item):
    for prefix in ("[GOOD] ", "[WARN] ", "[BAD] "):
        if feedback_item.startswith(prefix):
            return feedback_item[len(prefix):]
    return feedback_item


def build_followup_suggestions(context, exercise=None):
    if context == "analysis":
        exercise_text = "pull-up" if exercise == "pullup" else (exercise or "exercise")
        return [
            "What should I fix first?",
            "Why did I get this warning?",
            "Can you explain my score?",
            f"How can I improve my {exercise_text} form?",
            "Can I try another image or video?",
        ]
    if context == "unsupported":
        return [
            "Can you check my squat instead?",
            "Can you check my pushup instead?",
            "What exercises do you support?",
        ]
    if context == "missing_exercise":
        return [
            "Analyze squat",
            "Analyze pushup",
            "Analyze plank",
            "Analyze pullup",
        ]
    if context == "missing_file":
        return [
            "I can upload a workout image",
            "I can upload a short workout video",
            "What kind of image works best?",
        ]
    return [
        "Check my squat form",
        "Analyze my pushup video",
        "What camera angle should I use?",
        "What exercises are supported?",
    ]


def format_followup_suggestions(context, exercise=None):
    suggestions = build_followup_suggestions(context, exercise)
    return "💬 You can also ask me:\n" + "\n".join(f"• {item}" for item in suggestions)


def format_user_summary(report):
    feedback = "\n".join(f"• {clean_feedback(item)}" for item in report["feedback"][:3])
    return (
        "✅ Analysis complete!\n\n"
        f"🏋️ Exercise: {report['exercise'].title()}\n"
        "🖼️ Media type: Image\n"
        f"📍 Phase: {report['phase']}\n"
        f"⭐ Score: {report['score']}/{report['total']}\n\n"
        "📝 Main feedback:\n"
        f"{feedback}\n\n"
        "⚠️ Note: This is educational posture feedback, not medical advice.\n\n"
        f"{format_followup_suggestions('analysis', report['exercise'])}"
    )


def exercise_keyboard():
    buttons = [
        [InlineKeyboardButton(exercise.title(), callback_data=f"exercise:{exercise}")]
        for exercise in VALID_EXERCISES
    ]
    return InlineKeyboardMarkup(buttons)


def parse_exercise(text):
    if not text:
        return None

    tokens = text.lower().replace("/", " ").split()
    for token in tokens:
        if token in VALID_EXERCISES:
            return token
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply_text(
        update.message,
        "Send a workout photo with a caption like 'squat', 'pushup', 'plank', or 'pullup'.\n"
        "You can also choose the exercise first using /exercise.\n\n"
        f"{format_followup_suggestions('help')}",
        reply_markup=exercise_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply_text(
        update.message,
        "Commands:\n"
        "/exercise - choose exercise type\n"
        "/set squat - save exercise type\n\n"
        "Then send a clear full-body photo. Captions also work, for example: pullup\n\n"
        f"{format_followup_suggestions('help')}",
        reply_markup=exercise_keyboard(),
    )


async def exercise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_reply_text(update.message, "Choose the exercise to analyze:", reply_markup=exercise_keyboard())


async def set_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exercise = parse_exercise(" ".join(context.args))
    if exercise is None:
        await safe_reply_text(
            update.message,
            "Please choose one of: squat, pushup, plank, pullup\n\n"
            f"{format_followup_suggestions('missing_exercise')}",
            reply_markup=exercise_keyboard(),
        )
        return

    context.user_data["exercise"] = exercise
    await safe_reply_text(update.message, f"Exercise set to {exercise.upper()}. Now send a photo.")


async def exercise_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    exercise = query.data.split(":", 1)[1]
    context.user_data["exercise"] = exercise
    await query.edit_message_text(f"Exercise set to {exercise.upper()}. Now send a workout photo.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption_exercise = parse_exercise(update.message.caption)
    exercise = caption_exercise or context.user_data.get("exercise")

    if exercise is None:
        await safe_reply_text(
            update.message,
            "Which exercise is this? Choose one, or resend the photo with a caption like 'squat'.\n\n"
            f"{format_followup_suggestions('missing_exercise')}",
            reply_markup=exercise_keyboard(),
        )
        return

    status_message = await safe_reply_text(update.message, "Analyzing posture...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / "input.jpg"
        output_path = temp_path / "output.jpg"

        photo = update.message.photo[-1]
        telegram_file = await photo.get_file()
        await telegram_file.download_to_drive(str(input_path))

        try:
            def run_analysis():
                with capture_internal_output():
                    return analyze_image_file(
                        str(input_path),
                        exercise,
                        str(output_path),
                        False,
                    )

            report = await asyncio.to_thread(run_analysis)
        except Exception as exc:
            LOGGER.exception("Pose analysis failed")
            if "No pose detected" in str(exc):
                error_text = (
                    "Sorry, I could not detect a clear body pose in this photo. Please try again with:\n"
                    "- full body visible\n"
                    "- one person in frame\n"
                    "- good lighting\n"
                    "- less motion blur\n\n"
                    f"{format_followup_suggestions('missing_file')}"
                )
            else:
                error_text = (
                    "Sorry, I could not analyze this file. Please make sure:\n"
                    "- the file is a clear workout photo\n"
                    "- the full body is visible\n"
                    "- the exercise is squat, pushup, plank, or pullup\n\n"
                    f"{format_followup_suggestions('missing_file')}"
                )
            await safe_edit_text(
                status_message,
                error_text
            )
            return

        caption = (
            f"🏋️ {report['exercise'].upper()} | 📍 {report['phase']}\n"
            f"⭐ Score: {report['score']}/{report['total']} checks passed"
        )
        with output_path.open("rb") as image_file:
            await update.message.reply_photo(photo=image_file, caption=caption)

        await safe_reply_text(update.message, format_user_summary(report))
        await status_message.delete()


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exercise = parse_exercise(update.message.text)
    if exercise is None:
        if is_internal_openclaw_trace(update.message.text) and not DEBUG_TELEGRAM:
            log_internal_message(update.message.text)
            return
        await safe_reply_text(
            update.message,
            "Send a workout photo, or choose an exercise first.\n\n"
            f"{format_followup_suggestions('missing_file')}",
            reply_markup=exercise_keyboard(),
        )
        return

    context.user_data["exercise"] = exercise
    await safe_reply_text(update.message, f"Exercise set to {exercise.upper()}. Now send a photo.")


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running the bot")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("exercise", exercise_command))
    app.add_handler(CommandHandler("set", set_exercise))
    app.add_handler(CallbackQueryHandler(exercise_button, pattern=r"^exercise:"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    LOGGER.info("Workout posture bot is running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
