import tkinter as tk
from tkinter import ttk

class SettingsPanel(tk.Frame):
    def __init__(self, app, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.build()

    def build(self):
        self.card = tk.Frame(self, bg="#252538", bd=0, highlightbackground="#313244", highlightthickness=1)
        self.card.pack(fill=tk.BOTH, expand=True)

        self.header = tk.Frame(self.card, bg="#252538", padx=10, pady=5)
        self.header.pack(fill=tk.X)
        
        self.lbl_recent = tk.Label(self.header, text="🕒 Recent:", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        self.lbl_recent.pack(side=tk.LEFT, padx=(10, 2))

        self.cbo_recent = ttk.Combobox(self.header, width=45, state="readonly")
        self.cbo_recent.pack(side=tk.LEFT, padx=(0, 10), ipady=1)
        self.cbo_recent.bind("<<ComboboxSelected>>", self.app.on_recent_selected)
        
        self.btn_advanced_close = tk.Button(self.header, text="✕", command=self.app.toggle_advanced, bd=0, relief="flat", cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.btn_advanced_close.pack(side=tk.RIGHT, padx=5)

        self.content = tk.Frame(self.card, bg="#252538")
        self.content.pack(fill=tk.BOTH, expand=True)
        
        self.app.state.advanced_visible = False

        self.nbk_config = ttk.Notebook(self.content)
        self.nbk_config.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tab_filters = tk.Frame(self.nbk_config)
        self.tab_sharing = tk.Frame(self.nbk_config)

        self.nbk_config.add(self.tab_filters, text="⚙️ Filter Config")
        self.nbk_config.add(self.tab_sharing, text="☁️ LAN Sharing")

        self.tab_filters_border = tk.Frame(self.tab_filters, bg="#252538", bd=0, highlightthickness=1)
        self.tab_filters_border.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.ent_extensions = self.create_tab_input(
            self.tab_filters_border, "Allowed Extensions", self.app.config["allowed_extensions"],
            "E.g. .py, .md, .kt. Leave empty to allow all extensions."
        )
        self.ent_ignored_folders = self.create_tab_input(
            self.tab_filters_border, "Excluded Folders", self.app.config["ignored_folders"],
            "Comma-separated folder list to skip during recursive search."
        )
        self.ent_ignored_files = self.create_tab_input(
            self.tab_filters_border, "Excluded Files / Wildcards", self.app.config["ignored_files"],
            "Files or extensions to skip (e.g. .env, .gitignore, stress_test.py)."
        )

        self.ent_redact = self.create_tab_input(
            self.tab_filters_border, "Sensitive Keywords Redaction (API Keys, Secrets)", self.app.config.get("redact_keywords", ""),
            "List words (comma-separated) to automatically replace with [REDACTED]."
        )

        self.frm_pills = tk.Frame(self.tab_filters_border, bg="#252538", height=25)
        self.frm_pills.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.frm_behavior = tk.Frame(self.tab_filters_border, bg="#252538")
        self.frm_behavior.pack(fill=tk.X, padx=10, pady=5)

        self.var_use_regex = tk.BooleanVar(value=self.app.config.get("use_regex", False))
        self.cb_regex = tk.Checkbutton(self.frm_behavior, text="Regex", variable=self.var_use_regex, command=self.app.on_checkbox_updated)
        self.cb_regex.pack(side=tk.LEFT, padx=5)

        self.var_parse_gitignore = tk.BooleanVar(value=self.app.config.get("parse_gitignore", True))
        self.cb_gitignore = tk.Checkbutton(self.frm_behavior, text="Parse .gitignore", variable=self.var_parse_gitignore, command=self.app.on_checkbox_updated)
        self.cb_gitignore.pack(side=tk.LEFT, padx=5)

        self.var_watch_live = tk.BooleanVar(value=self.app.config.get("watch_live_updates", True))
        self.cb_watch_live = tk.Checkbutton(self.frm_behavior, text="Watch Live Updates", variable=self.var_watch_live, command=self.app.on_checkbox_updated)
        self.cb_watch_live.pack(side=tk.LEFT, padx=5)

        self.var_sound = tk.BooleanVar(value=self.app.config.get("sound_enabled", True))
        self.cb_sound = tk.Checkbutton(self.frm_behavior, text="Sounds", variable=self.var_sound, command=self.app.on_checkbox_updated)
        self.cb_sound.pack(side=tk.LEFT, padx=5)

        self.btn_reset = tk.Button(self.tab_filters_border, text="Reset defaults", command=self.app.reset_defaults, bg="#252538",
                                   bd=0, font=("Segoe UI", 8, "underline"), cursor="hand2")
        self.btn_reset.pack(anchor="e", padx=10, pady=(0, 5))

        self.tab_sharing_border = tk.Frame(self.tab_sharing, bg="#252538", bd=0, highlightthickness=1)
        self.tab_sharing_border.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sharing_container = tk.Frame(self.tab_sharing_border, bg="#252538", padx=10, pady=10)
        sharing_container.pack(fill=tk.BOTH, expand=True)

        lbl_share_title = tk.Label(sharing_container, text="📡 Share clipboard contents over local network", font=("Segoe UI", 10, "bold"))
        lbl_share_title.pack(anchor="w")

        lbl_share_desc = tk.Label(sharing_container, text="Clicking below starts a local HTTP daemon serving your active code package.\nAny device (phone, laptop) on the same Wi-Fi can retrieve it.", justify=tk.LEFT)
        lbl_share_desc.pack(anchor="w", pady=(5, 10))

        self.btn_lan_share = tk.Button(sharing_container, text="🌐 Start LAN Share Server", command=self.app.show_share_menu,
                                       bg="#89b4fa", fg="#11111b", bd=0, font=("Segoe UI", 10, "bold"), cursor="hand2", padx=20, pady=10)
        self.btn_lan_share.pack(anchor="w")

        self.mnu_share = tk.Menu(self.app.root, tearoff=0)
        self.mnu_share.add_command(label="🌐 Share Normal", command=lambda: self.app.start_share_server_with_mode("None"))
        self.mnu_share.add_command(label="🧹 Share Comments & Whitespace Stripped", command=lambda: self.app.start_share_server_with_mode("1. Comments & Whitespace Stripping"))
        self.mnu_share.add_command(label="🦴 Share Skeleton & Call Graph", command=lambda: self.app.start_share_server_with_mode("2. Skeleton (Signatures & Call Graph)"))
        self.mnu_share.add_command(label="🌿 Share Git Diff Mode", command=lambda: self.app.start_share_server_with_mode("3. Git Diff / Change-Context Mode"))

        self.lbl_share_status = tk.Label(sharing_container, text="Server status: Stopped", font=("Segoe UI", 9, "italic"))
        self.lbl_share_status.pack(anchor="w", pady=(5, 0))

        self.ent_extensions.bind("<KeyRelease>", self.app.on_entry_changed)
        self.ent_ignored_folders.bind("<KeyRelease>", self.app.on_entry_changed)
        self.ent_ignored_files.bind("<KeyRelease>", self.app.on_entry_changed)
        self.ent_redact.bind("<KeyRelease>", self.app.on_entry_changed)


    def create_tab_input(self, parent, label_text, default_val, help_text):
        frame = tk.Frame(parent, bg="#252538")
        frame.pack(fill=tk.X, padx=10, pady=(5, 5))
        
        lbl = tk.Label(frame, text=label_text, bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"), anchor="w")
        lbl.pack(fill=tk.X)
        
        entry = tk.Entry(frame, bg="#313244", fg="#cdd6f4", bd=0, insertbackground="#cdd6f4",
                         highlightbackground="#45475a", highlightcolor="#89b4fa", highlightthickness=1,
                         font=("Segoe UI", 10), relief="flat")
        entry.insert(0, default_val)
        entry.pack(fill=tk.X, pady=(2, 1), ipady=4)
        
        help_lbl = tk.Label(frame, text=help_text, bg="#252538", fg="#7f849c", font=("Segoe UI", 8, "italic"), anchor="w")
        help_lbl.pack(fill=tk.X)
        
        return entry
