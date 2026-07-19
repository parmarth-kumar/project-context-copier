import tkinter as tk
from tkinter import filedialog, ttk
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None
import os
from core import (
    copy_to_clipboard,
    read_file,
    is_git_repo,
    compress_comments_whitespace,
    compact_blank_lines,
    compact_indent,
    remove_comments,
    generate_skeleton,
    generate_project_mermaid_graph,
    get_git_diff,
    get_local_ip,
)
import json
import re
import socket
import threading
import subprocess
import winsound
from http.server import BaseHTTPRequestHandler, HTTPServer
from config import DEFAULT_CONFIG, THEMES, CONFIG_FILE, load_config, save_config
from ui.common import AutoScrollbar, create_action_button

# Windows high DPI support
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass








# --- CONTEXT COMPRESSION UTILITIES ---
















# --- LAN HTTP SHARE SERVER LOGIC ---


class ShareHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return  # Suppress logging

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(self.server.copied_data.encode("utf-8"))


class ShareServer:
    def __init__(self, data):
        self.data = data
        self.server = None
        self.thread = None
        self.port = 8080

    def start(self):
        ip = get_local_ip()
        while self.port < 8120:
            try:
                self.server = HTTPServer((ip, self.port), ShareHandler)
                self.server.copied_data = self.data
                self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
                self.thread.start()
                return f"http://{ip}:{self.port}"
            except Exception:
                self.port += 1
        return None

    def stop(self):
        if self.server:
            self.server.shutdown()


