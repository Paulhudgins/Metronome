"""Dialog windows for the metronome application."""

import tkinter as tk
from tkinter import ttk, messagebox
from config import PADDING, BUTTON_PADDING, MIN_BPM, MAX_BPM
from setlist import PartialSetlistError


class SectionDialog:
    """Dialog for creating/editing song sections."""

    def __init__(self, parent, section=None, is_new=False):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Section" if is_new else "Edit Section")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Name:").pack(pady=PADDING)
        self.name_entry = ttk.Entry(self.dialog)
        self.name_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Bars:").pack(pady=PADDING)
        self.bars_entry = ttk.Entry(self.dialog)
        self.bars_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text=f"BPM ({MIN_BPM}–{MAX_BPM}):").pack(pady=PADDING)
        self.bpm_entry = ttk.Entry(self.dialog)
        self.bpm_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Beats per Bar:").pack(pady=PADDING)
        self.beats_entry = ttk.Entry(self.dialog)
        self.beats_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Subdivisions:").pack(pady=PADDING)
        self.subdiv_entry = ttk.Entry(self.dialog)
        self.subdiv_entry.pack(fill=tk.X, padx=PADDING)

        ttk.Label(self.dialog, text="Repeat (times):").pack(pady=PADDING)
        self.repeat_entry = ttk.Entry(self.dialog)
        self.repeat_entry.pack(fill=tk.X, padx=PADDING)

        self.swing_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.dialog,
            text="Enable Swing",
            variable=self.swing_var
        ).pack(pady=PADDING)

        self.count_in_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.dialog,
            text="Count-in before this section",
            variable=self.count_in_var
        ).pack(pady=PADDING)

        if section:
            if not is_new:
                self.name_entry.insert(0, section.name)
            self.bars_entry.insert(0, str(section.bars))
            self.bpm_entry.insert(0, str(section.bpm))
            self.beats_entry.insert(0, str(section.beats_per_bar))
            self.subdiv_entry.insert(0, str(section.subdivisions))
            self.repeat_entry.insert(0, str(section.repeat))
            self.swing_var.set(section.swing_enabled)
            self.count_in_var.set(getattr(section, 'count_in', False))
        else:
            self.repeat_entry.insert(0, "1")

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
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Section name cannot be empty",
                                 parent=self.dialog)
            return
        try:
            bars = int(self.bars_entry.get())
            bpm = int(self.bpm_entry.get())
            beats_per_bar = int(self.beats_entry.get())
            subdivisions = int(self.subdiv_entry.get())
            repeat = int(self.repeat_entry.get())
        except ValueError:
            messagebox.showerror(
                "Error",
                "Bars, BPM, Beats per Bar, Subdivisions and Repeat must all be whole numbers.",
                parent=self.dialog
            )
            return

        if bars <= 0:
            messagebox.showerror("Error", "Bars must be a positive number.",
                                 parent=self.dialog)
            return
        if not (MIN_BPM <= bpm <= MAX_BPM):
            messagebox.showerror("Error", f"BPM must be between {MIN_BPM} and {MAX_BPM}.",
                                 parent=self.dialog)
            return
        if beats_per_bar <= 0:
            messagebox.showerror("Error", "Beats per bar must be a positive number.",
                                 parent=self.dialog)
            return
        if subdivisions <= 0:
            messagebox.showerror("Error", "Subdivisions must be a positive number.",
                                 parent=self.dialog)
            return
        if repeat < 1:
            messagebox.showerror("Error", "Repeat must be at least 1.",
                                 parent=self.dialog)
            return

        self.result = {
            'name': name,
            'bars': bars,
            'bpm': bpm,
            'beats_per_bar': beats_per_bar,
            'subdivisions': subdivisions,
            'swing_enabled': self.swing_var.get(),
            'repeat': repeat,
            'count_in': self.count_in_var.get(),
        }
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()


