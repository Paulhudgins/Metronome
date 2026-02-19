"""User interface for the metronome application."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import time
from config import (
    DEFAULT_BPM,
    DEFAULT_BEATS_PER_BAR,
    DEFAULT_SUBDIVISIONS,
    DEFAULT_TIMER_DURATION,
    DEFAULT_TEMPO_CHANGE_STEP,
    DEFAULT_TEMPO_CHANGE_INTERVAL,
    DEFAULT_COUNT_IN_BARS,
    MIN_BPM,
    MAX_BPM,
    PADDING,
    BUTTON_PADDING,
    FRAME_PADDING,
    WINDOW_PADDING,
    SAMPLES_FOLDER
)
from song_section import SongSection
from song import Song, SongManager
from setlist import Setlist, SetlistEntry
from setlist_manager import SetlistManager
from dialogs import SectionDialog, LoadSongDialog, DelayDialog, LoadSetlistDialog


class MetronomeUI:
    def __init__(self, root, metronome, sound_manager, song_manager, setlist_manager):
        """Initialize the UI.

        Args:
            root (tk.Tk): Root window
            metronome (Metronome): Metronome instance
            sound_manager (SoundManager): Sound manager instance
            song_manager (SongManager): Song manager instance
            setlist_manager (SetlistManager): Setlist manager instance
        """
        self.root = root
        self.metronome = metronome
        self.sound_manager = sound_manager
        self.song_manager = song_manager
        self.setlist_manager = setlist_manager
        self.current_song = None
        self.current_setlist = None
        self._setlist_active = False
        self._tap_times = []

        # Configure root window
        self.root.title("Metronome")
        self.root.minsize(600, 500)

        # Create main container
        self.main_container = ttk.Frame(self.root, padding=WINDOW_PADDING)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Playback controls pack first so they're always visible at the bottom
        self._create_playback_controls()

        # Notebook fills remaining space
        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self._create_basic_tab()
        self._create_song_flow_tab()
        self._create_settings_tab()

        # Wire beat indicator callback
        self.metronome.on_beat = self._on_beat

        # Keyboard shortcuts
        self.root.bind('<space>', self._toggle_start_stop)

        # Resize window to fit all content, capped at screen dimensions
        self.root.update_idletasks()
        req_w = max(self.root.winfo_reqwidth(), 600)
        req_h = max(self.root.winfo_reqheight(), 500)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        w = min(req_w, screen_w - 50)
        h = min(req_h, screen_h - 100)
        self.root.geometry(f"{w}x{h}")

    def _create_basic_tab(self):
        """Create the basic metronome tab."""
        self.basic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.basic_frame, text="Basic")

        # Beat indicator
        self.beat_indicator = tk.Canvas(
            self.basic_frame, width=60, height=60, bg='#333333',
            highlightthickness=0
        )
        self.beat_indicator.pack(pady=FRAME_PADDING)

        self._create_timing_frame()
        self.timing_frame.pack(fill=tk.X, pady=FRAME_PADDING)

    def _create_song_flow_tab(self):
        """Create the song flow tab."""
        self.song_flow_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.song_flow_frame, text="Song Flow")
        
        # Create left and right panes
        left_pane = ttk.Frame(self.song_flow_frame)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_pane = ttk.Frame(self.song_flow_frame)
        right_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Song management frame (left pane)
        song_frame = ttk.LabelFrame(
            left_pane,
            text="Song Management",
            padding=FRAME_PADDING
        )
        song_frame.pack(fill=tk.X, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Song name entry
        ttk.Label(song_frame, text="Song Name:").pack(pady=PADDING)
        self.song_name_entry = ttk.Entry(song_frame)
        self.song_name_entry.pack(fill=tk.X, pady=PADDING)
        
        # Song controls
        song_controls = ttk.Frame(song_frame)
        song_controls.pack(fill=tk.X, pady=PADDING)
        
        ttk.Button(
            song_controls,
            text="New Song",
            command=self._new_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            song_controls,
            text="Save Song",
            command=self._save_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            song_controls,
            text="Load Song",
            command=self._load_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Section list frame
        list_frame = ttk.LabelFrame(
            song_frame,
            text="Song Sections",
            padding=FRAME_PADDING
        )
        list_frame.pack(fill=tk.BOTH, expand=True, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Section list
        self.section_list = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            height=10
        )
        self.section_list.pack(fill=tk.BOTH, expand=True, pady=PADDING)
        
        # Section controls
        controls_frame = ttk.Frame(list_frame)
        controls_frame.pack(fill=tk.X, pady=PADDING)
        
        ttk.Button(
            controls_frame,
            text="Add Section",
            command=self._add_section
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            controls_frame,
            text="Edit Section",
            command=self._edit_section
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            controls_frame,
            text="Remove Section",
            command=self._remove_section
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            controls_frame,
            text="Move Up",
            command=self._move_section_up
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            controls_frame,
            text="Move Down",
            command=self._move_section_down
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Setlist management frame (right pane)
        setlist_frame = ttk.LabelFrame(
            right_pane,
            text="Setlist Management",
            padding=FRAME_PADDING
        )
        setlist_frame.pack(fill=tk.X, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Setlist name entry
        ttk.Label(setlist_frame, text="Setlist Name:").pack(pady=PADDING)
        self.setlist_name_entry = ttk.Entry(setlist_frame)
        self.setlist_name_entry.pack(fill=tk.X, pady=PADDING)
        
        # Setlist controls
        setlist_controls = ttk.Frame(setlist_frame)
        setlist_controls.pack(fill=tk.X, pady=PADDING)
        
        ttk.Button(
            setlist_controls,
            text="New Setlist",
            command=self._new_setlist
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            setlist_controls,
            text="Save Setlist",
            command=self._save_setlist
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            setlist_controls,
            text="Load Setlist",
            command=self._load_setlist
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Setlist entries frame
        entries_frame = ttk.LabelFrame(
            right_pane,
            text="Setlist Entries",
            padding=FRAME_PADDING
        )
        entries_frame.pack(fill=tk.BOTH, expand=True, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        # Setlist entries list
        self.setlist_list = tk.Listbox(
            entries_frame,
            selectmode=tk.SINGLE,
            height=10
        )
        self.setlist_list.pack(fill=tk.BOTH, expand=True, pady=PADDING)
        
        # Setlist entry controls
        entry_controls = ttk.Frame(entries_frame)
        entry_controls.pack(fill=tk.X, pady=PADDING)
        
        ttk.Button(
            entry_controls,
            text="Add Song",
            command=self._add_song_to_setlist
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            entry_controls,
            text="Edit Delay",
            command=self._edit_setlist_delay
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            entry_controls,
            text="Remove Song",
            command=self._remove_song_from_setlist
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            entry_controls,
            text="Move Up",
            command=self._move_setlist_entry_up
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        ttk.Button(
            entry_controls,
            text="Move Down",
            command=self._move_setlist_entry_down
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Setlist playback controls
        setlist_playback = ttk.LabelFrame(
            right_pane,
            text="Setlist Playback",
            padding=FRAME_PADDING
        )
        setlist_playback.pack(fill=tk.X, padx=FRAME_PADDING, pady=FRAME_PADDING)
        
        ttk.Button(
            setlist_playback,
            text="Play Setlist",
            command=self._play_setlist
        ).pack(pady=PADDING)

    def _create_settings_tab(self):
        """Create the settings tab."""
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Sample Management Section
        sample_frame = ttk.LabelFrame(
            self.settings_frame,
            text="Sample Management",
            padding=FRAME_PADDING
        )
        sample_frame.pack(fill=tk.X, pady=FRAME_PADDING)
        
        # Accented Sample Selection
        ttk.Label(sample_frame, text="Accented Beat Sample:").pack(pady=PADDING)
        self.accented_sample_menu = ttk.OptionMenu(
            sample_frame,
            self.sound_manager.accented_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.accented_sample_menu.pack(fill=tk.X, pady=PADDING)
        
        # Regular Sample Selection
        ttk.Label(sample_frame, text="Regular Beat Sample:").pack(pady=PADDING)
        self.regular_sample_menu = ttk.OptionMenu(
            sample_frame,
            self.sound_manager.regular_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.regular_sample_menu.pack(fill=tk.X, pady=PADDING)
        
        # Count-in Sample Selection
        ttk.Label(sample_frame, text="Count-in Sample:").pack(pady=PADDING)
        self.countin_sample_menu = ttk.OptionMenu(
            sample_frame,
            self.sound_manager.countin_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.countin_sample_menu.pack(fill=tk.X, pady=PADDING)
        
        # Upload Custom Sample Button
        ttk.Button(
            sample_frame,
            text="Upload Custom Sample",
            command=self._upload_custom_sample
        ).pack(pady=PADDING)
        
        # Sample Volume Controls
        volume_frame = ttk.LabelFrame(
            self.settings_frame,
            text="Sample Volumes",
            padding=FRAME_PADDING
        )
        volume_frame.pack(fill=tk.X, pady=FRAME_PADDING)
        
        # Accented Volume
        ttk.Label(volume_frame, text="Accented Volume:").pack(pady=PADDING)
        ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.sound_manager.accented_volume
        ).pack(fill=tk.X, pady=PADDING)
        
        # Regular Volume
        ttk.Label(volume_frame, text="Regular Volume:").pack(pady=PADDING)
        ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.sound_manager.regular_volume
        ).pack(fill=tk.X, pady=PADDING)
        
        # Count-in Volume
        ttk.Label(volume_frame, text="Count-in Volume:").pack(pady=PADDING)
        ttk.Scale(
            volume_frame,
            from_=0.0,
            to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.sound_manager.countin_volume
        ).pack(fill=tk.X, pady=PADDING)

    def _create_playback_controls(self):
        """Create playback control buttons."""
        self.control_frame = ttk.LabelFrame(
            self.main_container,
            text="Controls",
            padding=FRAME_PADDING
        )
        self.control_frame.pack(fill=tk.X, pady=FRAME_PADDING)

        # Button container for better layout
        button_container = ttk.Frame(self.control_frame)
        button_container.pack(expand=True)

        # Start and Stop buttons side by side
        self.start_button = ttk.Button(
            button_container,
            text="Start",
            command=self._start_metronome,
            style='Accent.TButton'
        )
        self.start_button.pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        self.stop_button = ttk.Button(
            button_container,
            text="Stop",
            command=self._stop_metronome
        )
        self.stop_button.pack(side=tk.LEFT, padx=BUTTON_PADDING)

        ttk.Button(
            button_container,
            text="Tap Tempo",
            command=self._tap_tempo
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

    def _new_song(self):
        """Create a new song."""
        if self.current_song and self.section_list.size() > 0:
            if not messagebox.askyesno(
                "Confirm",
                "Create new song? Current song will be lost."
            ):
                return
        
        self.current_song = Song(
            name=self.song_name_entry.get() or "Untitled",
            sections=[]
        )
        self.section_list.delete(0, tk.END)
        self.song_name_entry.delete(0, tk.END)
        self.song_name_entry.insert(0, "Untitled")

    def _save_song(self):
        """Save current song to file."""
        if not self.current_song:
            messagebox.showwarning("Warning", "No song to save")
            return
            
        name = self.song_name_entry.get()
        if not name:
            messagebox.showwarning("Warning", "Please enter a song name")
            return
            
        self.current_song.name = name
        self.song_manager.save_song(self.current_song, name)
        messagebox.showinfo("Success", "Song saved successfully")

    def _load_song(self):
        """Load a song from file."""
        if self.current_song and self.section_list.size() > 0:
            if not messagebox.askyesno(
                "Confirm",
                "Load new song? Current song will be lost."
            ):
                return
        
        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            self.current_song = dialog.result
            self.song_name_entry.delete(0, tk.END)
            self.song_name_entry.insert(0, self.current_song.name)
            self.section_list.delete(0, tk.END)
            for section in self.current_song.sections:
                self.section_list.insert(tk.END, section.name)

    def _add_section(self):
        """Open dialog to add a new section."""
        if not self.current_song:
            self._new_song()
            
        dialog = SectionDialog(self.root)
        if dialog.result:
            section = SongSection(**dialog.result)
            self.current_song.sections.append(section)
            self.section_list.insert(tk.END, section.name)

    def _edit_section(self):
        """Open dialog to edit selected section."""
        if not self.current_song:
            messagebox.showwarning("Warning", "No song loaded")
            return
            
        selection = self.section_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a section to edit")
            return
            
        index = selection[0]
        section = self.current_song.sections[index]
        dialog = SectionDialog(self.root, section)
        if dialog.result:
            updated_section = SongSection(**dialog.result)
            self.current_song.sections[index] = updated_section
            self.section_list.delete(index)
            self.section_list.insert(index, updated_section.name)

    def _remove_section(self):
        """Remove selected section."""
        if not self.current_song:
            messagebox.showwarning("Warning", "No song loaded")
            return
            
        selection = self.section_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a section to remove")
            return
            
        if messagebox.askyesno("Confirm", "Remove selected section?"):
            index = selection[0]
            self.current_song.sections.pop(index)
            self.section_list.delete(index)

    def _move_section_up(self):
        """Move selected section up in the list."""
        if not self.current_song:
            return
            
        selection = self.section_list.curselection()
        if not selection or selection[0] == 0:
            return
            
        index = selection[0]
        section = self.current_song.sections.pop(index)
        self.current_song.sections.insert(index - 1, section)
        name = self.section_list.get(index)
        self.section_list.delete(index)
        self.section_list.insert(index - 1, name)
        self.section_list.selection_set(index - 1)

    def _move_section_down(self):
        """Move selected section down in the list."""
        if not self.current_song:
            return
            
        selection = self.section_list.curselection()
        if not selection or selection[0] == self.section_list.size() - 1:
            return
            
        index = selection[0]
        section = self.current_song.sections.pop(index)
        self.current_song.sections.insert(index + 1, section)
        name = self.section_list.get(index)
        self.section_list.delete(index)
        self.section_list.insert(index + 1, name)
        self.section_list.selection_set(index + 1)

    def _play_setlist(self):
        """Play through the entire setlist."""
        if not self.current_setlist or not self.current_setlist.entries:
            messagebox.showwarning("Warning", "No setlist loaded")
            return

        self._setlist_active = True

        def wait_then_continue(index):
            if not self._setlist_active:
                return
            if self.metronome.is_running:
                self.root.after(100, lambda: wait_then_continue(index))
            else:
                entry = self.current_setlist.entries[index]
                self.root.after(
                    int(entry.delay_after * 1000),
                    lambda: play_next_song(index + 1)
                )

        def play_next_song(index):
            if not self._setlist_active or index >= len(self.current_setlist.entries):
                self._setlist_active = False
                return

            entry = self.current_setlist.entries[index]
            self.metronome.start_song_flow(entry.song.sections)
            wait_then_continue(index)

        play_next_song(0)

    def _stop_metronome(self):
        """Stop the metronome and cancel any active setlist playback."""
        self._setlist_active = False
        self.metronome.stop()

    def _start_metronome(self):
        """Start the metronome with current settings."""
        try:
            self.metronome.timer_duration = float(self.timer_entry.get())
        except ValueError:
            self.metronome.timer_duration = 0
            
        try:
            self.metronome.beats_per_bar = int(self.beats_entry.get())
            self.metronome.subdivisions = int(self.subdiv_entry.get())
            self.metronome.tempo_change_step = int(self.step_entry.get())
            self.metronome.tempo_change_interval = int(self.interval_entry.get())
            self.metronome.count_in_bars = int(self.count_in_bars_spin.get())
        except ValueError:
            pass
            
        self.metronome.start()

    def _update_bpm_display(self, *args):
        """Update the BPM display label with current BPM value."""
        self.bpm_display.config(text=str(self.metronome.bpm.get()))

    def _on_swing_toggle(self):
        """When swing is enabled, auto-set subdivisions to 2."""
        if self.metronome.swing_enabled.get():
            self.subdiv_entry.delete(0, tk.END)
            self.subdiv_entry.insert(0, "2")
            self.metronome.subdivisions = 2

    def _tap_tempo(self):
        """Record a tap and update BPM from average tap interval."""
        now = time.time()
        if self._tap_times and (now - self._tap_times[-1]) > 2.0:
            self._tap_times = []
        self._tap_times.append(now)
        if len(self._tap_times) >= 2:
            intervals = [
                self._tap_times[i + 1] - self._tap_times[i]
                for i in range(len(self._tap_times) - 1)
            ]
            bpm = round(60 / (sum(intervals) / len(intervals)))
            self.metronome.bpm.set(max(MIN_BPM, min(MAX_BPM, bpm)))

    def _toggle_start_stop(self, event=None):
        """Toggle start/stop; ignores event when focus is in an Entry."""
        if isinstance(self.root.focus_get(), (ttk.Entry, tk.Entry)):
            return
        if self.metronome.is_running:
            self._stop_metronome()
        else:
            self._start_metronome()

    def _on_beat(self, is_accented):
        """Called from the metronome thread on each beat tick."""
        self.root.after(0, lambda: self._flash_beat(is_accented))

    def _flash_beat(self, is_accented):
        """Flash the beat indicator canvas."""
        color = '#FF4444' if is_accented else '#44BB44'
        self.beat_indicator.config(bg=color)
        self.root.after(100, lambda: self.beat_indicator.config(bg='#333333'))

    def _upload_custom_sample(self):
        """Handle custom sample upload."""
        file_path = filedialog.askopenfilename(
            title="Select WAV File",
            filetypes=[("WAV files", "*.wav")]
        )
        
        if file_path:
            try:
                # Copy file to samples directory
                filename = os.path.basename(file_path)
                dest_path = os.path.join(SAMPLES_FOLDER, filename)
                shutil.copy2(file_path, dest_path)
                
                # Reload samples in sound manager
                self.sound_manager._preload_samples()
                
                # Update sample menus
                samples = self.sound_manager.get_available_samples()
                self.accented_sample_menu['values'] = samples
                self.regular_sample_menu['values'] = samples
                self.countin_sample_menu['values'] = samples
                
                messagebox.showinfo(
                    "Success",
                    "Custom sample uploaded successfully!"
                )
            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Failed to upload sample: {str(e)}"
                )

    def _create_timing_frame(self):
        """Create timing-related controls frame."""
        self.timing_frame = ttk.LabelFrame(
            self.basic_frame,
            text="Timing Settings",
            padding=FRAME_PADDING
        )

        # BPM Slider and Display
        bpm_frame = ttk.Frame(self.timing_frame)
        bpm_frame.pack(fill=tk.X, pady=PADDING)
        
        ttk.Label(bpm_frame, text="BPM:").pack(side=tk.LEFT)
        self.bpm_slider = ttk.Scale(
            bpm_frame,
            from_=MIN_BPM,
            to=MAX_BPM,
            orient=tk.HORIZONTAL,
            variable=self.metronome.bpm
        )
        self.bpm_slider.set(DEFAULT_BPM)
        self.bpm_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.bpm_display = ttk.Label(bpm_frame, text=str(DEFAULT_BPM))
        self.bpm_display.pack(side=tk.LEFT, padx=PADDING)
        
        # Update BPM display when BPM changes
        self.metronome.bpm.trace_add('write', lambda *args: self._update_bpm_display())

        # Timer Duration Entry
        ttk.Label(
            self.timing_frame,
            text="Timer Duration (seconds, 0 for none):"
        ).pack(pady=PADDING)
        self.timer_entry = ttk.Entry(self.timing_frame)
        self.timer_entry.insert(0, str(DEFAULT_TIMER_DURATION))
        self.timer_entry.pack(fill=tk.X, pady=PADDING)

        # Tempo Change Mode
        ttk.Label(
            self.timing_frame,
            text="Tempo Change Mode:"
        ).pack(pady=PADDING)
        self.tempo_mode_menu = ttk.OptionMenu(
            self.timing_frame,
            self.metronome.tempo_change_mode,
            "None",
            "Speed Up",
            "Slow Down"
        )
        self.tempo_mode_menu.pack(fill=tk.X, pady=PADDING)

        # Tempo Change Step
        ttk.Label(
            self.timing_frame,
            text="Tempo Change Step (BPM):"
        ).pack(pady=PADDING)
        self.step_entry = ttk.Entry(self.timing_frame)
        self.step_entry.insert(0, str(DEFAULT_TEMPO_CHANGE_STEP))
        self.step_entry.pack(fill=tk.X, pady=PADDING)

        # Tempo Change Interval
        ttk.Label(
            self.timing_frame,
            text="Tempo Change Interval (Bars):"
        ).pack(pady=PADDING)
        self.interval_entry = ttk.Entry(self.timing_frame)
        self.interval_entry.insert(0, str(DEFAULT_TEMPO_CHANGE_INTERVAL))
        self.interval_entry.pack(fill=tk.X, pady=PADDING)

        # Beats per Bar
        ttk.Label(self.timing_frame, text="Beats per Bar:").pack(pady=PADDING)
        self.beats_entry = ttk.Entry(self.timing_frame)
        self.beats_entry.insert(0, str(DEFAULT_BEATS_PER_BAR))
        self.beats_entry.pack(fill=tk.X, pady=PADDING)

        # Subdivisions per Beat
        ttk.Label(
            self.timing_frame,
            text="Subdivisions per Beat:"
        ).pack(pady=PADDING)
        self.subdiv_entry = ttk.Entry(self.timing_frame)
        self.subdiv_entry.insert(0, str(DEFAULT_SUBDIVISIONS))
        self.subdiv_entry.pack(fill=tk.X, pady=PADDING)

        # Swing Toggle
        self.swing_check = ttk.Checkbutton(
            self.timing_frame,
            text="Enable Swing (requires subdivisions = 2)",
            variable=self.metronome.swing_enabled,
            command=self._on_swing_toggle
        )
        self.swing_check.pack(pady=PADDING)

        # Count-in Bars
        countin_frame = ttk.Frame(self.timing_frame)
        countin_frame.pack(fill=tk.X, pady=PADDING)
        ttk.Label(countin_frame, text="Count-in Bars:").pack(side=tk.LEFT)
        self.count_in_bars_spin = ttk.Spinbox(
            countin_frame, from_=1, to=8, width=5,
            textvariable=tk.IntVar(value=DEFAULT_COUNT_IN_BARS)
        )
        self.count_in_bars_spin.pack(side=tk.LEFT, padx=PADDING)

    def _new_setlist(self):
        """Create a new setlist."""
        if self.current_setlist and self.setlist_list.size() > 0:
            if not messagebox.askyesno(
                "Confirm",
                "Create new setlist? Current setlist will be lost."
            ):
                return
        
        # Get setlist name
        name = self.setlist_name_entry.get() or "Untitled"
        self.current_setlist = Setlist(name=name)
        self.setlist_list.delete(0, tk.END)
        self.setlist_name_entry.delete(0, tk.END)
        self.setlist_name_entry.insert(0, name)
        
        # Open song selection dialog
        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            song = dialog.result
            delay_dialog = DelayDialog(self.root)
            if delay_dialog.result is not None:
                self.current_setlist.add_entry(
                    song,
                    delay_after=delay_dialog.result
                )
                self.setlist_list.insert(
                    tk.END,
                    f"{song.name} (Delay: {delay_dialog.result}s)"
                )

    def _save_setlist(self):
        """Save current setlist to file."""
        if not self.current_setlist:
            messagebox.showwarning("Warning", "No setlist to save")
            return
            
        name = self.setlist_name_entry.get()
        if not name:
            messagebox.showwarning("Warning", "Please enter a setlist name")
            return
            
        self.current_setlist.name = name
        self.setlist_manager.save_setlist(self.current_setlist)
        messagebox.showinfo("Success", "Setlist saved successfully")

    def _load_setlist(self):
        """Load a setlist from file."""
        if self.current_setlist and self.setlist_list.size() > 0:
            if not messagebox.askyesno(
                "Confirm",
                "Load new setlist? Current setlist will be lost."
            ):
                return
        
        dialog = LoadSetlistDialog(self.root, self.setlist_manager, self.song_manager)
        if dialog.result:
            self.current_setlist = dialog.result
            self.setlist_name_entry.delete(0, tk.END)
            self.setlist_name_entry.insert(0, self.current_setlist.name)
            self.setlist_list.delete(0, tk.END)
            for entry in self.current_setlist.entries:
                self.setlist_list.insert(
                    tk.END,
                    f"{entry.song.name} (Delay: {entry.delay_after}s)"
                )

    def _add_song_to_setlist(self):
        """Add a song to setlist."""
        if not self.current_setlist:
            self._new_setlist()
            return
            
        # Open song selection dialog
        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            song = dialog.result
            delay_dialog = DelayDialog(self.root)
            if delay_dialog.result is not None:
                self.current_setlist.add_entry(
                    song,
                    delay_after=delay_dialog.result
                )
                self.setlist_list.insert(
                    tk.END,
                    f"{song.name} (Delay: {delay_dialog.result}s)"
                )

    def _edit_setlist_delay(self):
        """Edit delay for selected setlist entry."""
        if not self.current_setlist:
            messagebox.showwarning("Warning", "No setlist loaded")
            return
            
        selection = self.setlist_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an entry to edit")
            return
            
        index = selection[0]
        entry = self.current_setlist.entries[index]
        dialog = DelayDialog(self.root, entry.delay_after)
        if dialog.result is not None:
            entry.delay_after = dialog.result
            self.setlist_list.delete(index)
            self.setlist_list.insert(
                index,
                f"{entry.song.name} (Delay: {dialog.result}s)"
            )

    def _remove_song_from_setlist(self):
        """Remove selected song from setlist."""
        if not self.current_setlist:
            messagebox.showwarning("Warning", "No setlist loaded")
            return
            
        selection = self.setlist_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select an entry to remove")
            return
            
        if messagebox.askyesno("Confirm", "Remove selected entry?"):
            index = selection[0]
            self.current_setlist.remove_entry(index)
            self.setlist_list.delete(index)

    def _move_setlist_entry_up(self):
        """Move selected entry up in the setlist."""
        if not self.current_setlist:
            return
            
        selection = self.setlist_list.curselection()
        if not selection or selection[0] == 0:
            return
            
        index = selection[0]
        self.current_setlist.move_entry(index, index - 1)
        text = self.setlist_list.get(index)
        self.setlist_list.delete(index)
        self.setlist_list.insert(index - 1, text)
        self.setlist_list.selection_set(index - 1)

    def _move_setlist_entry_down(self):
        """Move selected entry down in the setlist."""
        if not self.current_setlist:
            return
            
        selection = self.setlist_list.curselection()
        if not selection or selection[0] == self.setlist_list.size() - 1:
            return
            
        index = selection[0]
        self.current_setlist.move_entry(index, index + 1)
        text = self.setlist_list.get(index)
        self.setlist_list.delete(index)
        self.setlist_list.insert(index + 1, text)
        self.setlist_list.selection_set(index + 1)


 