class ProjectContextCopierApp:
    def __init__(self, root):

        from types import SimpleNamespace
        self.ui = SimpleNamespace()
        self.state = SimpleNamespace()
        self.cache = SimpleNamespace()
        self.root = root
        self.root.title("Project Context Copier")
        
        # Load Config and Layout position memory
        self.config = load_config()
        self.root.geometry(self.config.get("geometry", "1000x850"))
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(True, True)

        # State Variables
        self.state.current_theme = self.config.get("theme", "dark")

        self.apply_theme_title_bar()
        self.state.active_folder = None
        self.state.raw_selected_files = []
        self.state.active_files = []
        self.state.active_relative_paths = []
        self.state.unchecked_files = set()
        self.state.debounce_timer = None
        self.state.share_server = None
        self.ui.win_tooltip = None
        self.state.selected_preview_file = None
        self.state.toast_queue = []
        self.state.toast_active = False
        self.state.warning_timer = None
        
        # Real-time modification watch variables
        self.cache.preview_file_mtime = None
        self.cache.active_files_mtimes = {}
        self.cache.active_folder_mtime = None
        self.cache.stats_cache = {}

        self.create_widgets()
        
        if self.config.get("advanced_visible", False):
            self.toggle_advanced()
            
        try:
            tab_index = self.config.get("advanced_tab_index", 0)
            self.settings.nbk_config.select(tab_index)
        except Exception:
            pass
            
        self.apply_current_theme()

        # Window Position Saving on Close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Keyboard Shortcuts
        self.root.bind("<Control-o>", lambda e: self.load_folder())
        self.root.bind("<Control-i>", lambda e: self.load_files())
        self.root.bind("<Control-c>", lambda e: self.copy_filtered_selection())
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())
        self.root.bind("<Control-r>", lambda e: self.reset_defaults())

        # Start real-time background file modification watcher
        self.poll_file_changes()
        self.detect_active_preset()
        
        # Show the fully rendered window
        self.root.deiconify()

    def apply_theme_title_bar(self, window=None):
        target_win = window if window else self.root
        target_win.update()
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(target_win.winfo_id())
            if hwnd == 0:
                hwnd = target_win.winfo_id()
            value = ctypes.c_int(1 if self.state.current_theme == "dark" else 0)
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
            )
            if result != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, ctypes.byref(value), ctypes.sizeof(value)
                )
        except Exception:
            pass

    def on_close(self):
        """Saves current window geometry to config and exits."""
        self.config["geometry"] = self.root.winfo_geometry()
        self.config["advanced_visible"] = getattr(self.state, "advanced_visible", False)
        if hasattr(self, 'settings') and hasattr(self.settings, 'nbk_config'):
            try:
                self.config["advanced_tab_index"] = self.settings.nbk_config.index(self.settings.nbk_config.select())
            except Exception:
                pass
        if hasattr(self, 'ui') and hasattr(self.ui, 'pan_explorer'):
            try:
                self.config["explorer_sash"] = self.ui.pan_explorer.sash_coord(0)[0]
            except Exception:
                pass
        save_config(self.config)
        if self.state.share_server:
            self.state.share_server.stop()
        self.root.destroy()

    def play_sound(self, sound_type):
        """Plays custom tactile sounds if enabled."""
        if not self.config.get("sound_enabled", True):
            return
        try:
            if sound_type == "click":
                winsound.Beep(800, 30)
            elif sound_type == "success":
                winsound.Beep(1200, 100)
                winsound.Beep(1500, 150)
            elif sound_type == "error":
                winsound.Beep(400, 200)
        except Exception:
            pass

    def toggle_theme(self):
        self.state.current_theme = "light" if self.state.current_theme == "dark" else "dark"
        self.play_sound("click")
        self.apply_current_theme()

    def toggle_advanced(self):
        if self.state.advanced_visible:
            self.settings.pack_forget()
            self.state.advanced_visible = False
        else:
            self.settings.pack(fill=tk.X, padx=20, pady=(0, 10), after=self.ui.frm_header)
            self.state.advanced_visible = True

    def _apply_theme_recursive(self, widget, t):
        wtype = widget.winfo_class()
        
        # Determine background dynamically based on parent (unless it's root)
        bg_color = t["bg"]
        if widget != self.root:
            try:
                parent_bg = widget.winfo_parent()
                parent_widget = self.root.nametowidget(parent_bg)
                bg_color = parent_widget.cget("bg")
            except Exception:
                bg_color = t["card_bg"] # fallback
                
        try:
            if wtype in ("Frame", "Label", "Checkbutton", "Radiobutton"):
                widget.configure(bg=bg_color)
            if wtype in ("Label", "Checkbutton", "Radiobutton"):
                widget.configure(fg=t["text_primary"])
            if wtype == "Checkbutton":
                widget.configure(activebackground=bg_color, activeforeground=t["text_primary"], selectcolor=t["entry_bg"])
            if wtype == "Entry":
                widget.configure(bg=t["entry_bg"], fg=t["text_primary"], insertbackground=t["text_primary"], 
                                 highlightbackground=t["entry_border"], highlightcolor=t["accent"])
        except Exception:
            pass # Some ttk widgets or custom components might not support standard bg/fg
            
        for child in widget.winfo_children():
            self._apply_theme_recursive(child, t)

    def apply_current_theme(self):
        t = THEMES[self.state.current_theme]
        self.config["theme"] = self.state.current_theme
        save_config(self.config)
        self.apply_theme_title_bar()
        
        self.root.configure(bg=t["bg"])
        
        # 1. Recursive Auto-Theme
        self._apply_theme_recursive(self.root, t)
        
        # 2. Specific Overrides
        self.ui.lbl_title.configure(fg=t["accent"])
        
        theme_btn_text = "☀️ Light Mode" if self.state.current_theme == "dark" else "🌙 Dark Mode"
        self.ui.btn_theme.configure(
            text=theme_btn_text, bg=t["card_bg"], fg=t["text_primary"],
            activebackground=t["entry_bg"], activeforeground=t["text_primary"]
        )

        self.settings.nbk_config.configure(style="TNotebook")
        
        for frame in [self.settings.tab_filters, self.settings.tab_sharing]:
            frame.configure(bg=t["card_bg"])
            self._apply_theme_recursive(frame, t) # Re-apply to children so they inherit card_bg
            
        self.settings.tab_filters_border.configure(highlightbackground=t["entry_border"])
        self.settings.tab_sharing_border.configure(highlightbackground=t["entry_border"])

        # Help Labels (secondary text color instead of primary)
        try:
            for child in self.settings.tab_filters_border.winfo_children():
                for subchild in child.winfo_children():
                    if subchild.winfo_class() == "Label" and "E.g." in subchild.cget("text") or "List words" in subchild.cget("text") or "Files or extensions" in subchild.cget("text") or "Comma-separated folder list" in subchild.cget("text"):
                        subchild.configure(fg=t["text_secondary"])
        except Exception:
            pass

        # Action panel buttons
        if hasattr(self, 'toolbar'):
            self.toolbar.frm_action.configure(bg=t["bg"])
            self.toolbar.frm_load.configure(bg=t["bg"])
            self.toolbar.frm_copy_row.configure(bg=t["bg"])
            self.toolbar.frm_quick_presets.configure(bg=t["bg"])
            self.toolbar.lbl_quick_presets.configure(bg=t["bg"], fg=t["accent"])
        # Status footer
        if hasattr(self, 'status'):
            # Note: StatusBar is a ttk.Frame, but we configure its labels
             # if we used ttk styles, or skip if tk.Frame
            self.status.stats_label.configure(bg=t["bg"], fg=t["text_primary"])
            self.status.label.configure(bg=t["bg"])
            self.update_status_color()

        buttons_to_setup = [
            (self.toolbar.load_folder_button if hasattr(self, 'toolbar') else self.ui.btn_load_folder, t["accent"], t["accent_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]),
            (self.toolbar.load_files_button if hasattr(self, 'toolbar') else self.ui.btn_load_files, t["accent"], t["accent_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]),
            (self.toolbar.copy_button if hasattr(self, 'toolbar') else self.ui.btn_copy, t["copy_btn"], t["copy_btn_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]),
            (self.toolbar.btn_export_options if hasattr(self, 'toolbar') else None, t["copy_btn"], t["copy_btn_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]),
            (self.ui.btn_theme, t["bg"], t["entry_bg"], t["text_primary"]),
            (self.ui.btn_settings, t["bg"], t["entry_bg"], t["text_primary"]),
            (self.settings.btn_reset, t["card_bg"], t["entry_bg"], t["lbl_status_error"]),
            (self.settings.btn_advanced_close, t["card_bg"], t["entry_bg"], t["lbl_status_error"]),
        ]
        
        if hasattr(self, 'toolbar'):
            from tkinter import ttk
            if not isinstance(self.toolbar.copy_mode_dropdown, ttk.Combobox):
                self.toolbar.copy_mode_dropdown["menu"].config(
                    bg=t["bg"], fg=t["text_primary"], font=("Segoe UI", 9), bd=0,
                    activebackground=t["copy_btn_hover"], 
                    activeforeground="#11111b" if self.state.current_theme == "dark" else t["bg"]
                )
        
        if hasattr(self, 'toolbar'):
            for btn in self.toolbar.quick_presets_buttons:
                buttons_to_setup.append((btn, t["card_bg"], t["entry_bg"], t["text_primary"]))
        
        if hasattr(self.state, 'share_server') and self.state.share_server:
            buttons_to_setup.append((self.settings.btn_lan_share, t["lbl_status_error"], t["lbl_status_error"], "#11111b" if self.state.current_theme == "dark" else t["bg"]))
        elif hasattr(self, 'settings'):
            buttons_to_setup.append((self.settings.btn_lan_share, t["accent"], t["accent_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]))

        for btn, bg_color, hover_color, fg_color in buttons_to_setup:
            btn.configure(bg=bg_color, fg=fg_color, activebackground=hover_color, activeforeground=fg_color, cursor="hand2")
            btn.bind("<Enter>", lambda e, b=btn, h=hover_color: b.config(bg=h))
            btn.bind("<Leave>", lambda e, b=btn, c=bg_color: b.config(bg=c))

        if hasattr(self.ui, 'mnu_copy') and self.ui.mnu_copy:
            self.ui.mnu_copy.configure(bg=t["card_bg"], fg=t["text_primary"], activebackground=t["accent"], activeforeground="#11111b" if self.state.current_theme == "dark" else t["bg"])
        if hasattr(self, 'settings') and self.settings.mnu_share:
            self.settings.mnu_share.configure(bg=t["card_bg"], fg=t["text_primary"], activebackground=t["accent"], activeforeground="#11111b" if self.state.current_theme == "dark" else t["bg"])

        self.ui.pan_explorer.configure(bg=t["bg"])
        if hasattr(self, 'sidebar'):
            self.sidebar.configure(bg=t['bg'], highlightbackground=t['entry_border'])
            self.sidebar.title_label.configure(bg=t["bg"], fg=t["text_primary"])
            self.sidebar.search_wrapper.configure(bg=t["bg"])
            self.sidebar.search_frame.configure(bg=t["entry_bg"], highlightbackground=t["entry_border"])
            self.sidebar.search_icon.configure(bg=t["entry_bg"], fg=t["text_secondary"])
            self.sidebar.btn_clear_search.configure(bg=t["entry_bg"], fg=t["text_secondary"])
            is_placeholder = self.sidebar.search_entry.get() == "Search files..."
            self.sidebar.search_entry.configure(bg=t["entry_bg"], fg=t["text_secondary"] if is_placeholder else t["text_primary"], insertbackground=t["text_primary"], highlightthickness=0)
            self.sidebar.tree.configure(bg=t["console_bg"], fg=t["text_primary"])
            self.sidebar.tree.tag_configure("code", foreground=t["tag_code"])
            self.sidebar.tree.tag_configure("doc", foreground=t["tag_doc"])
            self.sidebar.tree.tag_configure("config", foreground=t["tag_config"])
            self.sidebar.tree.tag_configure("hover", background=t["entry_border"])

        if hasattr(self, 'preview'):
            self.preview.configure(bg=t['bg'], highlightbackground=t['entry_border'])
            self.preview.title_label.configure(bg=t["bg"], fg=t["text_primary"])
            self.preview.meta_wrapper.configure(bg=t["bg"])
            self.preview.meta_label.configure(bg=t["bg"], fg=t["text_secondary"])
            self.preview.code_view.configure(bg=t["console_bg"], fg=t["text_primary"])

        if hasattr(self, 'status'):
            self.status.configure(bg=t['bg'])
        if hasattr(self, 'toolbar'):
            self.toolbar.configure(bg=t['bg'])

        scrollbar_style = ttk.Style()
        scrollbar_style.theme_use('clam')
        scrollbar_style.configure('TFrame', background=t['bg'])
        scrollbar_style.layout("Dark.Vertical.TScrollbar", [
            ('Vertical.Scrollbar.trough', {
                'children': [
                    ('Vertical.Scrollbar.thumb', {'expand': '1', 'sticky': 'nswe'})
                ],
                'sticky': 'ns'
            })
        ])
        scrollbar_style.configure("Dark.Vertical.TScrollbar", gripcount=0, background=t["scrollbar_thumb"], troughcolor=t["console_bg"], bordercolor=t["console_bg"], lightcolor=t["console_bg"], darkcolor=t["console_bg"], width=10)
        scrollbar_style.map("Dark.Vertical.TScrollbar", background=[('active', t["entry_border"]), ('pressed', t["text_secondary"])])

        # --- Header Recent Combobox theming ---
        is_dark = self.state.current_theme == "dark"
        fg_on_accent = "#11111b" if is_dark else t["bg"]

        self.ui.frm_recent.configure(bg=t["bg"])
        self.ui.frm_recent_inner.configure(bg=t["entry_bg"], highlightbackground=t["entry_border"])


        combo_style = ttk.Style()
        combo_style.theme_use('clam')
        combo_style.configure(
            "Header.TCombobox",
            fieldbackground=t["entry_bg"],
            background=t["entry_bg"],
            foreground=t["text_primary"],
            arrowcolor=t["text_secondary"],
            bordercolor=t["entry_bg"],
            lightcolor=t["entry_bg"],
            darkcolor=t["entry_bg"],
            relief="flat",
            padding=2
        )
        combo_style.map(
            "Header.TCombobox",
            fieldbackground=[('readonly', t["entry_bg"])],
            foreground=[('readonly', t["text_primary"])],
            background=[('readonly', t["entry_bg"])],
            arrowcolor=[('active', t["accent"])],
            selectbackground=[('readonly', t["entry_bg"]), ('focus', t["entry_bg"])],
            selectforeground=[('readonly', t["text_primary"]), ('focus', t["text_primary"])]
        )
        
        btn_fg = "#11111b" if self.state.current_theme == "dark" else t["bg"]
        combo_style.configure(
            "CopyMode.TCombobox",
            fieldbackground=t["copy_btn"],
            background=t["copy_btn"],
            foreground=btn_fg,
            arrowcolor=btn_fg,
            bordercolor=t["copy_btn"],
            lightcolor=t["copy_btn"],
            darkcolor=t["copy_btn"],
            relief="flat",
            padding=2
        )
        combo_style.map(
            "CopyMode.TCombobox",
            fieldbackground=[('readonly', t["copy_btn"])],
            foreground=[('readonly', btn_fg)],
            background=[('readonly', t["copy_btn"])],
            arrowcolor=[('active', btn_fg)],
            selectbackground=[('readonly', t["copy_btn"]), ('focus', t["copy_btn"])],
            selectforeground=[('readonly', btn_fg), ('focus', btn_fg)]
        )

        # Dropdown listbox colors (ttk doesn't expose this via style alone)
        self.root.option_add('*TCombobox*Listbox.background', t["entry_bg"])
        self.root.option_add('*TCombobox*Listbox.foreground', t["text_primary"])
        self.root.option_add('*TCombobox*Listbox.selectBackground', t["accent"])
        self.root.option_add('*TCombobox*Listbox.selectForeground', fg_on_accent)
        self.root.option_add('*TCombobox*Listbox.font', ("Segoe UI", 9))

        try:
            self.root.tk.eval(f'''
                set popdown [ttk::combobox::PopdownWindow {self.ui.cbo_recent}]
                if {{[winfo exists $popdown]}} {{
                    $popdown.f.l configure -background "{t['entry_bg']}" -foreground "{t['text_primary']}" -selectbackground "{t['accent']}" -selectforeground "{fg_on_accent}"
                }}
            ''')
        except Exception:
            pass

        self.refresh_pills()

    def create_widgets(self):
        self.main_frame = self.root
        
        self.create_header()
        
        from ui.toolbar import Toolbar
        self.toolbar = Toolbar(
            self,
            self.main_frame
        )
        self.toolbar.pack(fill=tk.X, padx=20)
        
        from ui.settings_panel import SettingsPanel
        self.settings = SettingsPanel(
            self,
            self.main_frame
        )
        self.update_recent_history_ui()
        
        # Toast notifications overlay
        self.ui.frm_toast_banner = tk.Frame(self.main_frame, bg="#a6e3a1", height=0)

        from ui.statusbar import StatusBar
        self.status = StatusBar(
            self,
            self.main_frame,
            pady=5
        )
        self.status.pack(fill=tk.X, padx=20, side=tk.BOTTOM)

        # --- SPLIT SCREEN EXPLORER VIEW ---
        self.ui.pan_explorer = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL, bd=0, sashwidth=5, sashrelief="flat")
        self.ui.pan_explorer.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        from ui.explorer_panel import ExplorerPanel
        self.sidebar = ExplorerPanel(
            self,
            self.ui.pan_explorer,
            bd=0, highlightthickness=1
        )
        
        from ui.preview_panel import PreviewPanel
        self.preview = PreviewPanel(
            self,
            self.ui.pan_explorer,
            bd=0, highlightthickness=1
        )

        # Add panes to Splitter
        self.ui.pan_explorer.add(self.sidebar, minsize=250, width=375, stretch="never")
        self.ui.pan_explorer.add(self.preview, minsize=350, stretch="always")
        
        if "explorer_sash" in self.config:
            def restore_sash():
                try:
                    self.ui.pan_explorer.update_idletasks()
                    self.ui.pan_explorer.sash_place(0, self.config["explorer_sash"], 0)
                except Exception:
                    pass
            self.root.after(100, restore_sash)
        

        # Initial placeholders
        empty_tree_state = (
            "\n\n\n\n\n\n\n\n\n\n"
            "Drop a folder here\n\n"
            "or\n\n"
            "Load Folder/Files"
        )
        self.set_tree_preview_content(empty_tree_state, center=True)
        self.set_code_view_content("Select a file leaf in the tree view to inspect its content.")

    def create_header(self):
        # Header layout
        self.ui.frm_header = tk.Frame(self.root, bg="#1e1e2e", pady=10)
        self.ui.frm_header.pack(fill=tk.X, padx=20)

        self.ui.lbl_title = tk.Label(self.ui.frm_header, text="Project Context Copier", bg="#1e1e2e", fg="#cba6f7",
                                  font=("Segoe UI", 15, "bold"), anchor="w")
        self.ui.lbl_title.pack(side=tk.LEFT)

        self.ui.btn_settings = tk.Button(self.ui.frm_header, text="⚙️ Settings", command=self.toggle_advanced,
                                   bg="#252538", fg="#cdd6f4", bd=0, relief="flat", padx=10, pady=5,
                                   font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.ui.btn_settings.pack(side=tk.RIGHT)

        self.ui.btn_theme = tk.Button(self.ui.frm_header, text="☀️ Light Mode", command=self.toggle_theme,
                                   bg="#252538", fg="#cdd6f4", bd=0, relief="flat", padx=10, pady=5,
                                   font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.ui.btn_theme.pack(side=tk.RIGHT, padx=(0, 10))

        # --- RECENT PROJECTS (compact header dropdown, sits between title and action buttons) ---
        self.ui.frm_recent = tk.Frame(self.ui.frm_header, bg="#1e1e2e")
        self.ui.frm_recent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(25, 10))

        self.ui.frm_recent_inner = tk.Frame(
            self.ui.frm_recent, bg="#313244", bd=0,
            highlightthickness=1, highlightbackground="#45475a"
        )
        self.ui.frm_recent_inner.pack(side=tk.RIGHT, ipady=1)



        style = ttk.Style()
        style.theme_use('clam')
        self.ui.cbo_recent = ttk.Combobox(
            self.ui.frm_recent_inner, width=30, state="readonly",
            style="Header.TCombobox", font=("Segoe UI", 9)
        )
        self.ui.cbo_recent.pack(side=tk.LEFT, padx=(2, 8), pady=3)
        self.ui.cbo_recent.set("No recent projects")
        self.ui.cbo_recent.bind("<<ComboboxSelected>>", self.on_recent_selected)
        self.ui.cbo_recent.bind("<Enter>", self.show_combo_tooltip)
        self.ui.cbo_recent.bind("<Leave>", self.hide_combo_tooltip)


    # --- PILLS TAGS RENDER LOGIC ---
    def refresh_pills(self):
        """Builds interactive tag pills for active inclusions/exclusions."""
        for widget in self.settings.frm_pills.winfo_children():
            widget.destroy()

        t = THEMES[self.state.current_theme]
        
        raw_exts = self.settings.ent_extensions.get()
        raw_folders = self.settings.ent_ignored_folders.get()

        exts = [e.strip() for e in raw_exts.split(",") if e.strip()]
        folders = [f.strip() for f in raw_folders.split(",") if f.strip()]

        lbl_tags = tk.Label(self.settings.frm_pills, text="Active Tags: ", bg=t["card_bg"], fg=t["text_secondary"], font=("Segoe UI", 8, "bold"))
        lbl_tags.pack(side=tk.LEFT)

        # Render max 3 of each tag category
        for idx, ext in enumerate(exts[:3]):
            self.create_pill(self.settings.frm_pills, ext, lambda e=ext: self.remove_pill_filter("extensions", e), t, t["accent"])
        for idx, fld in enumerate(folders[:3]):
            self.create_pill(self.settings.frm_pills, fld, lambda f=fld: self.remove_pill_filter("folders", f), t, t["lbl_status_error"])

    def create_pill(self, parent, text, remove_command, theme, pill_color):
        pill = tk.Frame(parent, bg=pill_color, padx=5, pady=1)
        pill.pack(side=tk.LEFT, padx=3)
        
        # Pill label
        lbl = tk.Label(pill, text=text, bg=pill_color, fg="#11111b" if self.state.current_theme == "dark" else theme["bg"], font=("Segoe UI", 7, "bold"))
        lbl.pack(side=tk.LEFT)

        # Delete cross button
        btn_del = tk.Label(pill, text=" ×", bg=pill_color, fg="#11111b" if self.state.current_theme == "dark" else theme["bg"], font=("Segoe UI", 8, "bold"), cursor="hand2")
        btn_del.pack(side=tk.LEFT)
        btn_del.bind("<Button-1>", lambda e: remove_command())

    def remove_pill_filter(self, filter_type, value):
        self.play_sound("click")
        if filter_type == "extensions":
            current = self.settings.ent_extensions.get()
            items = [x.strip() for x in current.split(",") if x.strip()]
            if value in items:
                items.remove(value)
            self.settings.ent_extensions.delete(0, tk.END)
            self.settings.ent_extensions.insert(0, ", ".join(items))
        elif filter_type == "folders":
            current = self.settings.ent_ignored_folders.get()
            items = [x.strip() for x in current.split(",") if x.strip()]
            if value in items:
                items.remove(value)
            self.settings.ent_ignored_folders.delete(0, tk.END)
            self.settings.ent_ignored_folders.insert(0, ", ".join(items))
        self.refresh_filter()

    # --- TOAST NOTIFICATIONS ANIMATION ---
    def show_toast(self, message, state="success"):
        """Queues and animates a success/error toast banner from the bottom."""
        self.state.toast_queue.append((message, state))
        if not getattr(self.state, 'toast_active', False):
            self.process_toast_queue()

    def process_toast_queue(self):
        if not self.state.toast_queue:
            self.state.toast_active = False
            return
            
        self.state.toast_active = True
        message, state = self.state.toast_queue.pop(0)

        t = THEMES[self.state.current_theme]
        bg_col = t["lbl_status_success"] if state == "success" else t["lbl_status_error"]
        fg_col = "#11111b" if self.state.current_theme == "dark" else t["bg"]

        # Configure toast
        if hasattr(self.ui, 'frm_toast_banner') and self.ui.frm_toast_banner.winfo_exists():
            self.ui.frm_toast_banner.destroy()
            
        self.ui.frm_toast_banner = tk.Frame(self.root, bg=bg_col, bd=0, highlightbackground=t["entry_border"], highlightthickness=1)
        self.ui.frm_toast_banner.place(relx=0.5, rely=1.0, anchor="s", relwidth=0.6, height=45)

        lbl = tk.Label(self.ui.frm_toast_banner, text=message, bg=bg_col, fg=fg_col, font=("Segoe UI", 10, "bold"))
        lbl.pack(expand=True, fill=tk.BOTH)

        # Slide Up Animation
        def slide_up(curr_height):
            if curr_height < 45:
                self.ui.frm_toast_banner.place(rely=1.0 - (curr_height / self.root.winfo_height()))
                self.root.after(10, lambda: slide_up(curr_height + 5))
            else:
                # Auto dismissal
                self.root.after(2500, self.hide_toast)

        slide_up(5)

    def hide_toast(self):
        """Slides the toast banner back down."""
        def slide_down(curr_height):
            if curr_height > 0:
                self.ui.frm_toast_banner.place(rely=1.0 - (curr_height / self.root.winfo_height()))
                self.root.after(10, lambda: slide_down(curr_height - 5))
            else:
                self.ui.frm_toast_banner.place_forget()
                self.process_toast_queue()

        if hasattr(self.ui, 'frm_toast_banner') and self.ui.frm_toast_banner.winfo_exists():
            slide_down(45)
        else:
            self.process_toast_queue()

    # --- LAN SHARING SERVER CONTROL ---
    # --- LAN SHARING SERVER CONTROL ---
    def toggle_lan_share(self):
        """Starts/stops the background LAN http data server."""
        self.play_sound("click")
        t = THEMES[self.state.current_theme]
        if self.state.share_server:
            # Stop server
            self.state.share_server.stop()
            self.state.share_server = None
            self.settings.btn_lan_share.config(text="🌐 Start LAN Share Server", bg=t["accent"])
            self.settings.lbl_share_status.config(text="Server status: Stopped")
        else:
            self.show_share_menu()

    def show_share_menu(self):
        """Shows the dropdown sharing options menu right below the LAN share button."""
        if self.state.share_server:
            self.toggle_lan_share()
        else:
            self.play_sound("click")
            self.root.update_idletasks()
            x = self.settings.btn_lan_share.winfo_rootx()
            y = self.settings.btn_lan_share.winfo_rooty() + self.settings.btn_lan_share.winfo_height()
            self.settings.mnu_share.post(x, y)

    def start_share_server_with_mode(self, mode):
        """Starts the background LAN HTTP sharing server compiled in the selected compression mode."""
        t = THEMES[self.state.current_theme]
        output_text = self.get_bundled_data_by_mode(mode)
        if not output_text or output_text.startswith("[No git"):
            self.settings.lbl_share_status.config(text="Server status: Load active files first before sharing", fg=t["lbl_status_error"])
            self.play_sound("error")
            return

        self.state.share_server = ShareServer(output_text)
        url = self.state.share_server.start()
        if url:
            self.settings.btn_lan_share.config(text="🛑 Stop LAN Share Server", bg=t["lbl_status_error"])
            # Format clean representation of compression mode in status
            short_mode = mode.split(".")[0].strip() if "." in mode else "Normal"
            self.settings.lbl_share_status.config(text=f"Server status: Running ({short_mode} Mode) at {url}", fg=t["lbl_status_ready"])
            # Copy LAN URL to clipboard
            copy_to_clipboard(url)
            self.show_toast("LAN URL copied to clipboard!", "success")
            self.play_sound("success")
        else:
            self.settings.lbl_share_status.config(text="Server status: Port allocation failed", fg=t["lbl_status_error"])
            self.play_sound("error")

    def poll_file_changes(self):
        """Periodically polls the active folder and preview file for modifications outside the application."""
        try:
            if hasattr(self, 'settings') and not self.settings.var_watch_live.get():
                return
            # 1. Reload the code preview in real-time if the selected file has changed on disk
            if self.state.selected_preview_file and os.path.exists(self.state.selected_preview_file):
                try:
                    curr_mtime = os.path.getmtime(self.state.selected_preview_file)
                    if self.cache.preview_file_mtime is not None and curr_mtime != self.cache.preview_file_mtime:
                        self.cache.preview_file_mtime = curr_mtime
                        self.load_active_file_preview(preserve_scroll=True)
                except Exception:
                    pass

            # 2. Check if active folder contents or file mtimes have changed
            if self.state.active_folder and os.path.exists(self.state.active_folder):
                changed = False
                
                # Check if any mtimes of active files have changed
                for fp in list(self.state.active_files):
                    if os.path.exists(fp):
                        try:
                            mtime = os.path.getmtime(fp)
                            if fp not in self.cache.active_files_mtimes or self.cache.active_files_mtimes[fp] != mtime:
                                self.cache.active_files_mtimes[fp] = mtime
                                # Invalidate cache for this file
                                if fp in self.cache.stats_cache:
                                    del self.cache.stats_cache[fp]
                                changed = True
                        except Exception:
                            pass
                    else:
                        # File was deleted
                        if fp in self.cache.active_files_mtimes:
                            del self.cache.active_files_mtimes[fp]
                        if fp in self.cache.stats_cache:
                            del self.cache.stats_cache[fp]
                        changed = True

                # Check if new files appeared or files were deleted in active folder itself
                try:
                    curr_folder_mtime = os.path.getmtime(self.state.active_folder)
                    if self.cache.active_folder_mtime is not None and curr_folder_mtime != self.cache.active_folder_mtime:
                        self.cache.active_folder_mtime = curr_folder_mtime
                        changed = True
                except Exception:
                    pass

                if changed:
                    self.refresh_filter()
        except Exception:
            pass
        finally:
            # Re-schedule every 1.5 seconds
            self.root.after(1500, self.poll_file_changes)

    # --- RECENT PATHS HISTORY ---
    def get_recent_display_name(self, path, history):
        """Generates a clean display name, disambiguating duplicates if needed."""
        import os
        basename = os.path.basename(os.path.normpath(path))
        
        duplicates = [p for p in history if os.path.basename(os.path.normpath(p)) == basename]
        if len(duplicates) > 1:
            parent = os.path.basename(os.path.dirname(os.path.normpath(path)))
            return f"📁 {basename}  ({parent}/...)"
        return f"📁 {basename}"

    def update_recent_history_ui(self):
        history = self.config.get("recent_folders", [])
        
        self.state.recent_mapping = {}
        for p in history:
            self.state.recent_mapping[self.get_recent_display_name(p, history)] = p
            
        self.ui.cbo_recent["values"] = list(self.state.recent_mapping.keys())

        if hasattr(self.state, 'active_folder') and self.state.active_folder and self.state.active_folder in history:
            self.ui.cbo_recent.set(self.get_recent_display_name(self.state.active_folder, history))
        elif history:
            self.ui.cbo_recent.set("🕒  Open recent...")
        else:
            self.ui.cbo_recent.set("Recent projects...")
            
    def show_combo_tooltip(self, event):
        selected_display = self.ui.cbo_recent.get()
        if not hasattr(self.state, 'recent_mapping') or selected_display not in self.state.recent_mapping:
            return
            
        full_path = self.state.recent_mapping[selected_display]
        if getattr(self.ui, 'combo_tooltip', None):
            self.ui.combo_tooltip.destroy()
            
        self.ui.combo_tooltip = tk.Toplevel(self.root)
        self.ui.combo_tooltip.wm_overrideredirect(True)
        
        x = self.root.winfo_pointerx() + 15
        y = self.root.winfo_pointery() + 15
        self.ui.combo_tooltip.wm_geometry(f"+{x}+{y}")
        
        t = THEMES[self.state.current_theme]
        lbl = tk.Label(self.ui.combo_tooltip, text=full_path, bg=t["entry_bg"], fg=t["text_primary"], justify=tk.LEFT,
                       highlightbackground=t["entry_border"], highlightthickness=1, font=("Segoe UI", 8), padx=5, pady=3)
        lbl.pack()

    def hide_combo_tooltip(self, event):
        if getattr(self.ui, 'combo_tooltip', None):
            self.ui.combo_tooltip.destroy()
            self.ui.combo_tooltip = None

    def on_recent_selected(self, event=None):
        selected_display = self.ui.cbo_recent.get()
        if not hasattr(self.state, 'recent_mapping') or selected_display not in self.state.recent_mapping:
            return
            
        selected = self.state.recent_mapping[selected_display]
        if os.path.exists(selected):
            self.play_sound("click")
            self.state.active_folder = selected
            try:
                self.cache.active_folder_mtime = os.path.getmtime(selected)
            except Exception:
                self.cache.active_folder_mtime = None
            self.cache.stats_cache = {}
            self.cache.active_files_mtimes = {}
            self.state.raw_selected_files = []
            self.status.label.config(text=f"Loaded from history: {os.path.basename(selected)}", fg=THEMES[self.state.current_theme]["lbl_status_ready"])
            self.refresh_filter()
            self.show_toast("Loaded project from history!", "success")
            
            # Put the selected item at the top of history
            self.add_to_recent_history(selected)

    def add_to_recent_history(self, path):
        history = self.config.get("recent_folders", [])
        if path in history:
            history.remove(path)
        history.insert(0, path)
        self.config["recent_folders"] = history[:5]  # Limit to last 5
        save_config(self.config)
        self.update_recent_history_ui()

    # --- FILTER OPTIONS CALLBACKS ---
    def on_checkbox_updated(self):
        self.play_sound("click")
        self.config.update({
            "use_regex": self.settings.var_use_regex.get(),
            "parse_gitignore": self.settings.var_parse_gitignore.get(),
            "watch_live_updates": self.settings.var_watch_live.get(),
            "sound_enabled": self.settings.var_sound.get()
        })
        save_config(self.config)
        self.refresh_filter()

    def detect_active_preset(self):
        from config import PRESETS
        
        current_allowed = self.settings.ent_extensions.get().strip()
        current_folders = self.settings.ent_ignored_folders.get().strip()
        current_files = self.settings.ent_ignored_files.get().strip()

        matched_preset = "Custom"
        for name, data in PRESETS.items():
            if data["allowed"] == current_allowed and data["folders"] == current_folders and data["files"] == current_files:
                matched_preset = name
                break
                
        if hasattr(self, 'toolbar'):
            self.toolbar.update_active_preset(matched_preset)


    def apply_preset_by_name(self, preset):
        self.play_sound("click")
        if hasattr(self, 'toolbar'):
            self.toolbar.update_active_preset(preset)
        if preset == "Custom":
            self.settings.ent_extensions.delete(0, tk.END)
            self.settings.ent_ignored_folders.delete(0, tk.END)
            self.settings.ent_ignored_files.delete(0, tk.END)
            self.refresh_filter()
            self.show_toast("Cleared filters (Custom mode)", "success")
            return
            
        from config import PRESETS

        if preset in PRESETS:
            data = PRESETS[preset]
            self.settings.ent_extensions.delete(0, tk.END)
            self.settings.ent_extensions.insert(0, data["allowed"])
            
            self.settings.ent_ignored_folders.delete(0, tk.END)
            self.settings.ent_ignored_folders.insert(0, data["folders"])
            
            self.settings.ent_ignored_files.delete(0, tk.END)
            self.settings.ent_ignored_files.insert(0, data["files"])
            
            self.refresh_filter()
            self.show_toast(f"Swapped presets to {preset}!", "success")

    # --- AUTO GITIGNORE PARSER ---
    def read_gitignore_rules(self, folder):
        """Reads local gitignore rules and converts them to python regex arrays."""
        rules = []
        gi_path = os.path.join(folder, ".gitignore")
        if os.path.exists(gi_path):
            try:
                with open(gi_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Simple glob conversion to regex
                            reg = line.replace(".", "\\.").replace("*", ".*").replace("?", ".")
                            if not reg.startswith("^"):
                                reg = ".*" + reg
                            rules.append(re.compile(reg, re.IGNORECASE))
            except Exception:
                pass
        return rules

    # --- ACTIVE FILTERING LOGIC ---
    def get_parsed_settings(self):
        raw_exts = self.settings.ent_extensions.get()
        raw_folders = self.settings.ent_ignored_folders.get()
        raw_files = self.settings.ent_ignored_files.get()
        raw_redact = self.settings.ent_redact.get()

        self.config.update({
            "allowed_extensions": raw_exts,
            "ignored_folders": raw_folders,
            "ignored_files": raw_files,
            "redact_keywords": raw_redact
        })
        save_config(self.config)

        # Parse Extensions
        extensions = []
        for ext in raw_exts.split(','):
            ext = ext.strip().lower()
            if ext:
                if not ext.startswith('.') and not self.settings.var_use_regex.get():
                    ext = '.' + ext
                extensions.append(ext)

        # Parse Ignores
        ignored_folders = [f.strip() for f in raw_folders.split(',') if f.strip()]
        ignored_files = [f.strip() for f in raw_files.split(',') if f.strip()]

        return extensions, ignored_folders, ignored_files

    def on_entry_changed(self, event=None):
        if self.state.debounce_timer:
            self.root.after_cancel(self.state.debounce_timer)
        self.state.debounce_timer = self.root.after(300, self.refresh_filter)

    def on_search_changed(self, event=None):
        """Highlights matching files or hides unrelated tree structures dynamically."""
        self.refresh_filter()

    def refresh_filter(self):
        self.state.debounce_timer = None
        self.detect_active_preset()
        extensions, ignored_folders, ignored_files = self.get_parsed_settings()

        self.state.active_files = []
        self.state.active_relative_paths = []
        


        # Local gitignore rules
        gitignore_regex_rules = []
        if self.settings.var_parse_gitignore.get() and self.state.active_folder:
            if is_git_repo(self.state.active_folder):
                gitignore_regex_rules = self.read_gitignore_rules(self.state.active_folder)

        search_query = self.sidebar.search_entry.get().strip().lower()
        if search_query == "search files...":
            search_query = ""

        if not self.state.active_folder and not self.state.raw_selected_files:
            empty_tree_state = (
                "\n\n\n\n\n\n"
                "Drop a folder here\n\n"
                "or\n\n"
                "Load Folder/Files"
            )
            self.set_tree_preview_content(empty_tree_state, center=True)
            return

        if self.state.active_folder:
            for root, dirs, files in os.walk(self.state.active_folder):
                dirs[:] = [d for d in dirs if d not in ignored_folders]
                
                # Apply gitignore rules to directories
                if gitignore_regex_rules:
                    rel_dir_path = os.path.relpath(root, self.state.active_folder)
                    if rel_dir_path != ".":
                        if any(rule.match(rel_dir_path) for rule in gitignore_regex_rules):
                            dirs[:] = []  # Stop walking ignored subdirs
                            continue

                for file in files:
                    fp = os.path.join(root, file)
                    rel_path = os.path.relpath(fp, self.state.active_folder)



                    # Filter: Gitignore match
                    if gitignore_regex_rules and any(rule.match(rel_path) for rule in gitignore_regex_rules):
                        continue

                    # Filter: Search query check
                    if search_query and search_query not in file.lower() and search_query not in rel_path.lower():
                        continue

                    # Exclusions check
                    is_ignored = False
                    if self.settings.var_use_regex.get():
                        # regex exclusion matching
                        for ignored in ignored_files:
                            try:
                                if re.search(ignored, file, re.IGNORECASE):
                                    is_ignored = True
                                    break
                            except Exception:
                                pass
                    else:
                        # standard matching
                        for ignored in ignored_files:
                            if file == ignored:
                                is_ignored = True
                                break
                            if ignored.startswith('.') and file.lower().endswith(ignored.lower()):
                                is_ignored = True
                                break
                    if is_ignored:
                        continue

                    # Inclusions check
                    if self.settings.var_use_regex.get():
                        matches_inc = False
                        if not extensions:
                            matches_inc = True
                        else:
                            for ext in extensions:
                                try:
                                    if re.search(ext, file, re.IGNORECASE):
                                        matches_inc = True
                                        break
                                except Exception:
                                    pass
                        if not matches_inc:
                            continue
                    else:
                        if extensions and not any(file.lower().endswith(ext) for ext in extensions):
                            continue

                    # Safe file validation
                    self.state.active_files.append(fp)
                    folder_name = os.path.basename(self.state.active_folder)
                    self.state.active_relative_paths.append(os.path.join(folder_name, rel_path))
                    
                    if len(self.state.active_files) >= 5000:
                        break
                        
                if len(self.state.active_files) >= 5000:
                    self.show_toast("Warning: File limit (5000) reached. Please narrow filters.", "error")
                    break

        elif self.state.raw_selected_files:
            for fp in self.state.raw_selected_files:
                file = os.path.basename(fp)

                # Filter: Search query check
                if search_query and search_query not in file.lower():
                    continue

                is_ignored = False
                for ignored in ignored_files:
                    if file == ignored:
                        is_ignored = True
                        break
                    if ignored.startswith('.') and file.lower().endswith(ignored.lower()):
                        is_ignored = True
                        break
                if is_ignored:
                    continue

                if not extensions or any(file.lower().endswith(ext) for ext in extensions):
                    self.state.active_files.append(fp)
                    self.state.active_relative_paths.append(file)

        # Initialize mtimes for active files if not tracked
        for fp in self.state.active_files:
            try:
                if fp not in self.cache.active_files_mtimes and os.path.exists(fp):
                    self.cache.active_files_mtimes[fp] = os.path.getmtime(fp)
            except Exception:
                pass

        # Update Tree representation
        self.render_tree_view()
        self.calculate_stats()
        self.refresh_pills()

        # Real-time preview update check
        if hasattr(self.state, 'selected_preview_file') and self.state.selected_preview_file:
            if self.state.selected_preview_file not in self.state.active_files:
                self.state.selected_preview_file = None
                self.set_code_view_content("Select a file leaf in the tree view to inspect its content.")
            else:
                self.load_active_file_preview()

    # --- CODE PREVIEW RENDERING & COLOR CODING ---
    def render_tree_view(self):
        """Constructs and draws the tree representation in the Left panel, styling line colors by file type."""
        if not self.state.active_files:
            self.set_tree_preview_content("No files match the current parameters.")
            return

        tree_struct = {}
        for path, fp in zip(self.state.active_relative_paths, self.state.active_files):
            parts = path.replace('\\', '/').split('/')
            current = tree_struct
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = fp
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
        tree_lines = []
        self.cache.tree_line_mapping = {}
        def print_tree(d, indent=""):
            items = list(d.items())
            folder_files = []
            for i, (key, value) in enumerate(items):
                is_last = (i == len(items) - 1)
                marker = "└── " if is_last else "├── "
                
                if isinstance(value, dict):
                    line_num = len(tree_lines) + 1
                    tree_lines.append("") # Placeholder
                    
                    new_indent = indent + ("    " if is_last else "│   ")
                    sub_files = print_tree(value, new_indent)
                    folder_files.extend(sub_files)
                    
                    if not sub_files:
                        checkbox = "☐ "
                    else:
                        all_checked = all(f not in self.state.unchecked_files for f in sub_files)
                        all_unchecked = all(f in self.state.unchecked_files for f in sub_files)
                        if all_checked:
                            checkbox = "☑ "
                        elif all_unchecked:
                            checkbox = "☐ "
                        else:
                            checkbox = "[-] "
                            
                    tree_lines[line_num - 1] = f"{indent}{marker}{checkbox}{key}".ljust(200)
                    self.cache.tree_line_mapping[line_num] = ("folder", sub_files)
                else:
                    line_num = len(tree_lines) + 1
                    checkbox = "☐ " if value in self.state.unchecked_files else "☑ "
                    tree_lines.append(f"{indent}{marker}{checkbox}{key}".ljust(200))
                    self.cache.tree_line_mapping[line_num] = ("file", value)
                    folder_files.append(value)
                    
            return folder_files

        print_tree(tree_struct)
        self.set_tree_preview_content("\n".join(tree_lines))
        
        # Color coding highlighting via Tags
        self.sidebar.tree.config(state="normal")
        t = THEMES[self.state.current_theme]
        
        # Setup tags
        self.sidebar.tree.tag_configure("code", foreground=t["tag_code"])
        self.sidebar.tree.tag_configure("doc", foreground=t["tag_doc"])
        self.sidebar.tree.tag_configure("config", foreground=t["tag_config"])
        self.sidebar.tree.tag_configure("selected", background=t["accent"], foreground="#11111b" if self.state.current_theme == "dark" else t["bg"], font=("Consolas", 9, "bold"))
        self.sidebar.tree.tag_configure("search_match", font=("Consolas", 9, "bold"), foreground=t.get("accent", "#89b4fa"))
        
        search_term = self.sidebar.search_entry.get().strip().lower()
        if search_term == "search files...":
            search_term = ""

        # Iterate lines and assign tag colors
        for line_idx in range(1, len(tree_lines) + 1):
            line_txt = self.sidebar.tree.get(f"{line_idx}.0", f"{line_idx}.end")
            ext = os.path.splitext(line_txt)[1].lower()
            
            node_type, data = self.cache.tree_line_mapping.get(line_idx, (None, None))
            is_selected = node_type == "file" and data == getattr(self.state, "selected_preview_file", None)
            
            if is_selected:
                self.sidebar.tree.tag_add("selected", f"{line_idx}.0", f"{line_idx}.end + 1c")
            else:
                if ext in [".py", ".kt", ".java", ".js", ".jsx", ".ts", ".tsx"]:
                    self.sidebar.tree.tag_add("code", f"{line_idx}.0", f"{line_idx}.end")
                elif ext in [".md", ".txt", ".rst"]:
                    self.sidebar.tree.tag_add("doc", f"{line_idx}.0", f"{line_idx}.end")
                elif ext in [".json", ".xml", ".properties", ".gradle", ".env", ".gitignore"]:
                    self.sidebar.tree.tag_add("config", f"{line_idx}.0", f"{line_idx}.end")
            
            if search_term and not is_selected:
                start_idx = 0
                while True:
                    idx = line_txt.lower().find(search_term, start_idx)
                    if idx == -1:
                        break
                    self.sidebar.tree.tag_add("search_match", f"{line_idx}.{idx}", f"{line_idx}.{idx + len(search_term)}")
                    start_idx = idx + len(search_term)
                
        self.sidebar.tree.config(state="disabled")

    def set_tree_preview_content(self, text, center=False):
        yview = self.sidebar.tree.yview()
        xview = self.sidebar.tree.xview()
        
        self.sidebar.tree.config(state="normal")
        self.sidebar.tree.delete("1.0", tk.END)
        
        if center:
            self.sidebar.tree.insert(tk.END, text, "center")
            self.sidebar.tree.tag_configure("center", justify='center')
        else:
            self.sidebar.tree.insert(tk.END, text)
            
        self.sidebar.tree.config(state="disabled")
        
        if yview:
            self.sidebar.tree.yview_moveto(yview[0])
        if xview:
            self.sidebar.tree.xview_moveto(xview[0])

    def set_code_view_content(self, text, preserve_scroll=False):
        yview = None
        if preserve_scroll:
            yview = self.preview.code_view.yview()
        elif getattr(self.state, 'selected_preview_file', None) and getattr(self.cache, 'file_scroll_states', {}).get(self.state.selected_preview_file):
            yview = self.cache.file_scroll_states[self.state.selected_preview_file]
        self.preview.code_view.config(state="normal")
        self.preview.code_view.delete("1.0", tk.END)
        self.preview.code_view.insert(tk.END, text)
        self.preview.code_view.config(state="disabled")
        if yview:
            self.preview.code_view.update_idletasks()
            self.preview.code_view.yview_moveto(yview[0])

    # --- SPLIT SCREEN EXPLORER CLICK & INTERACTION ---
    def load_active_file_preview(self, preserve_scroll=False):
        """Loads, redacts, and displays the content of the currently selected file."""
        if not self.state.selected_preview_file or not os.path.exists(self.state.selected_preview_file):
            if hasattr(self, 'preview'):
                self.preview.meta_label.config(text=" Select a file to preview...")
            return
        try:
            self.cache.preview_file_mtime = os.path.getmtime(self.state.selected_preview_file)
        except Exception:
            self.cache.preview_file_mtime = None
        content = read_file(self.state.selected_preview_file)
        
        # Update meta information label
        if hasattr(self, 'preview'):
            file_name = os.path.basename(self.state.selected_preview_file)
            size_kb = len(content.encode('utf-8')) / 1024
            lines = content.count('\n') + 1
            _, ext = os.path.splitext(file_name)
            lang = ext.replace('.', '').upper() if ext else "TEXT"
            meta_text = f" File: {file_name}   |   Size: {size_kb:.2f} KB   |   Lines: {lines}   |   Lang: {lang}"
            self.preview.meta_label.config(text=meta_text)

        # Apply keyword redactions to preview window
        redact_keys = [k.strip() for k in self.settings.ent_redact.get().split(",") if k.strip()]
        for secret in redact_keys:
            content = content.replace(secret, "[REDACTED]")
            
        # Apply mode formatting if selected
        if hasattr(self, 'toolbar') and hasattr(self.toolbar, 'var_copy_mode'):
            import re
            mode = re.sub(r'\s*\(~.*?\)$', '', self.toolbar.var_copy_mode.get()).strip()
            if mode == "Compact Context":
                content = compress_comments_whitespace(content, self.state.selected_preview_file)
            elif mode == "Code Structure":
                content = generate_skeleton(content, self.state.selected_preview_file)
            elif mode == "Git Diff":
                content = self.get_file_git_diff(self.state.selected_preview_file)
            elif mode == "Mermaid Graph":
                content = generate_project_mermaid_graph([self.state.selected_preview_file])
                
        _, ext = os.path.splitext(self.state.selected_preview_file)
        if ext.lower() == ".md":
            self.render_rich_markdown(content, preserve_scroll=preserve_scroll)
        else:
            self.set_code_view_content(content, preserve_scroll=preserve_scroll)

    def get_file_git_diff(self, filepath):
        """Gets Git diff changes specifically for a single file."""
        if not self.state.active_folder or not os.path.exists(filepath):
            return "[No git repository loaded]"
        try:
            rel_path = os.path.relpath(filepath, self.state.active_folder)
            res = subprocess.run(
                ["git", "diff", rel_path],
                cwd=self.state.active_folder, capture_output=True, text=True, check=True, encoding="utf-8", errors="replace"
            )
            res_cached = subprocess.run(
                ["git", "diff", "--cached", rel_path],
                cwd=self.state.active_folder, capture_output=True, text=True, check=True, encoding="utf-8", errors="replace"
            )
            diff = res.stdout + "\n" + res_cached.stdout
            return diff.strip() if diff.strip() else "[No unstaged/staged git modifications in this file]"
        except Exception as e:
            return f"[Error running git diff: {str(e)}]"

    def insert_styled_text(self, text):
        """Parses inline markdown syntax (bold, italic, inline code) and inserts into the text widget."""
        pattern = re.compile(r'(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)')
        parts = pattern.split(text)
        
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                val = part[2:-2]
                self.preview.code_view.insert(tk.END, val, "bold")
            elif part.startswith("*") and part.endswith("*"):
                val = part[1:-1]
                self.preview.code_view.insert(tk.END, val, "italic")
            elif part.startswith("`") and part.endswith("`"):
                val = part[1:-1]
                self.preview.code_view.insert(tk.END, val, "inline_code")
            else:
                self.preview.code_view.insert(tk.END, part, "normal")

    def render_rich_markdown(self, markdown_text, preserve_scroll=False):
        """Parses markdown block elements (headers, quotes, bullets, code blocks) and renders in code preview."""
        yview = None
        if preserve_scroll:
            yview = self.preview.code_view.yview()
        elif getattr(self.state, 'selected_preview_file', None) and getattr(self.cache, 'file_scroll_states', {}).get(self.state.selected_preview_file):
            yview = self.cache.file_scroll_states[self.state.selected_preview_file]
        self.preview.code_view.config(state="normal")
        self.preview.code_view.delete("1.0", tk.END)

        t = THEMES[self.state.current_theme]
        # Set up markdown tag styles
        self.preview.code_view.tag_configure("h1", font=("Segoe UI", 16, "bold"), foreground=t["accent"], spacing1=10, spacing3=5)
        self.preview.code_view.tag_configure("h2", font=("Segoe UI", 13, "bold"), foreground=t["accent"], spacing1=8, spacing3=4)
        self.preview.code_view.tag_configure("h3", font=("Segoe UI", 11, "bold"), foreground=t["text_primary"], spacing1=6, spacing3=3)
        self.preview.code_view.tag_configure("bullet", font=("Segoe UI", 10), lmargin1=20, lmargin2=35, spacing1=3)
        self.preview.code_view.tag_configure("quote", font=("Segoe UI", 10, "italic"), foreground=t["text_secondary"], background=t["entry_bg"], lmargin1=30, lmargin2=30, spacing1=6, spacing3=6)
        self.preview.code_view.tag_configure("codeblock", font=("Consolas", 9), background=t["console_bg"] if self.state.current_theme == "light" else "#181825", spacing1=2, spacing3=2, lmargin1=15, lmargin2=15)
        
        # Inline styling configurations
        self.preview.code_view.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.preview.code_view.tag_configure("italic", font=("Segoe UI", 10, "italic"))
        self.preview.code_view.tag_configure("inline_code", font=("Consolas", 10), background=t["entry_bg"], foreground=t["accent"])
        self.preview.code_view.tag_configure("normal", font=("Segoe UI", 10), spacing1=4, spacing3=4)

        lines = markdown_text.splitlines()
        in_code_block = False
        
        for line in lines:
            # Code Blocks Toggle
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
                
            if in_code_block:
                self.preview.code_view.insert(tk.END, line + "\n", "codeblock")
                continue
                
            # Headers
            if line.startswith("# "):
                self.preview.code_view.insert(tk.END, line[2:] + "\n", "h1")
            elif line.startswith("## "):
                self.preview.code_view.insert(tk.END, line[3:] + "\n", "h2")
            elif line.startswith("### "):
                self.preview.code_view.insert(tk.END, line[4:] + "\n", "h3")
            # Blockquotes
            elif line.startswith(">"):
                val = line[1:].strip()
                self.preview.code_view.insert(tk.END, val + "\n", "quote")
            # Bullets
            elif line.strip().startswith("* ") or line.strip().startswith("- "):
                bullet_char = "• "
                val = line.strip()[2:]
                indent_spaces = len(line) - len(line.lstrip())
                self.preview.code_view.insert(tk.END, " " * indent_spaces + bullet_char, "bullet")
                self.insert_styled_text(val + "\n")
            # Normal paragraph
            else:
                if not line.strip():
                    self.preview.code_view.insert(tk.END, "\n", "normal")
                else:
                    self.insert_styled_text(line + "\n")

        self.preview.code_view.config(state="disabled")
        if yview:
            self.preview.code_view.update_idletasks()
            self.preview.code_view.yview_moveto(yview[0])

    def on_tree_single_click(self, event):
        """Toggles checkbox on click, and displays text content on the Right Explorer panel."""
        try:
            self.sidebar.tree.tag_remove(tk.SEL, "1.0", tk.END)
            index = self.sidebar.tree.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            col_num = int(index.split('.')[1])
            
            if not hasattr(self.cache, 'tree_line_mapping') or line_num not in self.cache.tree_line_mapping:
                return "break"
                
            node_type, data = self.cache.tree_line_mapping[line_num]
            line_text = self.sidebar.tree.get(f"{line_num}.0", f"{line_num}.end")
            
            checkbox_start = -1
            checkbox_len = 2
            if '☑ ' in line_text:
                checkbox_start = line_text.index('☑ ')
            elif '☐ ' in line_text:
                checkbox_start = line_text.index('☐ ')
            elif '[-] ' in line_text:
                checkbox_start = line_text.index('[-] ')
                checkbox_len = 4
                
            clicked_checkbox = False
            if checkbox_start != -1 and col_num >= checkbox_start and col_num < checkbox_start + checkbox_len:
                clicked_checkbox = True

            if node_type == "file":
                target_path = data
                if clicked_checkbox:
                    if target_path in self.state.unchecked_files:
                        self.state.unchecked_files.remove(target_path)
                    else:
                        self.state.unchecked_files.add(target_path)
                        
                    self.render_tree_view()
                    self.calculate_stats()
                    self.refresh_pills()
                    self.play_sound("click")
                else:
                    self.play_sound("click")
                    
                    if getattr(self.state, 'selected_preview_file', None) and hasattr(self, 'preview'):
                        if not hasattr(self.cache, 'file_scroll_states'):
                            self.cache.file_scroll_states = {}
                        self.cache.file_scroll_states[self.state.selected_preview_file] = self.preview.code_view.yview()
                        
                    self.state.selected_preview_file = target_path
                    self.render_tree_view()
                    self.load_active_file_preview()
                
            elif node_type == "folder":
                sub_files = data
                all_checked = all(f not in self.state.unchecked_files for f in sub_files)
                
                if all_checked:
                    for f in sub_files:
                        self.state.unchecked_files.add(f)
                else:
                    for f in sub_files:
                        if f in self.state.unchecked_files:
                            self.state.unchecked_files.remove(f)
                            
                self.render_tree_view()
                self.calculate_stats()
                self.refresh_pills()
                self.play_sound("click")

        except Exception:
            pass
        return "break"

    # --- INTERACTIVE HOVER CARD TOOLTIPS ---
    def hide_tree_tooltip(self, event=None):
        self.cache.tooltip_last_line = None
        if self.ui.win_tooltip:
            self.ui.win_tooltip.destroy()
            self.ui.win_tooltip = None

    def on_tree_mouse_hover(self, event):
        """Creates dynamic popup tooltips with file metadata on mouseover."""
        try:
            index = self.sidebar.tree.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            try:
                self.sidebar.tree.tag_remove("hover", "1.0", tk.END)
                self.sidebar.tree.tag_add("hover", f"{line_num}.0", f"{line_num}.end + 1c")
            except Exception:
                pass
            
            if getattr(self.cache, 'tooltip_last_line', None) == line_num and getattr(self.ui, 'win_tooltip', None) and self.ui.win_tooltip.winfo_exists():
                x = self.root.winfo_pointerx() + 15
                y = self.root.winfo_pointery() + 10
                self.ui.win_tooltip.wm_geometry(f"+{x}+{y}")
                return
                
            self.cache.tooltip_last_line = line_num
            
            if not hasattr(self.cache, 'tree_line_mapping') or line_num not in self.cache.tree_line_mapping:
                self.cache.tooltip_last_line = None
                if getattr(self.ui, 'win_tooltip', None):
                    self.ui.win_tooltip.destroy()
                    self.ui.win_tooltip = None
                return
                
            node_type, data = self.cache.tree_line_mapping[line_num]
            
            if node_type == "file":
                if data in self.cache.stats_cache:
                    stats = self.cache.stats_cache[data]
                    kb_val = stats["size"] / 1024
                    raw_c = stats["raw_chars"]
                    tokens = raw_c / 4
                    lines = stats.get("lines")
                    
                    if lines is None:
                        try:
                            with open(data, 'r', encoding='utf-8', errors='replace') as f:
                                lines = sum(1 for _ in f)
                        except Exception:
                            lines = 0
                        stats["lines"] = lines
                        
                    tokens_str = f"{int(tokens)}" if tokens < 1000 else f"{tokens/1000:.1f}k"
                    tt_text = f"{os.path.basename(data)}\nSize: {kb_val:.1f} KB\nLines: {lines:,}\n≈ {tokens_str} tokens"
                else:
                    tt_text = f"{os.path.basename(data)}\nSize: Unknown"
            else:
                line_content = self.sidebar.tree.get(f"{line_num}.0", f"{line_num}.end")
                clean_name = line_content.replace("└── ", "").replace("├── ", "").replace("│   ", "").replace("☑ ", "").replace("☐ ", "").replace("[-] ", "").strip()
                tt_text = f"{clean_name} (Folder)"

            if self.ui.win_tooltip:
                self.ui.win_tooltip.destroy()

            self.ui.win_tooltip = tk.Toplevel(self.root)
            self.ui.win_tooltip.wm_overrideredirect(True)
            
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 10
            self.ui.win_tooltip.wm_geometry(f"+{x}+{y}")
            
            t = THEMES[self.state.current_theme]
            lbl = tk.Label(self.ui.win_tooltip, text=tt_text, bg=t["entry_bg"], fg=t["text_primary"], justify=tk.LEFT,
                           highlightbackground=t["entry_border"], highlightthickness=1, font=("Segoe UI", 8), padx=5, pady=3)
            lbl.pack()
        except Exception:
            if self.ui.win_tooltip:
                self.ui.win_tooltip.destroy()
                self.ui.win_tooltip = None

    def show_tree_context_menu(self, event):
        try:
            index = self.sidebar.tree.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            if not hasattr(self.cache, 'tree_line_mapping') or line_num not in self.cache.tree_line_mapping:
                return
                
            node_type, data = self.cache.tree_line_mapping[line_num]
            if node_type == "file":
                self.sidebar.tree.tag_remove(tk.SEL, "1.0", tk.END)
                self.sidebar.tree.tag_add(tk.SEL, f"{line_num}.0", f"{line_num}.end")
                
                menu = tk.Menu(self.root, tearoff=0)
                
                menu.add_command(label="Copy File (Normal)", command=lambda: self.copy_single_file(data, "Normal"))
                menu.add_command(label="Copy File (Compact Context)", command=lambda: self.copy_single_file(data, "Compact Context"))
                menu.add_command(label="Copy Code Structure", command=lambda: self.copy_single_file(data, "Code Structure"))
                menu.add_separator()
                menu.add_command(label="Copy Relative Path", command=lambda: self.copy_relative_path(data))
                menu.add_command(label="Open in Explorer", command=lambda: self.open_in_explorer(data))
                
                # Setup colors
                t = THEMES[self.state.current_theme]
                menu.config(bg=t["card_bg"], fg=t["text_primary"], activebackground=t["accent"], activeforeground="#11111b" if self.state.current_theme == "dark" else t["bg"])
                
                menu.post(event.x_root, event.y_root)
        except Exception:
            pass

    def copy_single_file(self, filepath, mode):
        try:
            content = read_file(filepath)
            if mode == "Compact Context":
                content = compress_comments_whitespace(content, filepath)
            elif mode == "Code Structure":
                content = generate_skeleton(content, filepath)
                
            if self.state.active_folder:
                rel_path = os.path.relpath(filepath, self.state.active_folder)
            else:
                rel_path = os.path.basename(filepath)
            
            final_text = f"File: {rel_path}\n"
            final_text += "=" * 40 + "\n"
            final_text += f"```{os.path.splitext(filepath)[1].strip('.')}\n"
            final_text += content
            if not content.endswith("\n"):
                final_text += "\n"
            final_text += "```\n"
            
            copy_to_clipboard(final_text)
            self.show_toast(f"Copied {os.path.basename(filepath)} ({mode})", "success")
            self.play_sound("success")
        except Exception as e:
            self.show_toast(f"Error copying: {str(e)}", "error")
            self.play_sound("error")
            
    def copy_relative_path(self, filepath):
        try:
            if self.state.active_folder:
                rel_path = os.path.relpath(filepath, self.state.active_folder)
            else:
                rel_path = os.path.basename(filepath)
            copy_to_clipboard(rel_path)
            self.show_toast("Relative path copied!", "success")
            self.play_sound("success")
        except Exception:
            pass
            
    def open_in_explorer(self, filepath):
        try:
            subprocess.run(['explorer', '/select,', os.path.normpath(filepath)])
        except Exception:
            pass

    # --- STATISTICS & TOKEN HEURISTICS COUNTER ---
    def calculate_stats(self):
        checked_files = [f for f in self.state.active_files if f not in self.state.unchecked_files]
        if not checked_files:
            self.status.stats_label.config(text="0 files loaded | 0.0 KB size | Estimated Tokens: 0")
            return

        total_files = len(checked_files)
        total_size = 0
        total_chars = 0
        
        mode1_chars = 0
        mode2_chars = 0
        ext_breakdown = {}

        for fp in checked_files:
            try:
                if os.path.exists(fp):
                    sz = os.path.getsize(fp)
                    total_size += sz
                    
                    mtime = os.path.getmtime(fp)
                    # Check cache first
                    if fp in self.cache.stats_cache and self.cache.stats_cache[fp]["mtime"] == mtime and self.cache.stats_cache[fp]["size"] == sz:
                        cached = self.cache.stats_cache[fp]
                        total_chars += cached["raw_chars"]
                        mode1_chars += cached["mode1_chars"]
                        mode2_chars += cached["mode2_chars"]
                    else:
                        file_content = read_file(fp)
                        raw_c = len(file_content)
                        
                        # Heuristics: Skip comments/skeleton algorithms for binary or error content
                        is_binary = file_content.startswith("[Binary file") or file_content.startswith("[Error reading")
                        m1_c = len(compress_comments_whitespace(file_content, fp)) if not is_binary else raw_c
                        m2_c = len(generate_skeleton(file_content, fp)) if not is_binary else raw_c
                        
                        total_chars += raw_c
                        mode1_chars += m1_c
                        mode2_chars += m2_c
                        
                        # Cache the results
                        self.cache.stats_cache[fp] = {
                            "mtime": mtime,
                            "size": sz,
                            "raw_chars": raw_c,
                            "mode1_chars": m1_c,
                            "mode2_chars": m2_c
                        }

                    # Large File safety checking warning
                    kb_val = sz / 1024
                    limit = self.config.get("large_file_threshold_kb", 200)
                    if kb_val > limit:
                        def clear_warning():
                            if getattr(self.state, "warning_timer", None) is not None:
                                if self.status.label.cget("text").startswith("⚠️"):
                                    self.status.label.config(
                                        text="Status: Ready",
                                        fg=THEMES[self.state.current_theme].get("text_secondary", "#a6adc8")
                                    )
                                self.state.warning_timer = None
                                if hasattr(self, 'update_status_color'):
                                    self.update_status_color()
                                    
                        if getattr(self.state, "warning_timer", None) is not None:
                            self.root.after_cancel(self.state.warning_timer)
                            
                        self.status.label.config(
                            text=f"⚠️ Warning: File '{os.path.basename(fp)}' is very large ({kb_val:.1f} KB)",
                            fg=THEMES[self.state.current_theme]["lbl_status_error"]
                        )
                        self.state.warning_timer = self.root.after(4000, clear_warning)
            except Exception:
                pass

            _, ext = os.path.splitext(fp)
            ext = ext.lower()
            if not ext:
                ext = "[no ext]"
            ext_breakdown[ext] = ext_breakdown.get(ext, 0) + 1

        sorted_exts = sorted(ext_breakdown.items(), key=lambda x: x[1], reverse=True)
        ext_strings = [f"{count} {ext}" for ext, count in sorted_exts[:3]]
        ext_summary = ", ".join(ext_strings)
        if len(sorted_exts) > 3:
            ext_summary += ", ..."

        kb_size = total_size / 1024
        
        tokens_raw = total_chars // 4
        tokens_mode1 = mode1_chars // 4
        tokens_mode2 = mode2_chars // 4
        
        self.status.stats_label.config(
            text=f"{total_files} file(s) loaded ({ext_summary}) | Size: {kb_size:.1f} KB | Est. Tokens: {tokens_raw:,} (Compact: {tokens_mode1:,} | Structure: {tokens_mode2:,})"
        )
        
        self.update_copy_mode_sizes()

    def update_copy_mode_sizes(self):
        if not hasattr(self, 'toolbar'): return
        
        if hasattr(self.cache, 'mode_size_timer') and self.cache.mode_size_timer:
            self.root.after_cancel(self.cache.mode_size_timer)
            
        def _trigger():
            snapshot = {
                "redact": self.settings.ent_redact.get(),
                "active_folder": self.state.active_folder,
                "active_files": list(self.state.active_files),
                "unchecked_files": set(self.state.unchecked_files),
            }
            import threading
            threading.Thread(target=self._calc_mode_sizes, args=(snapshot,), daemon=True).start()
            
        self.cache.mode_size_timer = self.root.after(300, _trigger)
        
    def _calc_mode_sizes(self, snapshot=None):
        modes = ["Normal", "Compact Context", "Code Structure", "Mermaid Graph", "Git Diff"]
        sizes = {}
        tokens = {}
        for m in modes:
            try:
                data = self.get_bundled_data_by_mode(m, snapshot=snapshot)
                sz = len(data.encode('utf-8')) if data else 0
                tks = len(data) // 4 if data else 0
                tokens[m] = tks
                
                if sz < 1024:
                    sizes[m] = f"{sz} B"
                else:
                    sizes[m] = f"{sz/1024:.1f} KB"
            except Exception:
                sizes[m] = "0 B"
                tokens[m] = 0
                
        normal_tks = tokens.get("Normal", 0)
        descriptions = {}
        for m in modes:
            base_desc = {
                "Normal": "Copies complete file contents.",
                "Compact Context": "Removes comments and extra whitespace.",
                "Code Structure": "Only classes, methods and signatures.",
                "Mermaid Graph": "Generates a flowchart of function calls.",
                "Git Diff": "Copies only changed code."
            }.get(m, "")
            
            tks = tokens.get(m, 0)
            if tks >= 1000:
                tk_str = f"≈ {tks/1000:.0f}k tokens"
            else:
                tk_str = f"≈ {tks} tokens"
                
            savings = ""
            if m != "Normal" and normal_tks > 0 and tks < normal_tks:
                pct = int((1.0 - (tks / normal_tks)) * 100)
                savings = f" ↓{pct}%"
                
            descriptions[m] = f"{m} ({tk_str}{savings}): {base_desc}"
                
        self.root.after(0, lambda: self._apply_mode_sizes(sizes, descriptions))
        
    def _apply_mode_sizes(self, sizes, descriptions=None):
        if not hasattr(self, 'toolbar'): return
        
        import re
        import tkinter as tk
        
        current = self.toolbar.var_copy_mode.get()
        base_current = re.sub(r'\s*\(~.*?\)$', '', current).strip()
        # Also strip disabled tag if present
        base_current = base_current.replace(' (disabled)', '').strip()
        
        is_git = bool(self.state.active_folder and os.path.exists(os.path.join(self.state.active_folder, ".git")))
        
        if base_current == "Git Diff" and not is_git:
            base_current = "Normal"
            self.toolbar.var_copy_mode.set(base_current)
            
        new_selected = None
        new_values = []
        
        for base_mode, size_str in sizes.items():
            display_str = f"{base_mode} (~{size_str})"
            if base_mode == "Git Diff" and not is_git:
                display_str += " (disabled)"
                
            new_values.append(display_str)
            if base_mode == base_current:
                new_selected = display_str
                
        from tkinter import ttk
        if isinstance(self.toolbar.copy_mode_dropdown, ttk.Combobox):
            self.toolbar.copy_mode_dropdown["values"] = new_values
        else:
            menu = self.toolbar.copy_mode_dropdown["menu"]
            menu.delete(0, "end")
            for val in new_values:
                state = "disabled" if "(disabled)" in val else "normal"
                menu.add_command(label=val, command=tk._setit(self.toolbar.var_copy_mode, val), state=state)
                
        if new_selected:
            self.toolbar.var_copy_mode.set(new_selected)
            
        if descriptions:
            self.cache.mode_descriptions = descriptions
            # Force update of the label immediately
            self.toolbar.lbl_mode_desc.config(text=descriptions.get(base_current, ""))
                


    def on_drop(self, event):
        paths = self.root.tk.splitlist(event.data)
        if not paths: return
        path = paths[0]
        if os.path.isdir(path):
            self.play_sound("success")
            self.state.active_folder = path
            try:
                self.cache.active_folder_mtime = os.path.getmtime(path)
            except Exception:
                self.cache.active_folder_mtime = None
            self.cache.stats_cache = {}
            self.cache.active_files_mtimes = {}
            self.state.raw_selected_files = []
            
            self.status.label.config(text=f"Status: Loaded folder '{os.path.basename(path)}'", fg=THEMES[self.state.current_theme]["lbl_status_ready"])
            self.refresh_filter()
            self.show_toast("Folder loaded via drag & drop!", "success")
            self.add_to_recent_history(path)
        else:
            self.play_sound("success")
            self.state.active_folder = os.path.dirname(path)
            self.state.raw_selected_files = list(paths)
            self.cache.active_folder_mtime = None
            self.cache.stats_cache = {}
            self.cache.active_files_mtimes = {}
            self.status.label.config(text=f"Status: Loaded {len(paths)} file(s)", fg=THEMES[self.state.current_theme]["lbl_status_ready"])
            self.refresh_filter()
            self.show_toast(f"Loaded {len(paths)} files via drag & drop!", "success")
            self.add_to_recent_history(self.state.active_folder)

    # --- FILE LOADER OPERATIONS ---
    def load_folder(self):
        folder_path = filedialog.askdirectory(title="Select folder to load")
        if not folder_path:
            self.status.label.config(text="Status: Folder selection canceled", fg=THEMES[self.state.current_theme]["lbl_status_error"])
            return

        self.play_sound("success")
        self.state.active_folder = folder_path
        try:
            self.cache.active_folder_mtime = os.path.getmtime(folder_path)
        except Exception:
            self.cache.active_folder_mtime = None
        self.cache.stats_cache = {}
        self.cache.active_files_mtimes = {}
        self.state.raw_selected_files = []
        self.add_to_recent_history(folder_path)

        self.status.label.config(
            text=f"Loaded folder: {os.path.basename(folder_path)}. Open Settings to customize filters.", 
            fg=THEMES[self.state.current_theme]["lbl_status_ready"]
        )
        self.refresh_filter()
        self.show_toast("Successfully loaded folder!", "success")
        
        if not self.state.toast_active:
            self.status.label.config(
                text=f"Ready • {len(self.state.active_files)} files • {len(self.state.unchecked_files)} excluded • {os.path.getsize(folder_path)/1024:.1f} KB", 
                fg=THEMES[self.state.current_theme]["lbl_status_ready"]
            )
            
        self.update_copy_mode_sizes()

    def load_files(self):
        extensions, _, _ = self.get_parsed_settings()

        if extensions:
            ext_filter = " ".join([f"*{ext}" for ext in extensions])
            file_types = [("Target Files", ext_filter), ("All files", "*.*")]
        else:
            file_types = [("All files", "*.*")]

        file_paths = list(filedialog.askopenfilenames(
            title="Select files to load",
            filetypes=file_types
        ))
        
        if not file_paths:
            self.status.label.config(text="Status: File selection canceled", fg=THEMES[self.state.current_theme]["lbl_status_error"])
            return

        self.play_sound("success")
        self.state.raw_selected_files = file_paths
        self.state.active_folder = None

        self.status.label.config(
            text=f"Loaded {len(file_paths)} file(s). Open Settings to customize filters.", 
            fg=THEMES[self.state.current_theme]["lbl_status_ready"]
        )
        self.refresh_filter()
        self.show_toast("Successfully loaded files!", "success")



    def copy_filtered_selection(self):
        self.copy_with_compression(getattr(self.toolbar, 'var_copy_mode', tk.StringVar(value="None")).get())

    def get_bundled_data_by_mode(self, mode, snapshot=None):
        """Bundles contents of all active files and applies redaction/compression filters by mode."""
        import re
        mode = re.sub(r'\s*\(~.*?\)$', '', mode).strip()
        
        active_files = snapshot["active_files"] if snapshot else self.state.active_files
        unchecked_files = snapshot["unchecked_files"] if snapshot else self.state.unchecked_files
        active_folder = snapshot["active_folder"] if snapshot else self.state.active_folder
        redact_keys_str = snapshot["redact"] if snapshot else self.settings.ent_redact.get()

        checked_files = [f for f in active_files if f not in unchecked_files]
        if not checked_files:
            return ""

        redact_keys = [k.strip() for k in redact_keys_str.split(",") if k.strip()]
        output_text = ""
        
        # Mode: Mermaid Graph
        if mode == "Mermaid Graph":
            call_graph = generate_project_mermaid_graph(checked_files)
            return f"=== PROJECT FUNCTION CALL GRAPH ===\n{call_graph}\n\n"

        # Mode: Code Structure
        if mode == "Code Structure":
            call_graph = generate_project_mermaid_graph(checked_files)
            output_text += f"=== PROJECT FUNCTION CALL GRAPH ===\n{call_graph}\n\n"
            
        # Mode: Git Diff
        if mode == "Git Diff":
            diff = get_git_diff(active_folder)
            return diff if diff and diff.strip() else "✓ No staged or unstaged changes."

        for fp in checked_files:
            if active_folder:
                rel_path = os.path.relpath(fp, active_folder)
                folder_name = os.path.basename(active_folder)
                label = os.path.join(folder_name, rel_path)
            else:
                label = os.path.basename(fp)

            try:
                sz_kb = os.path.getsize(fp) / 1024
                limit = self.config.get("large_file_threshold_kb", 200)
                if sz_kb > limit:
                    sz_str = f"{sz_kb/1024:.1f} MB" if sz_kb >= 1024 else f"{sz_kb:.1f} KB"
                    output_text += f"--- {label} ---\n⚠ {os.path.basename(fp)} skipped ({sz_str} > {limit} KB)\n\n"
                    continue
            except Exception:
                pass

            content = read_file(fp)
            
            # Apply redactions
            for secret in redact_keys:
                content = content.replace(secret, "[REDACTED]")

            # Apply Compression Modes
            if mode == "Compact Context":
                content = compress_comments_whitespace(content, fp)
            elif mode == "Code Structure":
                content = generate_skeleton(content, fp)

            output_text += f"--- {label} ---\n{content}\n\n"

        return output_text

    def copy_with_compression(self, mode):
        """Copies bundled code content to clipboard using the selected compression filter."""
        raw_text = self.get_bundled_data_by_mode("Normal")
        comp_text = self.get_bundled_data_by_mode(mode)
        
        if not comp_text or comp_text.startswith("[No git") or comp_text.startswith("[Not a Git") or comp_text.startswith("[Error running git"):
            self.status.label.config(text="Status: No active files/changes to copy", fg=THEMES[self.state.current_theme]["lbl_status_error"])
            self.play_sound("error")
            return
            
        success = copy_to_clipboard(comp_text.strip())
        
        if success:
            self.play_sound("success")
            
            # Calculate token savings
            raw_tokens = len(raw_text) // 4
            comp_tokens = len(comp_text) // 4
            saved_tokens = max(0, raw_tokens - comp_tokens)
            
            if raw_tokens > 0 and mode != "Normal":
                savings_pct = (saved_tokens / raw_tokens) * 100
                msg = f"✓ Copied! Current: {comp_tokens:,} tokens (Saved {savings_pct:.1f}% / -{saved_tokens:,} t)"
                self.show_toast(msg, "success")
                self.status.label.config(text=f"Copied using {mode}. {msg}", fg=THEMES[self.state.current_theme]["lbl_status_success"])
            else:
                msg = f"✓ Copied {len(self.state.active_files)} file(s) to clipboard! ({comp_tokens:,} tokens | {len(comp_text)/1024:.1f} KB)"
                self.show_toast(f"Copied! ({comp_tokens:,} tokens)", "success")
                self.status.label.config(text=msg, fg=THEMES[self.state.current_theme]["lbl_status_success"])
        else:
            self.play_sound("error")
            self.show_toast("Error: Could not copy to clipboard", "error")
            self.status.label.config(text="✗ Failed to copy contents to clipboard", fg=THEMES[self.state.current_theme]["lbl_status_error"])
            
    def export_bundle_to_file(self, file_type):
        from tkinter import filedialog
        
        mode = self.toolbar.var_copy_mode.get() if hasattr(self, 'toolbar') else self.ui.var_copy_mode.get()
        comp_text = self.get_bundled_data_by_mode(mode)
        
        if not comp_text or comp_text.startswith("[No git"):
            self.status.label.config(text="Status: No active files/changes to export", fg=THEMES[self.state.current_theme]["lbl_status_error"])
            self.play_sound("error")
            return
            
        ext = ".md" if file_type == "markdown" else ".txt"
        filetypes = [("Markdown files", "*.md"), ("All files", "*.*")] if file_type == "markdown" else [("Text files", "*.txt"), ("All files", "*.*")]
        
        filepath = filedialog.asksaveasfilename(
            title="Export Bundle",
            defaultextension=ext,
            filetypes=filetypes,
            initialfile=f"context_bundle{ext}"
        )
        
        if not filepath:
            return
            
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(comp_text)
            
            # Calculate tokens
            comp_tokens = len(comp_text) // 4
            
            self.play_sound("success")
            msg = f"✓ Exported {len(self.state.active_files)} file(s)! ({comp_tokens:,} tokens | {len(comp_text)/1024:.1f} KB)"
            self.show_toast(f"Exported to {os.path.basename(filepath)}", "success")
            self.status.label.config(text=msg, fg=THEMES[self.state.current_theme]["lbl_status_success"])
        except Exception as e:
            self.play_sound("error")
            self.show_toast(f"Error exporting: {e}", "error")
            self.status.label.config(text="✗ Failed to export file", fg=THEMES[self.state.current_theme]["lbl_status_error"])

    def reset_defaults(self):
        self.play_sound("click")
        self.settings.ent_extensions.delete(0, tk.END)
        self.settings.ent_extensions.insert(0, DEFAULT_CONFIG["allowed_extensions"])
        
        self.settings.ent_ignored_folders.delete(0, tk.END)
        self.settings.ent_ignored_folders.insert(0, DEFAULT_CONFIG["ignored_folders"])
        
        self.settings.ent_ignored_files.delete(0, tk.END)
        self.settings.ent_ignored_files.insert(0, DEFAULT_CONFIG["ignored_files"])

        self.settings.ent_redact.delete(0, tk.END)
        self.settings.ent_redact.insert(0, DEFAULT_CONFIG["redact_keywords"])

        self.settings.var_use_regex.set(DEFAULT_CONFIG["use_regex"])
        self.settings.var_parse_gitignore.set(DEFAULT_CONFIG["parse_gitignore"])
        if hasattr(self.settings, "var_watch_live"):
            self.settings.var_watch_live.set(True)
        self.settings.var_sound.set(DEFAULT_CONFIG["sound_enabled"])

        self.config.update(DEFAULT_CONFIG.copy())
        self.config["watch_live_updates"] = True
        self.config["theme"] = self.state.current_theme
        save_config(self.config)

        self.status.label.config(text="Status: Settings reset to defaults", fg=THEMES[self.state.current_theme]["lbl_status_ready"])
        self.refresh_filter()
        self.show_toast("Reset config successfully!", "success")

    def update_status_color(self):
        t = THEMES[self.state.current_theme]
        if "✓" in self.status.label.cget("text"):
            self.status.label.config(fg=t["lbl_status_success"])
        elif "✗" in self.status.label.cget("text") or "Error" in self.status.label.cget("text") or "canceled" in self.status.label.cget("text"):
            self.status.label.config(fg=t["lbl_status_error"])
        else:
            self.status.label.config(fg=t["lbl_status_ready"])
