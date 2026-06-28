import os
import json
import customtkinter as ctk
from tkinter import messagebox
from script_tool import CALL_1_PROMPT as DEFAULT_CALL_1
from script_tool import CALL_2_PROMPT as DEFAULT_CALL_2
from script_tool import STITCH_PROMPT as DEFAULT_STITCH

PROMPTS_FILE = "prompts.json"

class PromptEditorWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Edit AI Prompts")
        self.geometry("900x700")
        self.minsize(600, 500)
        
        if master:
            self.transient(master)
        self.grab_set()
        self.focus_force()
        
        self.prompts = self._load_prompts()
        
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tab_call1 = self.tabview.add("Call 1 (Story Intel)")
        self.tab_call2 = self.tabview.add("Call 2 (Script Writer)")
        self.tab_stitch = self.tabview.add("Stitch (Sequential)")
        
        self.textbox_call1 = ctk.CTkTextbox(self.tab_call1, wrap="word", font=("Consolas", 12))
        self.textbox_call1.pack(fill="both", expand=True, padx=5, pady=5)
        self.textbox_call1.insert("0.0", self.prompts.get("CALL_1_PROMPT", DEFAULT_CALL_1))
        
        self.textbox_call2 = ctk.CTkTextbox(self.tab_call2, wrap="word", font=("Consolas", 12))
        self.textbox_call2.pack(fill="both", expand=True, padx=5, pady=5)
        self.textbox_call2.insert("0.0", self.prompts.get("CALL_2_PROMPT", DEFAULT_CALL_2))
        
        self.textbox_stitch = ctk.CTkTextbox(self.tab_stitch, wrap="word", font=("Consolas", 12))
        self.textbox_stitch.pack(fill="both", expand=True, padx=5, pady=5)
        self.textbox_stitch.insert("0.0", self.prompts.get("STITCH_PROMPT", DEFAULT_STITCH))
        
        self.btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=5, pady=5)
        
        self.btn_reset = ctk.CTkButton(self.btn_frame, text="Reset to Defaults", fg_color="red", hover_color="darkred", command=self._reset_defaults)
        self.btn_reset.pack(side="left", padx=5)
        
        self.btn_save = ctk.CTkButton(self.btn_frame, text="Save Prompts", fg_color="green", hover_color="darkgreen", command=self._save_prompts)
        self.btn_save.pack(side="right", padx=5)
        
    def _load_prompts(self):
        if os.path.exists(PROMPTS_FILE):
            try:
                with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load prompts.json: {e}")
        return {}
        
    def _reset_defaults(self):
        if messagebox.askyesno("Reset Prompts", "Are you sure you want to restore the original hardcoded prompts?"):
            self.textbox_call1.delete("0.0", "end")
            self.textbox_call1.insert("0.0", DEFAULT_CALL_1)
            
            self.textbox_call2.delete("0.0", "end")
            self.textbox_call2.insert("0.0", DEFAULT_CALL_2)
            
            self.textbox_stitch.delete("0.0", "end")
            self.textbox_stitch.insert("0.0", DEFAULT_STITCH)
            
    def _save_prompts(self):
        data = {
            "CALL_1_PROMPT": self.textbox_call1.get("0.0", "end").strip(),
            "CALL_2_PROMPT": self.textbox_call2.get("0.0", "end").strip(),
            "STITCH_PROMPT": self.textbox_stitch.get("0.0", "end").strip(),
        }
        try:
            with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            messagebox.showinfo("Success", "Prompts saved successfully! The AI will use these rules from now on.")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save prompts: {e}")
