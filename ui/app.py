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


class FileCopierApp:
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
        
        # Real-time modification watch variables
        self.cache.preview_file_mtime = None
        self.cache.active_files_mtimes = {}
        self.cache.active_folder_mtime = None
        self.cache.stats_cache = {}

        self.create_widgets()
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

    def apply_theme_title_bar(self):
        self.root.update()
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()
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
        self.settings.cbo_recent.configure(style="TCombobox")

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
            (self.toolbar.copy_mode_dropdown if hasattr(self, 'toolbar') else self.ui.cbo_copy_mode, t["copy_btn"], t["copy_btn_hover"], "#11111b" if self.state.current_theme == "dark" else t["bg"]),
            (self.ui.btn_theme, t["bg"], t["entry_bg"], t["text_primary"]),
            (self.ui.btn_settings, t["bg"], t["entry_bg"], t["text_primary"]),
            (self.settings.btn_reset, t["card_bg"], t["entry_bg"], t["lbl_status_error"]),
            (self.settings.btn_advanced_close, t["card_bg"], t["entry_bg"], t["lbl_status_error"]),
        ]
        
        if hasattr(self, 'toolbar'):
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
            self.sidebar.search_entry.configure(bg=t["entry_bg"], fg=t["text_primary"], insertbackground=t["text_primary"], highlightthickness=0)
            self.sidebar.tree.configure(bg=t["console_bg"], fg=t["text_primary"])
            self.sidebar.tree.tag_configure("code", foreground=t["tag_code"])
            self.sidebar.tree.tag_configure("doc", foreground=t["tag_doc"])
            self.sidebar.tree.tag_configure("config", foreground=t["tag_config"])

        if hasattr(self, 'preview'):
            self.preview.configure(bg=t['bg'], highlightbackground=t['entry_border'])
            self.preview.title_label.configure(bg=t["bg"], fg=t["text_primary"])
            self.preview.meta_wrapper.configure(bg=t["bg"])
            self.preview.meta_frame.configure(bg=t["entry_bg"], highlightbackground=t["entry_border"])
            self.preview.meta_label.configure(bg=t["entry_bg"], fg=t["text_secondary"], readonlybackground=t["entry_bg"])
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
        """Animates a success/error toast banner from the bottom."""
        t = THEMES[self.state.current_theme]
        bg_col = t["lbl_status_success"] if state == "success" else t["lbl_status_error"]
        fg_col = "#11111b" if self.state.current_theme == "dark" else t["bg"]

        # Configure toast
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

        slide_up(5)

        # Auto dismissal
        self.root.after(2500, self.hide_toast)

    def hide_toast(self):
        """Slides the toast banner back down."""
        def slide_down(curr_height):
            if curr_height > 0:
                self.ui.frm_toast_banner.place(rely=1.0 - (curr_height / self.root.winfo_height()))
                self.root.after(10, lambda: slide_down(curr_height - 5))
            else:
                self.ui.frm_toast_banner.place_forget()

        if self.ui.frm_toast_banner.winfo_exists():
            slide_down(45)

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

    def show_share_menu(self):
        """Shows the dropdown sharing options menu right below the LAN share button."""
        self.play_sound("click")
        if self.state.share_server:
            self.toggle_lan_share()
        else:
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
            copy_to_clipboard(url, self.root)
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
                        self.load_active_file_preview()
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
    def truncate_path(self, path, max_len=45):
        """Truncates long paths for UI display."""
        if len(path) <= max_len:
            return path
        parts = path.split(os.sep)
        if len(parts) > 2:
            return f"{parts[0]}{os.sep}...{os.sep}{parts[-2]}{os.sep}{parts[-1]}"
        return path[:max_len-3] + "..."

    def update_recent_history_ui(self):
        history = self.config.get("recent_folders", [])
        self.state.recent_mapping = {self.truncate_path(p): p for p in history}
        self.settings.cbo_recent["values"] = list(self.state.recent_mapping.keys())
        
        if hasattr(self.state, 'active_folder') and self.state.active_folder and self.state.active_folder in history:
            self.settings.cbo_recent.set(self.truncate_path(self.state.active_folder))
        elif history:
            self.settings.cbo_recent.set("History list...")

    def on_recent_selected(self, event=None):
        selected_display = self.settings.cbo_recent.get()
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
        presets = {
            "Python Project": {
                "allowed": ".py, .md, .kt, txt",
                "folders": ".venv, venv, __pycache__, .git, README, node_modules, stress_tests, pytest_cache, utilities, memory, experiments",
                "files": ".env, .gitignore, stress_test.py"
            },
            "NodeJS / React": {
                "allowed": ".js, .jsx, .ts, .tsx, .json, .md, .css",
                "folders": "node_modules, build, dist, .git, .env, .next, .cache",
                "files": ".env, .env.local, .gitignore, package-lock.json"
            },
            "Android Project": {
                "allowed": ".kt, .java, .xml, .properties, .gradle",
                "folders": ".gradle, build, .idea, captures, .git",
                "files": "local.properties, .gitignore"
            },
            "Markdown Docs": {
                "allowed": ".md, .txt, .rst",
                "folders": ".git, node_modules, build",
                "files": ".gitignore"
            }
        }
        
        current_allowed = self.settings.ent_extensions.get().strip()
        current_folders = self.settings.ent_ignored_folders.get().strip()
        current_files = self.settings.ent_ignored_files.get().strip()

        matched_preset = "Custom"
        for name, data in presets.items():
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
            
        presets = {
            "Python Project": {
                "allowed": ".py, .md, .kt, txt",
                "folders": ".venv, venv, __pycache__, .git, README, node_modules, stress_tests, pytest_cache, utilities, memory, experiments",
                "files": ".env, .gitignore, stress_test.py"
            },
            "NodeJS / React": {
                "allowed": ".js, .jsx, .ts, .tsx, .json, .md, .css",
                "folders": "node_modules, build, dist, .git, .env, .next, .cache",
                "files": ".env, .env.local, .gitignore, package-lock.json"
            },
            "Android Project": {
                "allowed": ".kt, .java, .xml, .properties, .gradle",
                "folders": ".gradle, build, .idea, captures, .git",
                "files": "local.properties, .gitignore"
            },
            "Markdown Docs": {
                "allowed": ".md, .txt, .rst",
                "folders": ".git, node_modules, build",
                "files": ".gitignore"
            }
        }

        if preset in presets:
            data = presets[preset]
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
                            
                    tree_lines[line_num - 1] = f"{indent}{marker}{checkbox}{key}"
                    self.cache.tree_line_mapping[line_num] = ("folder", sub_files)
                else:
                    line_num = len(tree_lines) + 1
                    checkbox = "☐ " if value in self.state.unchecked_files else "☑ "
                    tree_lines.append(f"{indent}{marker}{checkbox}{key}")
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

        # Iterate lines and assign tag colors
        for line_idx in range(1, len(tree_lines) + 1):
            line_txt = self.sidebar.tree.get(f"{line_idx}.0", f"{line_idx}.end")
            ext = os.path.splitext(line_txt)[1].lower()
            
            if ext in [".py", ".kt", ".java", ".js", ".jsx", ".ts", ".tsx"]:
                self.sidebar.tree.tag_add("code", f"{line_idx}.0", f"{line_idx}.end")
            elif ext in [".md", ".txt", ".rst"]:
                self.sidebar.tree.tag_add("doc", f"{line_idx}.0", f"{line_idx}.end")
            elif ext in [".json", ".xml", ".properties", ".gradle", ".env", ".gitignore"]:
                self.sidebar.tree.tag_add("config", f"{line_idx}.0", f"{line_idx}.end")
                
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

    def set_code_view_content(self, text):
        self.preview.code_view.config(state="normal")
        self.preview.code_view.delete("1.0", tk.END)
        self.preview.code_view.insert(tk.END, text)
        self.preview.code_view.config(state="disabled")

    # --- SPLIT SCREEN EXPLORER CLICK & INTERACTION ---
    def load_active_file_preview(self):
        """Loads, redacts, and displays the content of the currently selected file."""
        if not self.state.selected_preview_file or not os.path.exists(self.state.selected_preview_file):
            if hasattr(self, 'preview'):
                self.preview.meta_label.config(state="normal")
                self.preview.meta_label.delete(0, tk.END)
                self.preview.meta_label.insert(0, " Select a file...")
                self.preview.meta_label.config(state="readonly")
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
            meta_text = f"File: {file_name}   |   Size: {size_kb:.2f} KB   |   Lines: {lines}   |   Lang: {lang}"
            self.preview.meta_label.config(state="normal")
            self.preview.meta_label.delete(0, tk.END)
            self.preview.meta_label.insert(0, meta_text)
            self.preview.meta_label.config(state="readonly")

        # Apply keyword redactions to preview window
        redact_keys = [k.strip() for k in self.settings.ent_redact.get().split(",") if k.strip()]
        for secret in redact_keys:
            content = content.replace(secret, "[REDACTED]")
            
        _, ext = os.path.splitext(self.state.selected_preview_file)
        if ext.lower() == ".md":
            self.render_rich_markdown(content)
        else:
            self.set_code_view_content(content)

    def get_file_git_diff(self, filepath):
        """Gets Git diff changes specifically for a single file."""
        if not self.state.active_folder or not os.path.exists(filepath):
            return "[No git repository loaded]"
        try:
            rel_path = os.path.relpath(filepath, self.state.active_folder)
            res = subprocess.run(
                ["git", "diff", rel_path],
                cwd=self.state.active_folder, capture_output=True, text=True, check=True
            )
            res_cached = subprocess.run(
                ["git", "diff", "--cached", rel_path],
                cwd=self.state.active_folder, capture_output=True, text=True, check=True
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

    def render_rich_markdown(self, markdown_text):
        """Parses markdown block elements (headers, quotes, bullets, code blocks) and renders in code preview."""
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

    def on_tree_single_click(self, event):
        """Toggles checkbox on click, and displays text content on the Right Explorer panel."""
        try:
            self.sidebar.tree.tag_remove(tk.SEL, "1.0", tk.END)
            index = self.sidebar.tree.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            if not hasattr(self.cache, 'tree_line_mapping') or line_num not in self.cache.tree_line_mapping:
                return "break"
                
            node_type, data = self.cache.tree_line_mapping[line_num]
            
            if node_type == "file":
                target_path = data
                if target_path in self.state.unchecked_files:
                    self.state.unchecked_files.remove(target_path)
                else:
                    self.state.unchecked_files.add(target_path)
                    
                self.render_tree_view()
                self.calculate_stats()
                self.refresh_pills()

                self.play_sound("click")
                self.state.selected_preview_file = target_path
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
        if self.ui.win_tooltip:
            self.ui.win_tooltip.destroy()
            self.ui.win_tooltip = None

    def on_tree_mouse_hover(self, event):
        """Creates dynamic popup tooltips with file metadata on mouseover."""
        try:
            index = self.sidebar.tree.index(f"@{event.x},{event.y}")
            line_num = int(index.split('.')[0])
            
            if not hasattr(self.cache, 'tree_line_mapping') or line_num not in self.cache.tree_line_mapping:
                if self.ui.win_tooltip:
                    self.ui.win_tooltip.destroy()
                    self.ui.win_tooltip = None
                return
                
            node_type, data = self.cache.tree_line_mapping[line_num]
            
            size = 0
            if node_type == "file":
                if os.path.exists(data):
                    size = os.path.getsize(data) / 1024
                clean_name = os.path.basename(data)
            else:
                for fp in data:
                    if os.path.exists(fp):
                        size += os.path.getsize(fp) / 1024
                line_content = self.sidebar.tree.get(f"{line_num}.0", f"{line_num}.end")
                clean_name = line_content.replace("└── ", "").replace("├── ", "").replace("│   ", "").replace("☑ ", "").replace("☐ ", "").replace("[-] ", "").strip()
                clean_name = f"{clean_name} (Folder)"

            if self.ui.win_tooltip:
                self.ui.win_tooltip.destroy()

            self.ui.win_tooltip = tk.Toplevel(self.root)
            self.ui.win_tooltip.wm_overrideredirect(True)
            
            x = self.root.winfo_pointerx() + 15
            y = self.root.winfo_pointery() + 10
            self.ui.win_tooltip.wm_geometry(f"+{x}+{y}")
            
            t = THEMES[self.state.current_theme]
            lbl = tk.Label(self.ui.win_tooltip, text=f"File: {clean_name}\nSize: {size:.2f} KB", bg=t["entry_bg"], fg=t["text_primary"],
                           highlightbackground=t["entry_border"], highlightthickness=1, font=("Segoe UI", 8), padx=5, pady=3)
            lbl.pack()
        except Exception:
            if self.ui.win_tooltip:
                self.ui.win_tooltip.destroy()
                self.ui.win_tooltip = None

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
                        self.status.label.config(
                            text=f"⚠️ Warning: File '{os.path.basename(fp)}' is very large ({kb_val:.1f} KB)",
                            fg=THEMES[self.state.current_theme]["lbl_status_error"]
                        )
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
            text=f"{total_files} file(s) loaded ({ext_summary}) | Size: {kb_size:.1f} KB | Est. Tokens: {tokens_raw:,} (Stripped: {tokens_mode1:,} | Skeleton: {tokens_mode2:,})"
        )

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

    def get_bundled_data_by_mode(self, mode):
        """Bundles contents of all active files and applies redaction/compression filters by mode."""
        checked_files = [f for f in self.state.active_files if f not in self.state.unchecked_files]
        if not checked_files:
            return ""

        redact_keys = [k.strip() for k in self.settings.ent_redact.get().split(",") if k.strip()]
        output_text = ""
        
        # Mode: Mermaid Graph
        if mode == "Mermaid Graph":
            call_graph = generate_project_mermaid_graph(checked_files)
            return f"=== PROJECT FUNCTION CALL GRAPH ===\n{call_graph}\n\n"

        # Mode: Skeleton
        if mode == "Skeleton":
            call_graph = generate_project_mermaid_graph(checked_files)
            output_text += f"=== PROJECT FUNCTION CALL GRAPH ===\n{call_graph}\n\n"
            
        # Mode: Git Diff
        if mode == "Git Diff":
            diff = get_git_diff(self.state.active_folder)
            return diff if diff else "[No git changes found in repository]"

        for fp in checked_files:
            if self.state.active_folder:
                rel_path = os.path.relpath(fp, self.state.active_folder)
                folder_name = os.path.basename(self.state.active_folder)
                label = os.path.join(folder_name, rel_path)
            else:
                label = os.path.basename(fp)

            content = read_file(fp)
            
            # Apply redactions
            for secret in redact_keys:
                content = content.replace(secret, "[REDACTED]")

            # Apply Compression Modes
            if mode == "Strip Comments":
                content = compress_comments_whitespace(content, fp)
            elif mode == "Skeleton":
                content = generate_skeleton(content, fp)

            output_text += f"--- {label} ---\n{content}\n\n"

        return output_text

    def copy_with_compression(self, mode):
        """Copies bundled code content to clipboard using the selected compression filter."""
        raw_text = self.get_bundled_data_by_mode("Normal")
        comp_text = self.get_bundled_data_by_mode(mode)
        
        if not comp_text or comp_text.startswith("[No git"):
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
            self.status.label.config(text="✗ Failed to copy contents to clipboard", fg=THEMES[self.state.current_theme]["lbl_status_error"])

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
        self.ui.var_git_diff_only.set(DEFAULT_CONFIG["git_diff_only"])
        self.settings.var_sound.set(DEFAULT_CONFIG["sound_enabled"])

        self.config.update(DEFAULT_CONFIG.copy())
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
