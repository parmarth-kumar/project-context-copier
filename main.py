import os
import sys
import tkinter as tk
from ui.app import ProjectContextCopierApp

try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None

def main():
    # --- Fix Taskbar Icon on Windows ---
    if sys.platform == 'win32':
        import ctypes
        try:
            # Tell Windows this is an independent app, not just 'python.exe'
            # Use v3 to bypass Windows taskbar icon cache from the previous run
            myappid = 'mycompany.projectcontextcopier.v3'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Could not set AppUserModelID: {e}")

    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
        
    # Prevent flashing of small default window on launch
    root.withdraw()
        
    def resource_path(relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    try:
        icon_ico = resource_path(os.path.join("assets", "icon.ico"))
        
        if os.path.exists(icon_ico):
            root.iconbitmap(icon_ico)
        else:
            print(f"Warning: Icon not found at {icon_ico}")
            
    except Exception as e:
        print(f"Warning: Could not set application icon: {e}")
        
    ProjectContextCopierApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