class LoadSongDialog:
    """Dialog for loading or deleting a song."""

    def __init__(self, parent, song_manager):
        self.result = None
        self.song_manager = song_manager

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Load Song")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        ttk.Label(self.dialog, text="Select a song to load:").pack(pady=PADDING)

        self.song_list = tk.Listbox(self.dialog, selectmode=tk.SINGLE, height=10)
        self.song_list.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=PADDING)
        self._refresh_list()

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="Load", command=self._on_load).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Delete", command=self._on_delete).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self.dialog.minsize(320, 0)
        self._center(parent)
        parent.wait_window(self.dialog)

    def _refresh_list(self):
        self.song_list.delete(0, tk.END)
        for filename in self.song_manager.get_song_files():
            self.song_list.insert(tk.END, filename[:-5])

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_load(self):
        selection = self.song_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a song to load",
                                   parent=self.dialog)
            return
        try:
            filename = self.song_list.get(selection[0])
            self.result = self.song_manager.load_song(filename)
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)

    def _on_delete(self):
        selection = self.song_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a song to delete",
                                   parent=self.dialog)
            return
        name = self.song_list.get(selection[0])
        if messagebox.askyesno("Confirm", f"Delete '{name}'? This cannot be undone.",
                               parent=self.dialog):
            try:
                self.song_manager.delete_song(name)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)

    def _on_cancel(self):
        self.dialog.destroy()


class DelayDialog:
    """Dialog for setting delay between songs."""

    def __init__(self, parent, initial_delay=0.0):
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
            value = float(self.delay_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter a number of seconds (e.g. 2 or 1.5).",
                                 parent=self.dialog)
            return
        if value < 0:
            messagebox.showerror("Error", "Delay cannot be negative.", parent=self.dialog)
            return
        self.result = value
        self.dialog.destroy()

    def _on_cancel(self):
        self.dialog.destroy()


class LoadSetlistDialog:
    """Dialog for loading or deleting a setlist."""

    def __init__(self, parent, setlist_manager, song_manager):
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
        self._refresh_list()

        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=PADDING, pady=PADDING)

        ttk.Button(button_frame, text="Load", command=self._on_load).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Delete", command=self._on_delete).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=tk.LEFT, padx=BUTTON_PADDING
        )

        self._center(parent)
        parent.wait_window(self.dialog)

    def _refresh_list(self):
        self.setlist_list.delete(0, tk.END)
        for name in self.setlist_manager.get_setlist_files():
            self.setlist_list.insert(tk.END, name)

    def _center(self, parent):
        self.dialog.update_idletasks()
        w, h = self.dialog.winfo_width(), self.dialog.winfo_height()
        x = (parent.winfo_screenwidth() // 2) - (w // 2)
        y = (parent.winfo_screenheight() // 2) - (h // 2)
        self.dialog.geometry(f'{w}x{h}+{x}+{y}')

    def _on_load(self):
        selection = self.setlist_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a setlist to load",
                                   parent=self.dialog)
            return
        try:
            name = self.setlist_list.get(selection[0])
            self.result = self.setlist_manager.load_setlist(name, self.song_manager)
            self.dialog.destroy()
        except PartialSetlistError as e:
            self.result = e.setlist
            missing_list = ', '.join(f"'{m}'" for m in e.missing)
            messagebox.showwarning(
                "Missing Songs",
                f"The following songs could not be found and were skipped:\n{missing_list}",
                parent=self.dialog
            )
            self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.dialog)

    def _on_delete(self):
        selection = self.setlist_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a setlist to delete",
                                   parent=self.dialog)
            return
        name = self.setlist_list.get(selection[0])
        if messagebox.askyesno("Confirm", f"Delete '{name}'? This cannot be undone.",
                               parent=self.dialog):
            try:
                self.setlist_manager.delete_setlist(name)
                self._refresh_list()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.dialog)

    def _on_cancel(self):
        self.dialog.destroy()
