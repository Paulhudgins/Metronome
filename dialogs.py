"""Dialog windows for the metronome application."""

import tkinter as tk
from tkinter import ttk, messagebox
from config import PADDING, BUTTON_PADDING


class SectionDialog:
    """Dialog for creating/editing song sections."""

    def __init__(self, parent, section=None):
        """Initialize the dialog.

        Args:
            parent (tk.Tk): Parent window
            section (SongSection, optional): Section to edit
        """
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Song Section")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Name:").pack(pady=PADDING)
        self.name_entry = ttk.Entry(self.dialog)
        self.name_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Bars:").pack(pady=PADDING)
        self.bars_entry = ttk.Entry(self.dialog)
        self.bars_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="BPM:").pack(pady=PADDING)
        self.bpm_entry = ttk.Entry(self.dialog)
        self.bpm_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Beats per Bar:").pack(pady=PADDING)
        self.beats_entry = ttk.Entry(self.dialog)
        self.beats_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Subdivisions:").pack(pady=PADDING)
        self.subdiv_entry = ttk.Entry(self.dialog)
        self.subdiv_entry.pack(fill=tk.X, padx=PADDING)

        self.swing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.dialog,
            text="Enable Swing",
            variable=self.swing_var
        ).pack(pady=PADDING)

        if section:
            self.name_entry.insert(0, section.name)
            self.bars_entry.insert(0, str(section.bars))
            self.bpm_entry.insert(0, str(section.bpm))
            self.beats_entry.insert(0, str(section.beats_per_bar))
            self.subdiv_entry.insert(0, str(section.subdivisions))
            self.swing_var.set(section.swing_enabled)

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self._center(parent)
        parent.wait_window(self.dialog)

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_ok(self):
        try:
            self.result = {
                'name': self.name_entry.get(),
                'bars': int(self.bars_entry.get()),
                'bpm': int(self.bpm_entry.get()),
                'beats_per_bar': int(self.beats_entry.get()),
                'subdivisions': int(self.subdiv_entry.get()),
                'swing_enabled': self.swing_var.get()
            }
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _on_cancel(self):
        self.dialog.destroy()


class LoadSongDialog:
    """Dialog for loading a song."""

    def __init__(self, parent, song_manager):
        """Initialize the dialog.

        Args:
            parent (tk.Tk): Parent window
            song_manager (SongManager): Song manager instance
        """
        self.result = None
        self.song_manager = song_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Load Song")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Select a song to load:").pack(pady=PADDING)

        self.song_list = tk.Listbox(self.dialog, selectmode=tk.SINGLE, height=10)
        self.song_list.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=PADDING)

        for filename in self.song_manager.get_song_files():
            self.song_list.insert(tk.END, filename[:-5])

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="Load", command=self._on_load).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self._center(parent)
        parent.wait_window(self.dialog)

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_load(self):
        selection = self.song_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a song to load")
            return
        try:
            filename = self.song_list.get(selection[0])
            self.result = self.song_manager.load_song(filename)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_cancel(self):
        self.dialog.destroy()


class DelayDialog:
    """Dialog for setting delay between songs."""

    def __init__(self, parent, initial_delay=0.0):
        """Initialize the dialog.

        Args:
            parent (tk.Tk): Parent window
            initial_delay (float): Initial delay value
        """
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Delay")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Delay after song (seconds):").pack(pady=PADDING)

        self.delay_entry = ttk.Entry(self.dialog)
        self.delay_entry.insert(0, str(initial_delay))
        self.delay_entry.pack(fill=tk.X, padx=PADDING)

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self._center(parent)
        parent.wait_window(self.dialog)

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_ok(self):
        try:
            self.result = float(self.delay_entry.get())
            if self.result < 0:
                raise ValueError("Delay cannot be negative")
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _on_cancel(self):
        self.dialog.destroy()


class LoadSetlistDialog:
    """Dialog for loading a setlist."""

    def __init__(self, parent, setlist_manager, song_manager):
        """Initialize the dialog.

        Args:
            parent (tk.Tk): Parent window
            setlist_manager (SetlistManager): Setlist manager instance
            song_manager (SongManager): Song manager instance
        """
        self.result = None
        self.setlist_manager = setlist_manager
        self.song_manager = song_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Load Setlist")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Select a setlist to load:").pack(pady=PADDING)

        self.setlist_list = tk.Listbox(self.dialog, selectmode=tk.SINGLE, height=10)
        self.setlist_list.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=PADDING)

        for name in self.setlist_manager.get_setlist_files():
            self.setlist_list.insert(tk.END, name)

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="Load", command=self._on_load).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self._center(parent)
        parent.wait_window(self.dialog)

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_load(self):
        selection = self.setlist_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a setlist to load")
            return
        try:
            name = self.setlist_list.get(selection[0])
            self.result = self.setlist_manager.load_setlist(name, self.song_manager)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_cancel(self):
        self.dialog.destroy()
