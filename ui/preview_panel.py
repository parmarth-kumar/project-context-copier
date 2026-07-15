import tkinter as tk
from tkinter import ttk
from ui.common import AutoScrollbar

class PreviewPanel(tk.Frame):
    def __init__(self, app, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.build()

    def build(self):
        self.title_label = tk.Label(self, text="📄 Live Code Content Preview", font=("Segoe UI", 9, "bold"), anchor="w", padx=5)
        self.title_label.pack(fill=tk.X, pady=(5, 3))

        self.meta_wrapper = tk.Frame(self, pady=0, padx=5)
        self.meta_wrapper.pack(fill=tk.X, pady=(0, 5))
        
        self.meta_frame = tk.Frame(self.meta_wrapper, bd=0, highlightthickness=1)
        self.meta_frame.pack(fill=tk.X)

        self.meta_label = tk.Entry(self.meta_frame, bd=0, font=("Segoe UI", 9), relief="flat")
        self.meta_label.pack(fill=tk.X, expand=True, ipady=2, pady=1, padx=2)
        self.meta_label.insert(0, " Select a file...")
        self.meta_label.config(state="readonly")

        self.content_scroll_container = tk.Frame(self)
        self.content_scroll_container.pack(fill=tk.BOTH, expand=True)

        self.scrollbar_content = AutoScrollbar(self.content_scroll_container, orient=tk.VERTICAL, style="Dark.Vertical.TScrollbar")
        self.scrollbar_content.pack(side=tk.RIGHT, fill=tk.Y)

        self.code_view = tk.Text(
            self.content_scroll_container, wrap="word", font=("Consolas", 9), bd=0, padx=8, pady=5,
            yscrollcommand=self.scrollbar_content.set
        )
        self.code_view.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_content.config(command=self.code_view.yview)
