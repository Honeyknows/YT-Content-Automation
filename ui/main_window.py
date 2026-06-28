import customtkinter as ctk
import webbrowser
from ui.processing_view import ProcessingView
from ui.review_view import ReviewView
from ui.script_dashboard import ScriptDashboard

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YT Content Automation")
        self.geometry("1100x750")

        # Row 0 = header bar, Row 1 = content
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Minimal branded header ────────────────────────────────────
        header = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        link_lbl = ctk.CTkLabel(
            header,
            text="@honeyknows",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#ff4444",
            cursor="hand2"
        )
        link_lbl.grid(row=0, column=0, sticky="w", padx=(10, 0), pady=4)
        link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/honeyknows"))
        link_lbl.bind("<Enter>",    lambda e: link_lbl.configure(text_color="#ff6666"))
        link_lbl.bind("<Leave>",    lambda e: link_lbl.configure(text_color="#ff4444"))
        # ─────────────────────────────────────────────────────────────

        self.current_view = None
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.show_processing_view()

    def show_processing_view(self):
        if self.current_view is not None:
            self.current_view.destroy()
        self.current_view = ProcessingView(self, self.show_review_view)
        self.current_view.grid(row=1, column=0, sticky="nsew")

    def show_review_view(self, project_session):
        if self.current_view is not None:
            self.current_view.destroy()
        self.current_view = ReviewView(self, project_session, self.show_processing_view)
        self.current_view.grid(row=1, column=0, sticky="nsew")

    def show_script_view(self):
        if self.current_view is not None:
            self.current_view.destroy()
        self.current_view = ScriptDashboard(self, on_back_callback=self.show_processing_view)
        self.current_view.grid(row=1, column=0, sticky="nsew")

    def on_closing(self):
        """Clean up background threads before exit."""
        try:
            if self.current_view is not None:
                if hasattr(self.current_view, '_cancel_event'):
                    self.current_view._cancel_event.set()
                if hasattr(self.current_view, '_cancel'):
                    self.current_view._cancel.set()
        except Exception:
            pass
        self.destroy()
