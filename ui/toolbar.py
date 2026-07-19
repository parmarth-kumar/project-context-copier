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

        last_mode = self.app.config.get("last_copy_mode", "Normal")
        self.var_copy_mode = tk.StringVar(value=last_mode)
        
        self.lbl_mode_desc = tk.Label(self.frm_action, text="", font=("Segoe UI", 8, "italic"), bg="#1e1e2e", fg="#a6adc8", anchor="e")
        self.lbl_mode_desc.pack(fill=tk.X, pady=(2, 0))
        
        def save_mode(*args):
            import re
            from config import save_config
            val = self.var_copy_mode.get()
            
            if "(disabled)" in val:
                # Revert to Normal
                self.var_copy_mode.set("Normal")
                return
                
            base_val = re.sub(r'\s*\(~.*?\)$', '', val).strip()
            self.app.config["last_copy_mode"] = base_val
            save_config(self.app.config)
            
            if hasattr(self.app.cache, 'mode_descriptions'):
                self.lbl_mode_desc.config(text=self.app.cache.mode_descriptions.get(base_val, ""))
            else:
                desc = {
                    "Normal": "Copies complete file contents.",
                    "Compact Context": "Removes comments and extra whitespace. Smaller token usage.",
                    "Code Structure": "Only classes, methods and signatures. Ideal for architecture discussions.",
                    "Mermaid Graph": "Generates a flowchart of function calls.",
                    "Git Diff": "Copies only changed code."
                }.get(base_val, "")
                self.lbl_mode_desc.config(text=desc)
                
            if hasattr(self.app.state, 'selected_preview_file') and self.app.state.selected_preview_file:
                if hasattr(self.app, 'load_active_file_preview'):
                    self.app.load_active_file_preview(preserve_scroll=True)
            
        self.var_copy_mode.trace_add("write", save_mode)
        
        from tkinter import ttk
        self.copy_mode_dropdown = ttk.Combobox(self.frm_copy_row, textvariable=self.var_copy_mode, 
                                             values=["Normal", "Compact Context", "Code Structure", "Mermaid Graph", "Git Diff"],
                                             state="readonly", width=25, font=("Segoe UI", 10, "bold"), style="CopyMode.TCombobox")
        self.copy_mode_dropdown.pack(side=tk.RIGHT, padx=(5, 0), fill=tk.Y)
        
        save_mode()
        
        self.frm_copy_group = tk.Frame(self.frm_copy_row, bg="#1e1e2e")
        self.frm_copy_group.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        self.copy_button = create_action_button(self.frm_copy_group, "📋 Copy Context", self.app.copy_filtered_selection)
        self.copy_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 2))
        
        self.btn_export_options = create_action_button(self.frm_copy_group, "▼", self.show_export_menu)
        self.btn_export_options.pack(side=tk.RIGHT, fill=tk.Y)

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

    def show_export_menu(self):
        from config import THEMES
        t = THEMES[self.app.state.current_theme]
        
        menu = tk.Menu(self.app.root, tearoff=0)
        menu.config(
            bg=t["card_bg"], fg=t["text_primary"], 
            activebackground=t["accent"], 
            activeforeground="#11111b" if self.app.state.current_theme == "dark" else t["bg"],
            font=("Segoe UI", 9)
        )
        
        menu.add_command(label="📋 Copy to Clipboard", command=self.app.copy_filtered_selection)
        menu.add_separator()
        menu.add_command(label="📝 Save as Markdown...", command=lambda: self.app.export_bundle_to_file("markdown"))
        menu.add_command(label="📄 Save as Text...", command=lambda: self.app.export_bundle_to_file("text"))
        menu.add_separator()
        menu.add_command(label="🌐 Share over LAN", command=self.app.show_share_menu)
        
        x = self.btn_export_options.winfo_rootx()
        y = self.btn_export_options.winfo_rooty() + self.btn_export_options.winfo_height()
        menu.post(x, y)

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
