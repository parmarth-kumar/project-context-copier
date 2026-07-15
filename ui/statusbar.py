import tkinter as tk
from tkinter import ttk

class StatusBar(tk.Frame):
    def __init__(self, app, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.build()

    def build(self):
        self.stats_label = tk.Label(self, text="0 files loaded | 0.0 KB size | Estimated Tokens: 0",
                                  bg="#1e1e2e", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        self.stats_label.pack(side=tk.LEFT)
        
        self.label = tk.Label(self, text="Status: Ready", bg="#1e1e2e", fg="#a6adc8", 
                                   font=("Segoe UI", 9, "bold"))
        self.label.pack(side=tk.RIGHT)
