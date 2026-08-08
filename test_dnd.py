import tkinter as tk
import ttkbootstrap as ttk
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    has_dnd = True
except ImportError:
    has_dnd = False

if has_dnd:
    print("tkinterdnd2 installed")
else:
    print("tkinterdnd2 not installed")
