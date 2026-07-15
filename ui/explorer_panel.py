import tkinter as tk
from tkinter import ttk
from ui.common import AutoScrollbar

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

class ExplorerPanel(tk.Frame):
    def __init__(self, app, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.build()

    def build(self):
        self.title_label = tk.Label(self, text="📁 Files", font=("Segoe UI", 9, "bold"), anchor="w", padx=5)
        self.title_label.pack(fill=tk.X, pady=(5, 2))

        self.search_wrapper = tk.Frame(self, pady=0, padx=5)
        self.search_wrapper.pack(fill=tk.X, pady=(0, 5))
        
        self.search_frame = tk.Frame(self.search_wrapper, bd=0, highlightthickness=1)
        self.search_frame.pack(fill=tk.X)

        self.search_icon = tk.Label(self.search_frame, text=" 🔍 ", font=("Segoe UI", 9))
        self.search_icon.pack(side=tk.LEFT)
        
        self.search_entry = tk.Entry(self.search_frame, bd=0, font=("Segoe UI", 9), relief="flat")
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2, pady=1, padx=2)
        
        self.search_entry.insert(0, "Search files...")
        
        def on_search_focus_in(event):
            if self.search_entry.get() == "Search files...":
                self.search_entry.delete(0, tk.END)
                
        def on_search_focus_out(event):
            if not self.search_entry.get():
                self.search_entry.insert(0, "Search files...")
                
        self.search_entry.bind("<FocusIn>", on_search_focus_in)
        self.search_entry.bind("<FocusOut>", on_search_focus_out)
        self.search_entry.bind("<KeyRelease>", self.app.on_search_changed)

        self.tree_scroll_container = tk.Frame(self)
        self.tree_scroll_container.pack(fill=tk.BOTH, expand=True)

        self.scrollbar_tree = AutoScrollbar(self.tree_scroll_container, orient=tk.VERTICAL, style="Dark.Vertical.TScrollbar")
        self.scrollbar_tree.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = tk.Text(
            self.tree_scroll_container, wrap="none", font=("Consolas", 9), bd=0, padx=5, pady=5,
            yscrollcommand=self.scrollbar_tree.set
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_tree.config(command=self.tree.yview)

        self.tree.bind("<ButtonRelease-1>", self.app.on_tree_single_click)
        self.tree.bind("<Motion>", self.app.on_tree_mouse_hover)
        self.tree.bind("<Leave>", self.app.hide_tree_tooltip)
        
        if TkinterDnD:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind('<<Drop>>', self.app.on_drop)
