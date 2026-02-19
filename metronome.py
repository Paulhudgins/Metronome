"""Core metronome functionality."""

import time
import threading
import tkinter as tk
from config import (
    DEFAULT_BPM,
    DEFAULT_BEATS_PER_BAR,
    DEFAULT_SUBDIVISIONS,
    DEFAULT_TIMER_DURATION,
    DEFAULT_TEMPO_CHANGE_STEP,
    DEFAULT_TEMPO_CHANGE_INTERVAL,
    DEFAULT_COUNT_IN_BARS,
    MIN_BPM,
    MAX_BPM
)
from song_section import SongSection


class Metronome:
    def __init__(self, sound_manager):
        """Initialize the metronome.

        Args:
            sound_manager (SoundManager): Sound manager instance
        """
        self.sound_manager = sound_manager
        self.thread = None
        self._running = threading.Event()
        self.on_beat = None  # Optional callback: on_beat(is_accented)

        # Default settings
        self.bpm = tk.IntVar(value=DEFAULT_BPM)
        self.beats_per_bar = DEFAULT_BEATS_PER_BAR
        self.subdivisions = DEFAULT_SUBDIVISIONS
        self.count_in_enabled = tk.BooleanVar(value=True)
        self.count_in_bars = DEFAULT_COUNT_IN_BARS
        self.tempo_change_mode = tk.StringVar(value="None")
        self.tempo_change_step = DEFAULT_TEMPO_CHANGE_STEP
        self.tempo_change_interval = DEFAULT_TEMPO_CHANGE_INTERVAL
        self.timer_duration = DEFAULT_TIMER_DURATION
        self.swing_enabled = tk.BooleanVar(value=False)

        # Song flow settings
        self.current_section_index = 0
        self.current_section = None
        self.sections = []

    @property
    def is_running(self):
        return self._running.is_set()

    def start(self, start_time=None):
        """Start the metronome.

        Args:
            start_time (float, optional): Start time for timing calculations
        """
        if not self._running.is_set():
            self._running.set()
            self.start_time = start_time or time.time()
            self.next_tick_time = self.start_time
            self.thread = threading.Thread(target=self.play, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the metronome."""
        self._running.clear()
        if self.thread is not None:
            self.thread.join()
            self.thread = None
        self.current_section_index = 0
        self.current_section = None
        self.sections = []

    def start_song_flow(self, sections):
        """Start playing a sequence of sections.

        Args:
            sections (List[SongSection]): List of sections to play
        """
        if not sections:
            return

        self.sections = sections
        self.current_section_index = 0
        self.current_section = sections[0]

        # Update settings for first section
        self.bpm.set(self.current_section.bpm)
        self.beats_per_bar = self.current_section.beats_per_bar
        self.subdivisions = self.current_section.subdivisions
        self.swing_enabled.set(self.current_section.swing_enabled)

        # Start playback
        self.start()

    def play(self):
        """Main playback loop."""
        tick_count = 0
        bar_count = 0

        # Count-In Phase
        if self.count_in_enabled.get():
            for _ in range(self.beats_per_bar * self.count_in_bars):
                self.sound_manager.play_sample(
                    self.sound_manager.default_countin_sample,
                    self.sound_manager.countin_volume.get()
                )
                self.next_tick_time += 60 / self.bpm.get()
                sleep_time = self.next_tick_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
            tick_count = 0

        # Initialize sample values for first measure
        accented_sample_name = self.sound_manager.accented_sample_var.get()
        regular_sample_name = self.sound_manager.regular_sample_var.get()
        accented_volume = self.sound_manager.accented_volume.get()
        regular_volume = self.sound_manager.regular_volume.get()

        while self._running.is_set():
            # Check timer if set
            if (self.timer_duration > 0 and
                    (time.time() - self.start_time) >= self.timer_duration):
                self._running.clear()
                break

            # Check if we need to move to next section
            if self.current_section and bar_count >= self.current_section.bars:
                self.current_section_index += 1
                if self.current_section_index >= len(self.sections):
                    self._running.clear()
                    break

                self.current_section = self.sections[self.current_section_index]
                self.bpm.set(self.current_section.bpm)
                self.beats_per_bar = self.current_section.beats_per_bar
                self.subdivisions = self.current_section.subdivisions
                self.swing_enabled.set(self.current_section.swing_enabled)
                bar_count = 0

            tick_count += 1
            current_beat = (tick_count - 1) // self.subdivisions
            tick_in_beat = (tick_count - 1) % self.subdivisions
            is_accented = tick_in_beat == 0 and current_beat % self.beats_per_bar == 0

            # Update sample values at the start of each measure
            if is_accented:
                accented_sample_name = self.sound_manager.accented_sample_var.get()
                regular_sample_name = self.sound_manager.regular_sample_var.get()
                accented_volume = self.sound_manager.accented_volume.get()
                regular_volume = self.sound_manager.regular_volume.get()

            # Play appropriate sound
            if is_accented:
                self.sound_manager.play_sample(accented_sample_name, accented_volume)
            else:
                self.sound_manager.play_sample(regular_sample_name, regular_volume)

            # Fire beat callback (safe to call from thread via root.after in UI)
            if self.on_beat is not None:
                self.on_beat(is_accented)

            # Handle tempo changes
            if tick_count % (self.beats_per_bar * self.subdivisions) == 0:
                bar_count += 1
                self._handle_tempo_change(bar_count)

            # Calculate and apply delay
            delay = self._calculate_delay(tick_in_beat)
            self.next_tick_time += delay
            sleep_time = self.next_tick_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _handle_tempo_change(self, bar_count):
        """Handle tempo changes at measure boundaries.

        Args:
            bar_count (int): Current bar count
        """
        mode = self.tempo_change_mode.get()
        try:
            step = int(self.tempo_change_step)
            interval = int(self.tempo_change_interval)
        except ValueError:
            step = DEFAULT_TEMPO_CHANGE_STEP
            interval = DEFAULT_TEMPO_CHANGE_INTERVAL

        if mode == "Speed Up" and (bar_count % interval == 0):
            self.bpm.set(min(MAX_BPM, self.bpm.get() + step))
        elif mode == "Slow Down" and (bar_count % interval == 0):
            self.bpm.set(max(MIN_BPM, self.bpm.get() - step))

    def _calculate_delay(self, tick_in_beat):
        """Calculate delay for next tick.

        Args:
            tick_in_beat (int): Current tick position within beat

        Returns:
            float: Delay in seconds
        """
        if self.swing_enabled.get() and self.subdivisions == 2:
            return (60 / self.bpm.get()) * (2/3 if tick_in_beat == 0 else 1/3)
        return 60 / (self.bpm.get() * self.subdivisions)
