import os
import sys
import traceback
import tkinter.messagebox as msgbox
import logging

# ── Base directory ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── Local ffmpeg in PATH so pydub finds it ────────────────────────
ffmpeg_dir = os.path.join(BASE_DIR, "bin", "ffmpeg")
if os.path.exists(ffmpeg_dir):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

# ── Crash logger ──────────────────────────────────────────────────
log_path = os.path.join(BASE_DIR, "crash_log.txt")
logging.basicConfig(
    filename=log_path,
    level=logging.ERROR,
    format="%(asctime)s  %(levelname)s\n%(message)s\n" + "-" * 60
)

def handle_exception(exc_type, exc_value, exc_tb):
    """Global uncaught-exception handler – logs + shows a popup."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    error_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.error(error_text)
    try:
        msgbox.showerror(
            "Something went wrong",
            f"An unexpected error occurred.\n\nDetails saved to:\n{log_path}\n\n{exc_value}"
        )
    except Exception:
        pass  # If even the popup fails, silently ignore

sys.excepthook = handle_exception

# ── Launch app ────────────────────────────────────────────────────
from ui.main_window import MainWindow

if __name__ == "__main__":
    try:
        app = MainWindow()
        app.mainloop()
    except Exception:
        handle_exception(*sys.exc_info())
