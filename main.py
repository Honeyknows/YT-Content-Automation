import os
import sys
import traceback
import tkinter.messagebox as msgbox
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

ffmpeg_dir = os.path.join(BASE_DIR, "bin", "ffmpeg")
if os.path.exists(ffmpeg_dir):
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

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
        pass

sys.excepthook = handle_exception

from ui.main_window import MainWindow

if __name__ == "__main__":
    try:
        app = MainWindow()
        app.mainloop()
    except Exception:
        handle_exception(*sys.exc_info())
