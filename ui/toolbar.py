import tkinter as tk
from tkinter import ttk
from ui.common import create_action_button

class Toolbar(tk.Frame):
    def __init__(self, app, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.build()

    def build(self):
        # --- ACTION & RECENT PATHS BAR ---
        self.frm_action = tk.Frame(self, bg="#1e1e2e", pady=5)
        self.frm_action.pack(fill=tk.X)

        # Top row of Hero Zone: Load Buttons
        self.frm_load = tk.Frame(self.frm_action, bg="#1e1e2e")
        self.frm_load.pack(fill=tk.X, pady=(0, 5))

        self.load_files_button = create_action_button(self.frm_load, "📄 Load Files...", self.app.load_files)
        self.load_files_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.load_folder_button = create_action_button(self.frm_load, "📁 Load Folder...", self.app.load_folder)
        self.load_folder_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # Bottom row of Hero Zone: Copy + Mode Dropdown
        self.frm_copy_row = tk.Frame(self.frm_action, bg="#1e1e2e")
        self.frm_copy_row.pack(fill=tk.X)

        self.var_copy_mode = tk.StringVar(value="Normal")
        self.copy_mode_dropdown = tk.OptionMenu(self.frm_copy_row, self.var_copy_mode, 
                                             "Normal", "Strip Comments", "Skeleton", "Mermaid Graph", "Git Diff")
        self.copy_mode_dropdown.config(font=("Segoe UI", 10, "bold"), bd=0, relief="flat", padx=15, pady=8, cursor="hand2", highlightthickness=0)
        self.copy_mode_dropdown.pack(side=tk.RIGHT, padx=(5, 0), fill=tk.Y)
        
        self.copy_button = create_action_button(self.frm_copy_row, "📋 Copy Filtered Selection", self.app.copy_filtered_selection)
        self.copy_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # --- QUICK PRESETS BAR ---
        self.frm_quick_presets = tk.Frame(self, bg="#1e1e2e", pady=2)
        self.frm_quick_presets.pack(fill=tk.X)
        
        self.lbl_quick_presets = tk.Label(self.frm_quick_presets, text="⚡ Quick Presets:", font=("Segoe UI", 9, "bold"), bg="#1e1e2e", fg="#cba6f7")
        self.lbl_quick_presets.pack(side=tk.LEFT, padx=(0, 10))

        preset_names = [
            ("Python", "Python Project"),
            ("React", "NodeJS / React"),
            ("Android", "Android Project"),
            ("Markdown", "Markdown Docs"),
            ("Custom", "Custom")
        ]
        
        self.quick_presets_buttons = []
        for label, p_name in preset_names:
            btn = tk.Button(self.frm_quick_presets, text=label, command=lambda n=p_name: self.app.apply_preset_by_name(n),
                            bd=0, relief="flat", padx=10, pady=2, font=("Segoe UI", 8, "bold"), cursor="hand2")
            btn.pack(side=tk.LEFT, padx=3)
            btn._preset_name = p_name
            self.quick_presets_buttons.append(btn)

    def update_active_preset(self, active_name):
        from config import THEMES
        t = THEMES[self.app.state.current_theme]
        
        for btn in self.quick_presets_buttons:
            if btn._preset_name == active_name:
                # Active style: Accent background
                btn.configure(
                    bg=t["accent"], 
                    fg="#11111b" if self.app.state.current_theme == "dark" else t["bg"],
                    activebackground=t["accent_hover"],
                    activeforeground="#11111b" if self.app.state.current_theme == "dark" else t["bg"]
                )
                
                # Rebind hover to stay on accent
                btn.bind("<Enter>", lambda e, b=btn, h=t["accent_hover"]: b.config(bg=h))
                btn.bind("<Leave>", lambda e, b=btn, c=t["accent"]: b.config(bg=c))
            else:
                # Inactive style: Standard card background
                btn.configure(
                    bg=t["card_bg"],
                    fg=t["text_primary"],
                    activebackground=t["entry_bg"],
                    activeforeground=t["text_primary"]
                )
                
                # Rebind hover to standard behavior
                btn.bind("<Enter>", lambda e, b=btn, h=t["entry_bg"]: b.config(bg=h))
                btn.bind("<Leave>", lambda e, b=btn, c=t["card_bg"]: b.config(bg=c))
