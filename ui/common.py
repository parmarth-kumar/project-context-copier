import tkinter as tk
from tkinter import ttk

class AutoScrollbar(ttk.Scrollbar):
    """A custom scrollbar that automatically hides itself when the content fits perfectly."""
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.pack_forget()
        else:
            self.pack(side=tk.RIGHT, fill=tk.Y)
        super().set(lo, hi)

def create_action_button(parent, text, command):
    btn = tk.Button(parent, text=text, command=command, bd=0, relief="flat",
                    font=("Segoe UI", 9, "bold"), cursor="hand2", pady=8)
    return btn
