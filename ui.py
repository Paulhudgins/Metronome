"""User interface for the metronome application."""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import shutil
import time

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')

# Labeled subdivision options shown in the combobox
SUBDIV_OPTIONS = [
    "1 — Quarter notes",
    "2 — Eighth notes",
    "3 — Triplets",
    "4 — Sixteenth notes",
    "5 — Quintuplets",
    "6 — Sextuplets",
    "7 — Septuplets",
    "8 — Thirty-second notes",
]

# Common time signature presets: (label, beats_per_bar, denominator, beat_pattern)
# Pattern values: 'S' = strong accent, 'M' = medium accent, 'W' = weak (regular)
TIME_SIG_PRESETS = [
    [
        ("2/4",  2, 4, ['S','W']),
        ("3/4",  3, 4, ['S','W','W']),
        ("4/4",  4, 4, ['S','W','W','W']),
        ("5/4",  5, 4, ['S','W','W','M','W']),        # 3+2 grouping
        ("6/4",  6, 4, ['S','W','W','M','W','W']),
        ("7/4",  7, 4, ['S','W','W','M','W','W','W']), # 3+4 grouping
    ],
    [
        ("5/8",  5, 8, ['S','W','W','M','W']),          # 3+2
        ("6/8",  6, 8, ['S','W','W','M','W','W']),
        ("7/8",  7, 8, ['S','W','W','M','W','W','W']),  # 3+4
        ("9/8",  9, 8, ['S','W','W','M','W','W','M','W','W']),
        ("12/8", 12, 8, ['S','W','W','M','W','W','M','W','W','M','W','W']),
    ],
]
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
        self._current_setlist_index = 0
        self._setlist_generation = 0
        self._shuffle_enabled = False
        self._shuffle_order = []
        self._loop_in_index = None
        self._loop_out_index = None
        self._song_play_active = False
        self._song_dirty = False
        self._setlist_dirty = False
        self._timesig_denominator = 4  # display denominator; presets update this
        self._recent_songs = []
        self._practice_section_obj = None  # set while practice mode is active

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
        self._create_help_tab()

        # Apply theme colors to non-ttk widgets (Listbox, ScrolledText)
        self._style_tk_widgets()

        # Wire beat indicator callback
        self.metronome.on_beat = self._on_beat

        # Keyboard shortcuts
        self.root.bind('<space>', self._toggle_start_stop)
        for key in ('<plus>', '<equal>', '<Up>'):
            self.root.bind(key, self._nudge_bpm_up)
        for key in ('<minus>', '<Down>'):
            self.root.bind(key, self._nudge_bpm_down)
        self.root.bind('t', self._on_tap_key)
        self.root.bind('T', self._on_tap_key)

        # Load persisted settings, then handle clean close
        self._load_settings()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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

        # Now Playing panel (hidden by default, shown during setlist playback)
        self._create_now_playing_frame()

        self._create_timing_frame()
        self.timing_frame.pack(fill=tk.X, pady=FRAME_PADDING)

    def _create_now_playing_frame(self):
        """Create the Now Playing panel (initially hidden)."""
        self.now_playing_frame = ttk.LabelFrame(
            self.basic_frame, text="Now Playing", padding=FRAME_PADDING
        )
        # Not packed — shown only during setlist playback

        self.now_playing_song_label = ttk.Label(self.now_playing_frame, text="")
        self.now_playing_song_label.pack()

        # Setlist position — "Song 2 of 5" (empty during single-song play)
        self.now_playing_position_label = ttk.Label(
            self.now_playing_frame, text="", foreground='gray'
        )
        self.now_playing_position_label.pack()

        self.now_playing_section_label = ttk.Label(
            self.now_playing_frame, text="", font=('TkDefaultFont', 12, 'bold')
        )
        self.now_playing_section_label.pack()

        # BPM display — updated each bar as sections may have different tempos
        self.now_playing_bpm_label = ttk.Label(self.now_playing_frame, text="")
        self.now_playing_bpm_label.pack()

        self.now_playing_bars_label = ttk.Label(self.now_playing_frame, text="")
        self.now_playing_bars_label.pack()

        self.now_playing_next_label = ttk.Label(self.now_playing_frame, text="")
        self.now_playing_next_label.pack()

        # Transport buttons: Restart / Skip / Shuffle
        transport_row = ttk.Frame(self.now_playing_frame)
        transport_row.pack(pady=PADDING)

        ttk.Button(
            transport_row, text="Restart", command=self._restart_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        ttk.Button(
            transport_row, text="Skip", command=self._skip_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        self.shuffle_btn = ttk.Button(
            transport_row, text="Shuffle: Off", command=self._toggle_shuffle
        )
        self.shuffle_btn.pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Loop buttons
        loop_row = ttk.Frame(self.now_playing_frame)
        loop_row.pack(pady=PADDING)

        self.loop_in_btn = ttk.Button(
            loop_row, text="Set Loop In", command=self._set_loop_in
        )
        self.loop_in_btn.pack(side=tk.LEFT, padx=BUTTON_PADDING)

        self.loop_out_btn = ttk.Button(
            loop_row, text="Set Loop Out", command=self._set_loop_out
        )
        self.loop_out_btn.pack(side=tk.LEFT, padx=BUTTON_PADDING)

        ttk.Button(
            loop_row, text="Clear Loop", command=self._clear_loop
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Guidance label — changes text to walk the user through the workflow
        self.loop_guidance_label = ttk.Label(
            self.now_playing_frame, text="", foreground='gray',
            font=('TkDefaultFont', 8, 'italic')
        )
        self.loop_guidance_label.pack()

        # Active loop status ("↺ Verse → Chorus")
        self.now_playing_loop_label = ttk.Label(
            self.now_playing_frame, text="", font=('TkDefaultFont', 9, 'bold')
        )
        self.now_playing_loop_label.pack()

    def _show_now_playing(self, song_name):
        """Show the Now Playing panel and switch to the Basic tab."""
        self.now_playing_song_label.config(text=song_name)
        self._refresh_loop_ui()  # ensure button colours/text are correct for new song
        self.now_playing_frame.pack(
            fill=tk.X, pady=FRAME_PADDING, before=self.timing_frame
        )
        self.notebook.select(0)

    def _hide_now_playing(self):
        """Hide the Now Playing panel and clear all labels and loop state."""
        self.now_playing_frame.pack_forget()
        self.now_playing_song_label.config(text="")
        self.now_playing_position_label.config(text="")
        self.now_playing_section_label.config(text="")
        self.now_playing_bpm_label.config(text="")
        self.now_playing_bars_label.config(text="")
        self.now_playing_next_label.config(text="")
        self._loop_in_index = None
        self._loop_out_index = None
        self.metronome.loop_start = None
        self.metronome.loop_end = None
        self._refresh_loop_ui()

    def _on_count_in(self, beats_remaining, total_beats):
        """Called from the metronome thread on each count-in beat."""
        self.root.after(
            0, lambda: self._update_count_in(beats_remaining, total_beats)
        )

    def _update_count_in(self, beats_remaining, total_beats):
        """Show count-in progress in the Now Playing panel."""
        self.now_playing_section_label.config(text="Count In")
        plural = "beat" if beats_remaining == 1 else "beats"
        self.now_playing_bars_label.config(
            text=f"{beats_remaining} {plural} remaining"
        )
        sections = self.metronome.sections
        if (self._loop_in_index is not None and self._loop_out_index is not None
                and sections and self._loop_in_index < len(sections)):
            # Loop count-in — returning to loop start, not the song's first section
            self.now_playing_next_label.config(
                text=f"Returning to: {sections[self._loop_in_index].name}"
            )
        elif sections:
            self.now_playing_next_label.config(text=f"Starting: {sections[0].name}")
        else:
            self.now_playing_next_label.config(text="")

    def _on_bar(self, section, bars_remaining, next_section):
        """Called from the metronome thread on each accented beat during song flow."""
        self.root.after(
            0, lambda: self._update_now_playing(section, bars_remaining, next_section)
        )

    def _update_now_playing(self, section, bars_remaining, next_section):
        """Update all Now Playing labels for the current bar."""
        current_bar = section.bars - bars_remaining + 1
        self.now_playing_section_label.config(text=section.name)
        self.now_playing_bpm_label.config(text=f"{section.bpm} BPM")
        self.now_playing_bars_label.config(
            text=f"Bar {current_bar} of {section.bars}  \u2022  {bars_remaining} bars remaining"
        )

        # Determine next section text
        if (self._loop_in_index is not None and self._loop_out_index is not None
                and self.metronome.current_section_index == self._loop_out_index):
            sections = self.metronome.sections
            if sections and self._loop_in_index < len(sections):
                loop_start_name = sections[self._loop_in_index].name
                next_text = f"Next: \u21a9 {loop_start_name}"
            else:
                next_text = "Next: \u21a9 loop"
        elif next_section is not None:
            next_text = f"Next: {next_section.name}"
        else:
            next_text = "Next: End"
        self.now_playing_next_label.config(text=next_text)

        # Sync beats/subdiv — skip if user is actively editing those widgets
        focused = self.root.focus_get()
        if focused not in (self.beats_entry, self.subdiv_entry):
            self.beats_entry.delete(0, tk.END)
            self.beats_entry.insert(0, str(section.beats_per_bar))
            self.timesig_label.config(
                text=f"{section.beats_per_bar} / {self._timesig_denominator}"
            )
            self.subdiv_entry.set(self._subdiv_label(section.subdivisions))
            self._update_pattern_display()

    def _play_next_song(self, pos):
        """Play the song at position `pos` in the current shuffle order."""
        if not self._setlist_active or pos >= len(self._shuffle_order):
            self._setlist_active = False
            self._hide_now_playing()
            self.metronome.on_count_in = None
            self.metronome.on_bar = None
            return

        self._current_setlist_index = pos
        self._setlist_generation += 1
        gen = self._setlist_generation

        # Clear any loop left over from the previous song
        self._loop_in_index = None
        self._loop_out_index = None
        self.metronome.loop_start = None
        self.metronome.loop_end = None

        entry_idx = self._shuffle_order[pos]
        entry = self.current_setlist.entries[entry_idx]

        # Expand sections by repeat count
        expanded = [s for s in entry.song.sections for _ in range(s.repeat)]

        self._apply_playback_settings()
        self.metronome.on_count_in = self._on_count_in
        self.metronome.on_bar = self._on_bar
        self.metronome.start_song_flow(expanded)
        self.start_button.config(text="Pause", command=self._pause_metronome)
        total = len(self._shuffle_order)
        self._show_now_playing(entry.song.name)
        self.now_playing_position_label.config(text=f"Song {pos + 1} of {total}")

        # Highlight the active song in the setlist widget
        self.setlist_list.selection_clear(0, tk.END)
        self.setlist_list.selection_set(entry_idx)
        self.setlist_list.see(entry_idx)

        self._wait_then_continue(pos, entry_idx, gen)

    def _wait_then_continue(self, pos, entry_idx, gen):
        """Poll until song finishes, then schedule the next song."""
        if not self._setlist_active or gen != self._setlist_generation:
            return
        if self.metronome.is_running:
            self.root.after(100, lambda: self._wait_then_continue(pos, entry_idx, gen))
        else:
            entry = self.current_setlist.entries[entry_idx]
            self.root.after(
                int(entry.delay_after * 1000),
                lambda: self._play_next_song(pos + 1)
            )

    def _restart_song(self):
        """Restart the current song (or practice section) from the beginning."""
        if self._song_play_active:
            if self._practice_section_obj is not None:
                section = self._practice_section_obj
                self._song_play_active = False
                self._practice_section_obj = None
                self._start_practice(section)
            else:
                self._song_play_active = False
                self._play_song()
        else:
            pos = self._current_setlist_index
            self._setlist_generation += 1
            self.metronome.stop()
            self._loop_in_index = None
            self._loop_out_index = None
            self.metronome.loop_start = None
            self.metronome.loop_end = None
            self._play_next_song(pos)

    def _skip_song(self):
        """Skip to the next song (or end playback if playing a single song)."""
        if self._song_play_active:
            self._song_play_active = False
            self._setlist_generation += 1
            self.metronome.stop()
            self.metronome.on_count_in = None
            self.metronome.on_bar = None
            self._hide_now_playing()
        else:
            self._setlist_generation += 1
            self.metronome.stop()
            self._loop_in_index = None
            self._loop_out_index = None
            self.metronome.loop_start = None
            self.metronome.loop_end = None
            self._play_next_song(self._current_setlist_index + 1)

    def _toggle_shuffle(self):
        """Toggle shuffle mode; reshuffles remaining songs when enabling."""
        if self._song_play_active:
            return  # shuffle not applicable for single-song play
        import random
        self._shuffle_enabled = not self._shuffle_enabled
        if self._shuffle_enabled:
            # Shuffle everything after the current position
            remaining = self._shuffle_order[self._current_setlist_index + 1:]
            random.shuffle(remaining)
            self._shuffle_order[self._current_setlist_index + 1:] = remaining
            self.shuffle_btn.config(text="Shuffle: On")
        else:
            # Restore sequential order from current position onward
            n = len(self.current_setlist.entries)
            self._shuffle_order = (
                self._shuffle_order[:self._current_setlist_index + 1]
                + list(range(self._current_setlist_index + 1, n))
            )
            self.shuffle_btn.config(text="Shuffle: Off")

    def _set_loop_in(self):
        """Mark the current section as the loop start."""
        if not self.metronome.is_running or self.metronome.current_section is None:
            return
        self._loop_in_index = self.metronome.current_section_index
        self.metronome.loop_start = self._loop_in_index
        self._refresh_loop_ui()

    def _set_loop_out(self):
        """Mark the current section as the loop end."""
        if not self.metronome.is_running or self.metronome.current_section is None:
            return
        self._loop_out_index = self.metronome.current_section_index
        self.metronome.loop_end = self._loop_out_index
        self._refresh_loop_ui()

    def _clear_loop(self):
        """Remove all loop markers."""
        self._loop_in_index = None
        self._loop_out_index = None
        self.metronome.loop_start = None
        self.metronome.loop_end = None
        self._refresh_loop_ui()

    def _refresh_loop_ui(self):
        """Update loop button colours, texts, guidance label, and status label."""
        if not hasattr(self, 'loop_in_btn'):
            return  # UI not yet fully created
        sections = self.metronome.sections
        in_idx = self._loop_in_index
        out_idx = self._loop_out_index

        # Button texts reflect which section is marked
        if in_idx is not None and sections and in_idx < len(sections):
            self.loop_in_btn.config(text=f"\u2713 {sections[in_idx].name} (In)")
        else:
            self.loop_in_btn.config(text="Set Loop In")

        if out_idx is not None and sections and out_idx < len(sections):
            self.loop_out_btn.config(text=f"\u2713 {sections[out_idx].name} (Out)")
        else:
            self.loop_out_btn.config(text="Set Loop Out")

        # Guidance text and foreground colours depend on how many markers are set
        if in_idx is not None and out_idx is not None:
            # Both set — loop is active
            if sections and in_idx < len(sections) and out_idx < len(sections):
                self.now_playing_loop_label.config(
                    text=f"\u21ba {sections[in_idx].name} \u2192 {sections[out_idx].name}",
                    foreground='#4CAF50'
                )
            self.loop_guidance_label.config(
                text="Count-in plays before each repeat", foreground='gray'
            )

        elif in_idx is not None:
            # Only In set — waiting for Out
            self.now_playing_loop_label.config(text="")
            self.loop_guidance_label.config(
                text="\u2192 Now press Set Loop Out to complete the loop",
                foreground='#FF9800'
            )

        elif out_idx is not None:
            # Only Out set — waiting for In
            self.now_playing_loop_label.config(text="")
            self.loop_guidance_label.config(
                text="\u2192 Now press Set Loop In to complete the loop",
                foreground='#FF9800'
            )

        else:
            # No markers — show static hint
            self.now_playing_loop_label.config(text="")
            self.loop_guidance_label.config(
                text="Loop In = bar 1 of section  \u2022  Loop Out = plays section to its end",
                foreground='gray'
            )

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

        ttk.Button(
            song_controls,
            text="Duplicate Song",
            command=self._duplicate_song
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Recent songs row
        recent_row = ttk.Frame(song_frame)
        recent_row.pack(fill=tk.X, pady=PADDING)
        ttk.Label(recent_row, text="Recent:").pack(side=tk.LEFT)
        self.recent_songs_combo = ttk.Combobox(
            recent_row, state='readonly', width=30
        )
        self.recent_songs_combo.pack(side=tk.LEFT, padx=PADDING)
        ttk.Button(
            recent_row, text="Load Recent",
            command=self._load_recent_song
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
            text="Duplicate",
            command=self._duplicate_section
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

        ttk.Button(
            controls_frame,
            text="Practice",
            command=self._practice_section
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Song playback controls (left pane)
        song_playback = ttk.LabelFrame(
            left_pane,
            text="Song Playback",
            padding=FRAME_PADDING
        )
        song_playback.pack(fill=tk.X, padx=FRAME_PADDING, pady=FRAME_PADDING)

        ttk.Button(
            song_playback,
            text="Play Song",
            command=self._play_song
        ).pack(pady=PADDING)

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

        ttk.Button(
            setlist_controls,
            text="Export to Text",
            command=self._export_setlist
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

        # Scrollable interior ─────────────────────────────────────────────
        _canvas = tk.Canvas(self.settings_frame, highlightthickness=0)
        _scrollbar = ttk.Scrollbar(
            self.settings_frame, orient='vertical', command=_canvas.yview
        )
        _canvas.configure(yscrollcommand=_scrollbar.set)
        _scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        _canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        _inner = ttk.Frame(_canvas)
        _cw = _canvas.create_window((0, 0), window=_inner, anchor='nw')

        _inner.bind(
            '<Configure>',
            lambda e: _canvas.configure(scrollregion=_canvas.bbox('all'))
        )
        _canvas.bind(
            '<Configure>',
            lambda e: _canvas.itemconfig(_cw, width=e.width)
        )
        # Bind mousewheel only while the pointer is inside the settings area
        _inner.bind(
            '<Enter>',
            lambda e: _canvas.bind_all(
                '<MouseWheel>',
                lambda ev: _canvas.yview_scroll(int(-1 * (ev.delta / 120)), 'units')
            )
        )
        _inner.bind('<Leave>', lambda e: _canvas.unbind_all('<MouseWheel>'))
        # ─────────────────────────────────────────────────────────────────

        # Sample Management Section
        sample_frame = ttk.LabelFrame(
            _inner,
            text="Sample Management",
            padding=FRAME_PADDING
        )
        sample_frame.pack(fill=tk.X, pady=FRAME_PADDING)
        
        # Accented Sample Selection
        ttk.Label(sample_frame, text="Accented Beat Sample:").pack(pady=PADDING)
        acc_row = ttk.Frame(sample_frame)
        acc_row.pack(fill=tk.X, pady=PADDING)
        self.accented_sample_menu = ttk.OptionMenu(
            acc_row,
            self.sound_manager.accented_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.accented_sample_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            acc_row, text="Preview",
            command=lambda: self._preview_sample(
                self.sound_manager.accented_sample_var.get(),
                self.sound_manager.accented_volume.get()
            )
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Regular Sample Selection
        ttk.Label(sample_frame, text="Regular Beat Sample:").pack(pady=PADDING)
        reg_row = ttk.Frame(sample_frame)
        reg_row.pack(fill=tk.X, pady=PADDING)
        self.regular_sample_menu = ttk.OptionMenu(
            reg_row,
            self.sound_manager.regular_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.regular_sample_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            reg_row, text="Preview",
            command=lambda: self._preview_sample(
                self.sound_manager.regular_sample_var.get(),
                self.sound_manager.regular_volume.get()
            )
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)

        # Count-in Sample Selection
        ttk.Label(sample_frame, text="Count-in Sample:").pack(pady=PADDING)
        ci_row = ttk.Frame(sample_frame)
        ci_row.pack(fill=tk.X, pady=PADDING)
        self.countin_sample_menu = ttk.OptionMenu(
            ci_row,
            self.sound_manager.countin_sample_var,
            *self.sound_manager.get_available_samples()
        )
        self.countin_sample_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(
            ci_row, text="Preview",
            command=lambda: self._preview_sample(
                self.sound_manager.countin_sample_var.get(),
                self.sound_manager.countin_volume.get()
            )
        ).pack(side=tk.LEFT, padx=BUTTON_PADDING)
        
        # Upload Custom Sample Button
        ttk.Button(
            sample_frame,
            text="Upload Custom Sample",
            command=self._upload_custom_sample
        ).pack(pady=PADDING)
        
        # Sample Volume Controls
        volume_frame = ttk.LabelFrame(
            _inner,
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

        # Playback Feel section
        feel_frame = ttk.LabelFrame(
            _inner,
            text="Playback Feel",
            padding=FRAME_PADDING
        )
        feel_frame.pack(fill=tk.X, pady=FRAME_PADDING)

        # Humanize slider
        humanize_row = ttk.Frame(feel_frame)
        humanize_row.pack(fill=tk.X, pady=PADDING)
        ttk.Label(humanize_row, text="Humanize:").pack(side=tk.LEFT)
        self.humanize_var = tk.DoubleVar(value=0.0)
        self.humanize_label = ttk.Label(humanize_row, text="0 ms", width=7)
        self.humanize_label.pack(side=tk.RIGHT)
        ttk.Scale(
            humanize_row,
            from_=0,
            to=50,
            orient=tk.HORIZONTAL,
            variable=self.humanize_var,
            command=self._on_humanize_change
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=PADDING)

        # Humanize direction
        direction_row = ttk.Frame(feel_frame)
        direction_row.pack(fill=tk.X, pady=(0, PADDING))
        ttk.Label(direction_row, text="Direction:").pack(side=tk.LEFT)
        self.humanize_direction_var = tk.StringVar(value='push')
        ttk.Radiobutton(
            direction_row, text="Push (play late)",
            variable=self.humanize_direction_var, value='push',
            command=self._on_humanize_change
        ).pack(side=tk.LEFT, padx=PADDING)
        ttk.Radiobutton(
            direction_row, text="Pull (play early)",
            variable=self.humanize_direction_var, value='pull',
            command=self._on_humanize_change
        ).pack(side=tk.LEFT)

        # Fade-in spinbox
        fadein_row = ttk.Frame(feel_frame)
        fadein_row.pack(fill=tk.X, pady=PADDING)
        ttk.Label(fadein_row, text="Fade-in (bars, 0=off):").pack(side=tk.LEFT)
        self.fadein_var = tk.IntVar(value=0)
        ttk.Spinbox(
            fadein_row,
            from_=0,
            to=32,
            width=5,
            textvariable=self.fadein_var
        ).pack(side=tk.LEFT, padx=PADDING)

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

        # Start/Pause/Resume button — label and command change with state
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

    def _check_song_dirty(self):
        """Return True if it's safe to discard the current song (not dirty or user confirmed)."""
        if self._song_dirty:
            return messagebox.askyesno(
                "Unsaved Changes",
                "The current song has unsaved changes. Discard them?"
            )
        return True

    def _new_song(self):
        """Create a new song."""
        if not self._check_song_dirty():
            return
        # Also confirm if a clean (unedited) song is loaded — prevents silent data loss
        if (self.current_song and self.current_song.sections
                and not self._song_dirty):
            if not messagebox.askyesno(
                "Confirm", "Discard the current song and start a new one?"
            ):
                return
        self.current_song = Song(
            name=self.song_name_entry.get() or "Untitled",
            sections=[]
        )
        self.section_list.delete(0, tk.END)
        self.song_name_entry.delete(0, tk.END)
        self.song_name_entry.insert(0, "Untitled")
        self._song_dirty = False
        self._update_window_title()

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
        try:
            self.song_manager.save_song(self.current_song, name)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save song: {e}")
            return
        self._song_dirty = False
        self._push_recent_song(name)
        self._update_window_title()
        messagebox.showinfo("Success", "Song saved successfully")

    def _load_song(self):
        """Load a song from file."""
        if not self._check_song_dirty():
            return

        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            self.current_song = dialog.result
            self.song_name_entry.delete(0, tk.END)
            self.song_name_entry.insert(0, self.current_song.name)
            self.section_list.delete(0, tk.END)
            for section in self.current_song.sections:
                self.section_list.insert(tk.END, self._section_list_text(section))
            self._song_dirty = False
            self._push_recent_song(self.current_song.name)
            self._update_window_title()

    def _push_recent_song(self, name):
        """Add a song name to the top of the recent songs list."""
        self._recent_songs = [name] + [n for n in self._recent_songs if n != name]
        self._recent_songs = self._recent_songs[:5]
        self.recent_songs_combo['values'] = self._recent_songs
        if self._recent_songs:
            self.recent_songs_combo.set(self._recent_songs[0])

    def _load_recent_song(self):
        """Load the song selected in the recent songs combobox."""
        name = self.recent_songs_combo.get()
        if not name:
            return
        if not self._check_song_dirty():
            return
        try:
            song = self.song_manager.load_song(name)
        except Exception as e:
            self._recent_songs = [n for n in self._recent_songs if n != name]
            self.recent_songs_combo['values'] = self._recent_songs
            messagebox.showerror("Error", f"Could not load '{name}': {e}")
            return
        self.current_song = song
        self.song_name_entry.delete(0, tk.END)
        self.song_name_entry.insert(0, self.current_song.name)
        self.section_list.delete(0, tk.END)
        for section in self.current_song.sections:
            self.section_list.insert(tk.END, self._section_list_text(section))
        self._song_dirty = False
        self._push_recent_song(name)
        self._update_window_title()

    def _add_section(self):
        """Open dialog to add a new section."""
        if not self.current_song:
            self._new_song()

        # Pre-fill from the last section so BPM/time-sig don't need retyping
        template = self.current_song.sections[-1] if self.current_song.sections else None
        dialog = SectionDialog(self.root, template, is_new=True)
        if dialog.result:
            try:
                section = SongSection(**dialog.result)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.current_song.sections.append(section)
            self.section_list.insert(tk.END, self._section_list_text(section))
            self._song_dirty = True
            self._update_window_title()

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
            try:
                updated_section = SongSection(**dialog.result)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            self.current_song.sections[index] = updated_section
            self.section_list.delete(index)
            self.section_list.insert(index, self._section_list_text(updated_section))
            self._song_dirty = True
            self._update_window_title()

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
            self._song_dirty = True
            self._update_window_title()

    def _section_list_text(self, section):
        """Format a section for display in the section listbox."""
        repeat = f"  ×{section.repeat}" if section.repeat > 1 else ""
        ci = "  ↵" if getattr(section, 'count_in', False) else ""
        return f"{section.name}  —  {section.bpm} BPM  —  {section.bars} bars{repeat}{ci}"

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
        self._song_dirty = True
        self._update_window_title()

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
        self._song_dirty = True
        self._update_window_title()

    def _apply_playback_settings(self):
        """Push UI entry values (count-in bars, tempo-change, feel) onto the metronome."""
        try:
            self.metronome.count_in_bars = int(self.count_in_bars_spin.get())
        except ValueError:
            pass
        try:
            self.metronome.tempo_change_step = int(self.step_entry.get())
            self.metronome.tempo_change_interval = int(self.interval_entry.get())
        except ValueError:
            pass
        self.metronome.humanize = self.humanize_var.get()
        self.metronome.humanize_direction = self.humanize_direction_var.get()
        try:
            self.metronome.fade_in_bars = int(self.fadein_var.get())
        except (ValueError, tk.TclError):
            pass

    def _play_song(self):
        """Play the current song directly, showing the Now Playing panel."""
        if not self.current_song or not self.current_song.sections:
            messagebox.showwarning("Warning", "No song loaded or song has no sections")
            return

        # Cancel any active setlist or previous song play
        self._setlist_active = False
        self._song_play_active = True
        self._setlist_generation += 1
        gen = self._setlist_generation

        self.metronome.stop()
        self._loop_in_index = None
        self._loop_out_index = None
        self.metronome.loop_start = None
        self.metronome.loop_end = None

        self._apply_playback_settings()

        # Expand sections by repeat count
        expanded = [s for s in self.current_song.sections for _ in range(s.repeat)]

        self.metronome.on_count_in = self._on_count_in
        self.metronome.on_bar = self._on_bar
        self.metronome.start_song_flow(expanded)
        self.start_button.config(text="Pause", command=self._pause_metronome)
        self._show_now_playing(self.current_song.name)
        self._wait_for_song_end(gen)

    def _practice_section(self):
        """Play the selected section on loop indefinitely."""
        if not self.current_song:
            messagebox.showwarning("Warning", "No song loaded")
            return
        selection = self.section_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a section to practice")
            return
        index = selection[0]
        section = self.current_song.sections[index]
        self._start_practice(section)

    def _start_practice(self, section):
        """Internal: start looping a single section in practice mode."""
        self._setlist_active = False
        self._song_play_active = True
        self._practice_section_obj = section
        self._setlist_generation += 1
        gen = self._setlist_generation

        self.metronome.stop()
        self._loop_in_index = None
        self._loop_out_index = None
        # Infinite loop: loop_start=0, loop_end=0 on a single-section list
        self.metronome.loop_start = 0
        self.metronome.loop_end = 0

        self._apply_playback_settings()
        self.metronome.on_count_in = self._on_count_in
        self.metronome.on_bar = self._on_bar
        self.metronome.start_song_flow([section])
        self.start_button.config(text="Pause", command=self._pause_metronome)
        self._show_now_playing(f"{section.name} (Practice)")
        self._wait_for_song_end(gen)

    def _wait_for_song_end(self, gen):
        """Poll until the single-song finishes, then hide the Now Playing panel."""
        if gen != self._setlist_generation or not self._song_play_active:
            return
        if self.metronome.is_running:
            self.root.after(100, lambda: self._wait_for_song_end(gen))
        else:
            self._song_play_active = False
            self._practice_section_obj = None
            self.metronome.on_count_in = None
            self.metronome.on_bar = None
            self._hide_now_playing()
            self.start_button.config(text="Start", command=self._start_metronome)

    def _play_setlist(self):
        """Play through the entire setlist."""
        if not self.current_setlist or not self.current_setlist.entries:
            messagebox.showwarning("Warning", "No setlist loaded")
            return

        # Stop any currently running free metronome or song before starting
        self.metronome.stop()
        self._song_play_active = False

        self._setlist_active = True
        self._shuffle_enabled = False
        self._shuffle_order = list(range(len(self.current_setlist.entries)))
        self.shuffle_btn.config(text="Shuffle: Off")
        self._loop_in_index = None
        self._loop_out_index = None
        self.metronome.loop_start = None
        self.metronome.loop_end = None
        self._play_next_song(0)

    def _stop_metronome(self):
        """Stop the metronome and cancel any active song or setlist playback."""
        self._setlist_active = False
        self._song_play_active = False
        self._practice_section_obj = None
        self.metronome.stop()
        self.metronome.on_count_in = None
        self.metronome.on_bar = None
        self._hide_now_playing()
        self.start_button.config(text="Start", command=self._start_metronome)

    def _start_metronome(self):
        """Start the metronome with current settings."""
        self.metronome.on_count_in = None  # free play shows no Now Playing panel
        self.metronome.on_bar = None
        try:
            self.metronome.timer_duration = float(self.timer_entry.get())
        except ValueError:
            self.metronome.timer_duration = 0
            
        try:
            self.metronome.beats_per_bar = int(self.beats_entry.get())
            self.metronome.subdivisions = self._get_subdiv_value()
            self.metronome.tempo_change_step = int(self.step_entry.get())
            self.metronome.tempo_change_interval = int(self.interval_entry.get())
            self.metronome.count_in_bars = int(self.count_in_bars_spin.get())
        except ValueError:
            pass
            
        self.metronome.start()
        self.start_button.config(text="Pause", command=self._pause_metronome)

    def _pause_metronome(self):
        """Pause playback without resetting position."""
        self.metronome.pause()
        self.start_button.config(text="Resume", command=self._resume_metronome)

    def _resume_metronome(self):
        """Resume from the paused position."""
        self.metronome.resume()
        self.start_button.config(text="Pause", command=self._pause_metronome)

    def _update_bpm_display(self, *args):
        """Sync the BPM entry widget with the current IntVar value."""
        val = str(self.metronome.bpm.get())
        if self.bpm_display.get() != val:
            self.bpm_display.delete(0, tk.END)
            self.bpm_display.insert(0, val)

    def _on_bpm_entry(self, event=None):
        """Apply a value typed into the BPM entry field."""
        try:
            val = int(self.bpm_display.get())
            val = max(MIN_BPM, min(MAX_BPM, val))
            self.metronome.bpm.set(val)
        except ValueError:
            self._update_bpm_display()  # revert to current valid value

    # ------------------------------------------------------------------
    # Time signature + subdivision helpers
    # ------------------------------------------------------------------

    def _subdiv_label(self, n):
        """Return the labeled combobox string for subdivision number n."""
        if 1 <= n <= len(SUBDIV_OPTIONS):
            return SUBDIV_OPTIONS[n - 1]
        return str(n)

    def _get_subdiv_value(self):
        """Extract the numeric subdivision value from the combobox."""
        try:
            return int(self.subdiv_entry.get().split(' ')[0])
        except (ValueError, IndexError):
            return DEFAULT_SUBDIVISIONS

    def _pattern_display_text(self, pattern):
        """Convert a beat pattern list to a readable symbol string."""
        symbols = {'S': '●', 'M': '◐', 'W': '○'}
        return '  '.join(symbols.get(b, '○') for b in pattern)

    def _rebuild_pattern_buttons(self):
        """Recreate the accent pattern buttons to match the current beat pattern."""
        for btn in self.pattern_buttons:
            btn.destroy()
        self.pattern_buttons.clear()
        symbols = {'S': '●', 'M': '◐', 'W': '○'}
        for i, level in enumerate(self.metronome.beat_pattern):
            btn = ttk.Button(
                self.pattern_frame,
                text=symbols.get(level, '○'),
                width=2,
                command=lambda idx=i: self._cycle_pattern_beat(idx)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.pattern_buttons.append(btn)

    def _cycle_pattern_beat(self, index):
        """Cycle one beat's accent level: S → M → W → S."""
        cycle = {'S': 'M', 'M': 'W', 'W': 'S'}
        if index < len(self.metronome.beat_pattern):
            self.metronome.beat_pattern[index] = cycle[self.metronome.beat_pattern[index]]
            self._update_pattern_display()

    def _update_pattern_display(self):
        """Refresh the accent pattern buttons to match the current beat pattern."""
        if not hasattr(self, 'pattern_buttons'):
            return
        symbols = {'S': '●', 'M': '◐', 'W': '○'}
        pattern = self.metronome.beat_pattern
        if len(self.pattern_buttons) != len(pattern):
            self._rebuild_pattern_buttons()
            return
        for i, btn in enumerate(self.pattern_buttons):
            btn.config(text=symbols.get(pattern[i], '○'))

    def _apply_time_sig(self, beats, denominator, pattern):
        """Apply a time signature preset — updates display, entry, metronome, and pattern."""
        self._timesig_denominator = denominator
        self.beats_entry.delete(0, tk.END)
        self.beats_entry.insert(0, str(beats))
        self.metronome.beats_per_bar = beats
        self.metronome.beat_pattern = pattern
        self.timesig_label.config(text=f"{beats} / {denominator}")
        self._update_pattern_display()

    def _on_beats_entry(self, event=None):
        """Update display and metronome when beats entry is edited manually."""
        try:
            beats = int(self.beats_entry.get())
            if beats > 0:
                self.metronome.beats_per_bar = beats
                self.timesig_label.config(text=f"{beats} / {self._timesig_denominator}")
                # Reset to simple beat-1-only pattern for custom values
                self.metronome.beat_pattern = ['S'] + ['W'] * (beats - 1)
                self._update_pattern_display()
        except ValueError:
            pass

    def _on_subdiv_changed(self, event=None):
        """Sync metronome subdivisions when combobox selection changes.

        During free play we stop/restart so tick_count resets cleanly.
        During song or setlist flow we only update the value — stopping would
        wipe the section list, and the play loop reads subdivisions each tick
        so the new value takes effect naturally.
        """
        new_val = self._get_subdiv_value()
        if self.metronome.is_running and not self._song_play_active and not self._setlist_active:
            self.metronome.stop()
            self.metronome.subdivisions = new_val
            self.metronome.start()
            self.start_button.config(text="Pause", command=self._pause_metronome)
        else:
            self.metronome.subdivisions = new_val

    def _update_window_title(self):
        """Reflect current song name and dirty state in the window title."""
        if self.current_song:
            dirty = " *" if self._song_dirty else ""
            self.root.title(f"Metronome — {self.current_song.name}{dirty}")
        else:
            self.root.title("Metronome")

    def _on_count_in_toggle(self):
        """Enable or disable the bars spinbox depending on the count-in checkbox."""
        state = 'normal' if self.metronome.count_in_enabled.get() else 'disabled'
        self.count_in_bars_spin.config(state=state)

    def _on_humanize_change(self, value=None):
        """Sync humanize slider and direction to metronome and update label."""
        val = self.humanize_var.get()
        self.metronome.humanize = val
        self.metronome.humanize_direction = self.humanize_direction_var.get()
        self.humanize_label.config(text=f"{int(val)} ms")

    def _on_swing_toggle(self):
        """When swing is enabled, auto-set subdivisions to Eighth notes."""
        if self.metronome.swing_enabled.get():
            self.subdiv_entry.set(self._subdiv_label(2))
            self.metronome.subdivisions = 2

    def _on_tap_key(self, event=None):
        """T key shortcut for tap tempo — ignored when an entry widget has focus."""
        if isinstance(self.root.focus_get(), (ttk.Entry, tk.Entry)):
            return
        self._tap_tempo()

    def _tap_tempo(self):
        """Record a tap and update BPM from average tap interval."""
        now = time.time()
        # Reset after 3 beat-lengths of silence (min 2 s) so slow tempos work correctly
        current_bpm = max(self.metronome.bpm.get(), 1)
        reset_threshold = max(2.0, 60 / current_bpm * 3)
        if self._tap_times and (now - self._tap_times[-1]) > reset_threshold:
            self._tap_times = []
        self._tap_times.append(now)
        if len(self._tap_times) >= 2:
            intervals = [
                self._tap_times[i + 1] - self._tap_times[i]
                for i in range(len(self._tap_times) - 1)
            ]
            bpm = round(60 / (sum(intervals) / len(intervals)))
            self.metronome.bpm.set(max(MIN_BPM, min(MAX_BPM, bpm)))
        self.root.after(0, lambda: self._flash_beat_color('#44AAFF', 80))

    def _nudge_bpm_up(self, event=None):
        """Increase BPM by 1 (keyboard shortcut)."""
        if isinstance(self.root.focus_get(), (ttk.Entry, tk.Entry)):
            return
        self.metronome.bpm.set(min(MAX_BPM, self.metronome.bpm.get() + 1))

    def _nudge_bpm_down(self, event=None):
        """Decrease BPM by 1 (keyboard shortcut)."""
        if isinstance(self.root.focus_get(), (ttk.Entry, tk.Entry)):
            return
        self.metronome.bpm.set(max(MIN_BPM, self.metronome.bpm.get() - 1))

    def _toggle_start_stop(self, event=None):
        """Space bar: start → pause → resume cycle; ignores events when an Entry has focus."""
        if isinstance(self.root.focus_get(), (ttk.Entry, tk.Entry)):
            return
        if self.metronome.is_running:
            self._pause_metronome()
        elif self.metronome._paused:
            self._resume_metronome()
        else:
            self._start_metronome()

    def _on_beat(self, is_accented):
        """Called from the metronome thread on each beat tick."""
        self.root.after(0, lambda: self._flash_beat(is_accented))

    def _flash_beat_color(self, color, duration_ms):
        """Flash the beat indicator to a given color for duration_ms milliseconds."""
        self.beat_indicator.config(bg=color)
        self.root.after(duration_ms, lambda: self.beat_indicator.config(bg='#333333'))

    def _flash_beat(self, is_accented):
        """Flash the beat indicator canvas."""
        color = '#FF4444' if is_accented else '#44BB44'
        # Flash for ≈40% of a beat duration, capped so it's always visible
        beat_ms = round(60_000 / max(self.metronome.bpm.get(), 1))
        flash_ms = max(50, min(200, beat_ms * 2 // 5))
        self._flash_beat_color(color, flash_ms)

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------

    def _save_settings(self):
        """Save current settings to JSON file."""
        try:
            settings = {
                'bpm': self.metronome.bpm.get(),
                'beats_per_bar': self.beats_entry.get(),
                'subdivisions': self._get_subdiv_value(),
                'timesig_denominator': self._timesig_denominator,
                'timer_duration': self.timer_entry.get(),
                'tempo_change_mode': self.metronome.tempo_change_mode.get(),
                'tempo_change_step': self.step_entry.get(),
                'tempo_change_interval': self.interval_entry.get(),
                'count_in_enabled': self.metronome.count_in_enabled.get(),
                'count_in_bars': self.count_in_bars_spin.get(),
                'swing_enabled': self.metronome.swing_enabled.get(),
                'accents_enabled': self.metronome.accents_enabled.get(),
                'accented_sample': self.sound_manager.accented_sample_var.get(),
                'regular_sample': self.sound_manager.regular_sample_var.get(),
                'countin_sample': self.sound_manager.countin_sample_var.get(),
                'accented_volume': self.sound_manager.accented_volume.get(),
                'regular_volume': self.sound_manager.regular_volume.get(),
                'countin_volume': self.sound_manager.countin_volume.get(),
                'humanize': self.humanize_var.get(),
                'humanize_direction': self.humanize_direction_var.get(),
                'fade_in_bars': self.fadein_var.get(),
                'recent_songs': self._recent_songs,
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass  # Never crash on save failure

    def _load_settings(self):
        """Load settings from JSON file if it exists."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, 'r') as f:
                s = json.load(f)

            # BPM is driven by an IntVar bound to the slider — just set the var
            if 'bpm' in s:
                self.metronome.bpm.set(int(s['bpm']))
            if 'timesig_denominator' in s:
                self._timesig_denominator = int(s['timesig_denominator'])
            if 'beats_per_bar' in s:
                beats = int(s['beats_per_bar'])
                self.beats_entry.delete(0, tk.END)
                self.beats_entry.insert(0, str(beats))
                self.timesig_label.config(
                    text=f"{beats} / {self._timesig_denominator}"
                )
            if 'subdivisions' in s:
                self.subdiv_entry.set(self._subdiv_label(int(s['subdivisions'])))
            if 'timer_duration' in s:
                self.timer_entry.delete(0, tk.END)
                self.timer_entry.insert(0, str(s['timer_duration']))
            if 'tempo_change_mode' in s:
                self.metronome.tempo_change_mode.set(s['tempo_change_mode'])
            if 'tempo_change_step' in s:
                self.step_entry.delete(0, tk.END)
                self.step_entry.insert(0, str(s['tempo_change_step']))
            if 'tempo_change_interval' in s:
                self.interval_entry.delete(0, tk.END)
                self.interval_entry.insert(0, str(s['tempo_change_interval']))
            if 'count_in_enabled' in s:
                self.metronome.count_in_enabled.set(bool(s['count_in_enabled']))
                self._on_count_in_toggle()
            if 'count_in_bars' in s:
                self.count_in_bars_spin.delete(0, tk.END)
                self.count_in_bars_spin.insert(0, str(s['count_in_bars']))
            if 'swing_enabled' in s:
                self.metronome.swing_enabled.set(bool(s['swing_enabled']))
            if 'accents_enabled' in s:
                self.metronome.accents_enabled.set(bool(s['accents_enabled']))
            if 'accented_sample' in s:
                self.sound_manager.accented_sample_var.set(s['accented_sample'])
            if 'regular_sample' in s:
                self.sound_manager.regular_sample_var.set(s['regular_sample'])
            if 'countin_sample' in s:
                self.sound_manager.countin_sample_var.set(s['countin_sample'])
            if 'accented_volume' in s:
                self.sound_manager.accented_volume.set(float(s['accented_volume']))
            if 'regular_volume' in s:
                self.sound_manager.regular_volume.set(float(s['regular_volume']))
            if 'countin_volume' in s:
                self.sound_manager.countin_volume.set(float(s['countin_volume']))
            if 'humanize' in s:
                self.humanize_var.set(float(s['humanize']))
                self.metronome.humanize = float(s['humanize'])
                self.humanize_label.config(text=f"{int(float(s['humanize']))} ms")
            if 'humanize_direction' in s:
                self.humanize_direction_var.set(s['humanize_direction'])
                self.metronome.humanize_direction = s['humanize_direction']
            if 'fade_in_bars' in s:
                self.fadein_var.set(int(s['fade_in_bars']))
                self.metronome.fade_in_bars = int(s['fade_in_bars'])
            if 'recent_songs' in s:
                self._recent_songs = s['recent_songs'][:5]
                self.recent_songs_combo['values'] = self._recent_songs
                if self._recent_songs:
                    self.recent_songs_combo.set(self._recent_songs[0])
        except Exception:
            pass  # Bad settings file — just ignore it

    def _on_close(self):
        """Warn about unsaved changes, save settings, then close."""
        if self._song_dirty:
            if not messagebox.askyesno(
                "Unsaved Changes",
                "The current song has unsaved changes. Close anyway?"
            ):
                return
        if self._setlist_dirty:
            if not messagebox.askyesno(
                "Unsaved Changes",
                "The current setlist has unsaved changes. Close anyway?"
            ):
                return
        self._save_settings()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Help tab
    # ------------------------------------------------------------------

    def _create_help_tab(self):
        """Create the Help tab with user documentation."""
        help_tab = ttk.Frame(self.notebook)
        self.notebook.add(help_tab, text='Help')

        self._help_text = scrolledtext.ScrolledText(
            help_tab, wrap=tk.WORD, state='disabled',
            font=('TkDefaultFont', 10), relief='flat'
        )
        self._help_text.pack(fill=tk.BOTH, expand=True, padx=PADDING, pady=PADDING)
        text = self._help_text

        help_content = """\
METRONOME — QUICK GUIDE
=======================

BASIC METRONOME (Basic tab)
────────────────────────────
• BPM — beats per minute.  Type a value or use the +/- buttons.
• Beats per Bar — how many beats in one bar (e.g. 4 for 4/4 time).
• Subdivisions — ticks per beat (1 = quarter notes, 2 = eighth notes, 4 = sixteenth notes).
• Swing — when subdivisions = 2, the first tick of each beat is lengthened for a swing feel.
• Count-in — tick the checkbox to play a count-in before the first beat.
  Set Bars (1–8) to control how many bars the count-in lasts.
• Timer — automatically stops the metronome after the given number of seconds (0 = run forever).
• Tap Tempo — tap the button repeatedly to set the BPM by feel.
  The beat indicator flashes cyan on each tap so you can see it landing.

Press START to begin and STOP to end.  The coloured circle flashes red on beat 1, green on other beats.


TEMPO CHANGE MODE (Basic tab)
──────────────────────────────
• Speed Up / Slow Down — automatically raises or lowers the BPM every N bars.
• Step — how many BPM to add or subtract.
• Every (bars) — how often the change happens.
Example: Step=5, Every=4 → BPM increases by 5 every 4 bars.


SONGS & SECTIONS (Song Flow tab)
─────────────────────────────────
A Song is a sequence of Sections, each with its own BPM, time signature, and length.

Creating a song:
  1. Type a name in "Song Name" and press Save Song.
  2. Press Add Section, fill in the details, and press OK.
  3. Repeat for each section (Intro, Verse, Chorus, Bridge, Outro, etc.).
  4. Use Move Up / Move Down to reorder sections.
  5. Press Save Song again to keep your changes.

Section fields:
  • Name — label shown in the Now Playing panel.
  • Bars — how many bars this section plays before moving to the next.
  • BPM — tempo for this section.
  • Beats per Bar — e.g. 4 for 4/4, 3 for 3/4.
  • Subdivisions — ticks per beat (same as on the Basic tab).
  • Swing — enable swing feel for this section.
  • Count-in before this section — when ticked, a one-bar count-in plays every time
    playback enters this section (useful for a chorus or bridge that needs a cue).
  • Repeat — play this section N times before moving on.

Tip: When you press Add Section, the previous section's settings are pre-filled as a starting point.

Play Song button — plays the song immediately and shows the Now Playing panel (no setlist needed).


PRACTICE MODE (Song Flow tab)
──────────────────────────────
Select a single section in the list and press Practice.  That section loops indefinitely
with a one-bar count-in before each repeat so you can drill it at tempo.
Press Stop (or the transport Stop button) to end practice mode.


RECENT SONGS (Song Flow tab)
─────────────────────────────
The last 5 songs you saved or loaded are listed in the Recent drop-down.
Pick a name and press Load Recent to open it instantly — no need to use the full Load Song dialog.
The list is saved between sessions.


SETLISTS (Song Flow tab)
──────────────────────────
A Setlist is an ordered list of songs that play back-to-back.

  1. Load or create each song you need.
  2. Press "Add Song" to append the current song.
  3. Select an entry and use Edit Delay to set seconds of silence after that song ends.
  4. Press Play Setlist to start.

Play Setlist opens the Now Playing panel and switches to the Basic tab so you can see
the beat indicator while following the set.

Export to Text — saves the full setlist (song names, section details, BPMs, bar counts)
to a plain .txt file you can print or share.


NOW PLAYING PANEL (appears when playing a song or setlist)
───────────────────────────────────────────────────────────
Displays:
  • Song title and (for setlists) position — e.g. "Song 2 of 5"
  • Current section name, BPM, bars remaining, and next section

Transport controls:
  • Restart — restarts the current song from the beginning.
  • Skip — jumps to the next song in the setlist (no effect in single-song mode).
  • Shuffle — randomises the remaining setlist order on each press.


LOOP PRACTICE
─────────────
Loop lets you repeat a range of sections indefinitely — ideal for drilling difficult passages.

  1. While a song or setlist is playing, navigate to the section you want to start looping.
  2. Press Set Loop In — the button turns orange and the panel prompts you to set the end.
  3. When the section you want to end on begins, press Set Loop Out — both buttons turn green.
  4. After the loop-out section finishes, a one-bar count-in plays and the loop-in section repeats.
  5. Press Clear Loop to remove the loop and continue playing normally.

Notes:
  • Loop In marks bar 1 of the chosen section.
  • Loop Out plays the section all the way to its end before looping back.
  • Loops are cleared automatically when you restart or skip to another song.


PLAYBACK FEEL (Settings tab)
──────────────────────────────
• Humanize — adds a small random timing variation to each tick, giving the click
  a more natural, human feel.  Set to 0 for a perfectly rigid grid.
  Recommended range: 5–20 ms.  Values above 30 ms become noticeably sloppy.
  Direction controls which way the variation goes:
    Push (play late)  — each tick lands slightly after the grid
    Pull (play early) — each tick lands slightly before the grid

• Fade-in (bars) — ramps the click volume from silence up to full over the first N bars
  of playback.  Useful for easing in at the start of a song.  Set to 0 to disable.

Both settings are saved between sessions and applied whenever you start or play a song.


SAMPLES & VOLUMES (Settings tab)
──────────────────────────────────
• Accented Beat — sound played on beat 1 of each bar.
• Regular Beat — sound played on all other beats/subdivisions.
• Count-In — sound played during count-in bars.
• Volume sliders control the level of each sound independently.
• Upload Custom Sample — copies a WAV file into the Samples folder and makes it available.


KEYBOARD SHORTCUTS
──────────────────
  Space — Start / Pause / Resume the metronome
  T     — Tap Tempo
  +  or  ↑ — Increase BPM by 1
  -  or  ↓ — Decrease BPM by 1
"""

        text.config(state='normal')
        text.insert('1.0', help_content)
        text.config(state='disabled')

    def _style_tk_widgets(self):
        """Apply current ttk theme colors to non-themed tk widgets (Listbox, ScrolledText)."""
        style = ttk.Style()
        bg = style.lookup('TFrame', 'background') or '#2b2b2b'
        fg = style.lookup('TLabel', 'foreground') or '#ffffff'
        for lb in (self.section_list, self.setlist_list):
            lb.configure(
                bg=bg, fg=fg,
                selectbackground='#0078d4',
                selectforeground='#ffffff',
                borderwidth=0,
                highlightthickness=0,
            )
        if hasattr(self, '_help_text'):
            self._help_text.configure(bg=bg, fg=fg, insertbackground=fg)

    def _preview_sample(self, sample_name, volume):
        """Play a sample once for preview."""
        self.sound_manager.play_sample(sample_name, volume)

    def _duplicate_section(self):
        """Duplicate the selected section and insert the copy below it."""
        if not self.current_song:
            return
        selection = self.section_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a section to duplicate")
            return
        index = selection[0]
        original = self.current_song.sections[index]
        import copy
        dup = copy.copy(original)
        dup.name = f"{original.name} (Copy)"
        self.current_song.sections.insert(index + 1, dup)
        self.section_list.insert(index + 1, self._section_list_text(dup))
        self.section_list.selection_set(index + 1)
        self._song_dirty = True
        self._update_window_title()

    def _duplicate_song(self):
        """Save a copy of the current song under a new name."""
        if not self.current_song:
            messagebox.showwarning("Warning", "No song loaded")
            return
        import copy
        dup = copy.deepcopy(self.current_song)
        dup.name = f"{self.current_song.name} (Copy)"
        try:
            self.song_manager.save_song(dup, dup.name)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        messagebox.showinfo("Duplicated", f"Saved as '{dup.name}'")

    def _rebuild_sample_menus(self):
        """Rebuild all three sample OptionMenus after the available samples list changes."""
        samples = self.sound_manager.get_available_samples()
        for menu_widget, var in (
            (self.accented_sample_menu, self.sound_manager.accented_sample_var),
            (self.regular_sample_menu,  self.sound_manager.regular_sample_var),
            (self.countin_sample_menu,  self.sound_manager.countin_sample_var),
        ):
            menu = menu_widget['menu']
            menu.delete(0, 'end')
            for sample in samples:
                menu.add_command(
                    label=sample,
                    command=lambda v=var, s=sample: v.set(s)
                )

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
                
                # Rebuild sample OptionMenus with the new sample list
                self._rebuild_sample_menus()
                
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
        
        # Editable BPM entry — synced both ways with the IntVar
        self.bpm_display = ttk.Entry(bpm_frame, width=5, justify='center')
        self.bpm_display.insert(0, str(DEFAULT_BPM))
        self.bpm_display.pack(side=tk.LEFT, padx=PADDING)
        self.bpm_display.bind('<Return>', self._on_bpm_entry)
        self.bpm_display.bind('<FocusOut>', self._on_bpm_entry)

        # Keep entry in sync when slider or IntVar changes
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

        # ── Time Signature ──────────────────────────────────────────────
        tsig_frame = ttk.LabelFrame(self.timing_frame, text="Time Signature", padding=PADDING)
        tsig_frame.pack(fill=tk.X, pady=PADDING)

        # Large display label
        self.timesig_label = ttk.Label(
            tsig_frame, text=f"{DEFAULT_BEATS_PER_BAR} / 4",
            font=('TkDefaultFont', 22, 'bold'), anchor='center'
        )
        self.timesig_label.pack(fill=tk.X, pady=(PADDING, 2))

        # Preset button rows
        for row_presets in TIME_SIG_PRESETS:
            row = ttk.Frame(tsig_frame)
            row.pack(pady=2)
            for label, beats, denom, pattern in row_presets:
                ttk.Button(
                    row, text=label, width=5,
                    command=lambda b=beats, d=denom, p=pattern: self._apply_time_sig(b, d, p)
                ).pack(side=tk.LEFT, padx=2)

        # Pattern editor — clickable buttons cycle S → M → W → S
        ttk.Label(
            tsig_frame, text="Click a beat to cycle: ● Strong  ◐ Medium  ○ Weak",
            font=('TkDefaultFont', 8), foreground='gray'
        ).pack(pady=(4, 0))
        self.pattern_frame = ttk.Frame(tsig_frame)
        self.pattern_frame.pack(pady=(2, 0))
        self.pattern_buttons = []
        self._rebuild_pattern_buttons()

        # Custom beats entry
        custom_row = ttk.Frame(tsig_frame)
        custom_row.pack(fill=tk.X, pady=(PADDING, 0))
        ttk.Label(custom_row, text="Custom beats/bar:").pack(side=tk.LEFT)
        self.beats_entry = ttk.Entry(custom_row, width=5, justify='center')
        self.beats_entry.insert(0, str(DEFAULT_BEATS_PER_BAR))
        self.beats_entry.pack(side=tk.LEFT, padx=PADDING)
        self.beats_entry.bind('<Return>', self._on_beats_entry)
        self.beats_entry.bind('<FocusOut>', self._on_beats_entry)

        # ── Subdivisions per Beat ────────────────────────────────────────
        ttk.Label(self.timing_frame, text="Subdivisions per Beat:").pack(pady=PADDING)
        self.subdiv_entry = ttk.Combobox(
            self.timing_frame,
            values=SUBDIV_OPTIONS,
            state='readonly',
        )
        self.subdiv_entry.set(SUBDIV_OPTIONS[DEFAULT_SUBDIVISIONS - 1])
        self.subdiv_entry.pack(fill=tk.X, pady=PADDING)
        self.subdiv_entry.bind('<<ComboboxSelected>>', self._on_subdiv_changed)

        # Swing Toggle
        self.swing_check = ttk.Checkbutton(
            self.timing_frame,
            text="Enable Swing (requires Eighth notes subdivision)",
            variable=self.metronome.swing_enabled,
            command=self._on_swing_toggle
        )
        self.swing_check.pack(pady=PADDING)

        # Enable Accents toggle
        ttk.Checkbutton(
            self.timing_frame,
            text="Enable Accents",
            variable=self.metronome.accents_enabled,
        ).pack(pady=PADDING)

        # Count-in enable + bars
        countin_frame = ttk.Frame(self.timing_frame)
        countin_frame.pack(fill=tk.X, pady=PADDING)
        ttk.Checkbutton(
            countin_frame,
            text="Count-in",
            variable=self.metronome.count_in_enabled,
            command=self._on_count_in_toggle,
        ).pack(side=tk.LEFT)
        ttk.Label(countin_frame, text="Bars:").pack(side=tk.LEFT, padx=(PADDING, 0))
        self.count_in_bars_spin = ttk.Spinbox(
            countin_frame, from_=1, to=8, width=5,
            textvariable=tk.IntVar(value=DEFAULT_COUNT_IN_BARS)
        )
        self.count_in_bars_spin.pack(side=tk.LEFT, padx=PADDING)
        # Reflect initial state
        self._on_count_in_toggle()

    def _check_setlist_dirty(self):
        """Return True if safe to discard setlist (not dirty or user confirmed)."""
        if self._setlist_dirty:
            return messagebox.askyesno(
                "Unsaved Changes",
                "The current setlist has unsaved changes. Discard them?"
            )
        return True

    def _new_setlist(self):
        """Create a new setlist."""
        if not self._check_setlist_dirty():
            return
        name = self.setlist_name_entry.get() or "Untitled"
        self.current_setlist = Setlist(name=name)
        self.setlist_list.delete(0, tk.END)
        self.setlist_name_entry.delete(0, tk.END)
        self.setlist_name_entry.insert(0, name)
        self._setlist_dirty = False

        # Open song selection dialog to seed the new setlist
        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            song = dialog.result
            delay_dialog = DelayDialog(self.root)
            if delay_dialog.result is not None:
                self.current_setlist.add_entry(song, delay_after=delay_dialog.result)
                self.setlist_list.insert(
                    tk.END, f"{song.name} (Delay: {delay_dialog.result}s)"
                )
                self._setlist_dirty = True

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
        try:
            self.setlist_manager.save_setlist(self.current_setlist)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save setlist: {e}")
            return
        self._setlist_dirty = False
        messagebox.showinfo("Success", "Setlist saved successfully")

    def _load_setlist(self):
        """Load a setlist from file."""
        if not self._check_setlist_dirty():
            return

        dialog = LoadSetlistDialog(self.root, self.setlist_manager, self.song_manager)
        if dialog.result:
            self.current_setlist = dialog.result
            self.setlist_name_entry.delete(0, tk.END)
            self.setlist_name_entry.insert(0, self.current_setlist.name)
            self.setlist_list.delete(0, tk.END)
            for entry in self.current_setlist.entries:
                self.setlist_list.insert(
                    tk.END, f"{entry.song.name} (Delay: {entry.delay_after}s)"
                )
            self._setlist_dirty = False

    def _export_setlist(self):
        """Export the current setlist to a formatted .txt file."""
        if not self.current_setlist:
            messagebox.showwarning("Warning", "No setlist loaded")
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.txt',
            filetypes=[('Text files', '*.txt')],
            initialfile=f"{self.current_setlist.name}.txt"
        )
        if not path:
            return
        lines = [f"SETLIST: {self.current_setlist.name}", "=" * 40, ""]
        for i, entry in enumerate(self.current_setlist.entries, 1):
            lines.append(f"{i}. {entry.song.name}")
            for sec in entry.song.sections:
                repeat = f"  \xd7{sec.repeat}" if sec.repeat > 1 else ""
                lines.append(f"     {sec.name}  \u2014  {sec.bpm} BPM  \u2014  {sec.bars} bars{repeat}")
            if entry.delay_after:
                lines.append(f"     [Delay: {entry.delay_after}s]")
            lines.append("")
        try:
            with open(path, 'w') as f:
                f.write('\n'.join(lines))
            messagebox.showinfo("Exported", f"Setlist exported to {os.path.basename(path)}")
        except OSError as e:
            messagebox.showerror("Error", f"Could not export: {e}")

    def _add_song_to_setlist(self):
        """Add a song to setlist."""
        if not self.current_setlist:
            self._new_setlist()
            return

        dialog = LoadSongDialog(self.root, self.song_manager)
        if dialog.result:
            song = dialog.result
            delay_dialog = DelayDialog(self.root)
            if delay_dialog.result is not None:
                self.current_setlist.add_entry(song, delay_after=delay_dialog.result)
                self.setlist_list.insert(
                    tk.END, f"{song.name} (Delay: {delay_dialog.result}s)"
                )
                self._setlist_dirty = True

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
                index, f"{entry.song.name} (Delay: {dialog.result}s)"
            )
            self._setlist_dirty = True

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
            self._setlist_dirty = True

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
        self._setlist_dirty = True

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
        self._setlist_dirty = True


 