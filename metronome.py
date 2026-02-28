"""Core metronome functionality."""

import time
import threading
import random
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
        self.on_bar = None        # callback(section, bars_remaining, next_section)
        self.on_count_in = None   # callback(beats_remaining, total_beats)
        self.loop_start = None    # section index to loop back to (None = no loop)
        self.loop_end = None      # section index that triggers the loop (None = no loop)

        # Timing
        self.start_time = 0.0

        # Playback feel
        self.humanize = 0.0             # max jitter in milliseconds
        self.humanize_direction = 'push'  # 'push' = late, 'pull' = early
        self.fade_in_bars = 0           # 0 = disabled

        # Pause state
        self._paused = False
        self._skip_count_in = False

        # Accent pattern — list of 'S' (strong), 'M' (medium), 'W' (weak) per beat
        self.beat_pattern = ['S', 'W', 'W', 'W']  # default 4/4
        self.accents_enabled = tk.BooleanVar(value=True)

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

    def pause(self):
        """Pause playback, preserving section position."""
        self._paused = True
        self._running.clear()
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    def resume(self):
        """Resume from the start of the current section (no count-in)."""
        if not self._paused:
            return
        self._paused = False
        self._skip_count_in = True
        self._running.set()
        self.start_time = time.time()
        self.next_tick_time = self.start_time
        self.thread = threading.Thread(target=self.play, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the metronome and reset all playback state."""
        self._paused = False
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
        if self.count_in_enabled.get() and not self._skip_count_in:
            count_in_total = self.beats_per_bar * self.count_in_bars
            for beat_i in range(count_in_total):
                if not self._running.is_set():
                    return
                if self.on_count_in is not None:
                    beats_remaining = count_in_total - beat_i
                    self.on_count_in(beats_remaining, count_in_total)
                self.sound_manager.play_sample(
                    self.sound_manager.countin_sample_var.get(),
                    self.sound_manager.countin_volume.get()
                )
                self.next_tick_time += 60 / self.bpm.get()
                sleep_time = self.next_tick_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
            tick_count = 0

        self._skip_count_in = False

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
                do_count_in = False
                if (self.loop_start is not None and self.loop_end is not None
                        and self.current_section_index == self.loop_end):
                    self.current_section_index = self.loop_start
                    do_count_in = True
                else:
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

                if not do_count_in and getattr(self.current_section, 'count_in', False):
                    do_count_in = True

                # Play 1-bar count-in before loop repeat or flagged section
                if do_count_in:
                    for beat_i in range(self.beats_per_bar):
                        if not self._running.is_set():
                            return
                        if self.on_count_in is not None:
                            self.on_count_in(self.beats_per_bar - beat_i, self.beats_per_bar)
                        self.sound_manager.play_sample(
                            self.sound_manager.countin_sample_var.get(),
                            self.sound_manager.countin_volume.get()
                        )
                        self.next_tick_time += 60 / self.bpm.get()
                        sleep_time = self.next_tick_time - time.time()
                        if sleep_time > 0:
                            time.sleep(sleep_time)
                    tick_count = 0  # realign so next tick is the accented downbeat

            tick_count += 1
            current_beat = (tick_count - 1) // self.subdivisions
            tick_in_beat = (tick_count - 1) % self.subdivisions
            beat_in_bar = current_beat % self.beats_per_bar
            is_accented = tick_in_beat == 0 and beat_in_bar == 0

            # Update sample values at the start of each measure
            if is_accented:
                accented_sample_name = self.sound_manager.accented_sample_var.get()
                regular_sample_name = self.sound_manager.regular_sample_var.get()
                accented_volume = self.sound_manager.accented_volume.get()
                regular_volume = self.sound_manager.regular_volume.get()

            # Determine accent level for this tick
            if tick_in_beat == 0 and self.accents_enabled.get() and self.beat_pattern:
                level = self.beat_pattern[beat_in_bar % len(self.beat_pattern)]
            else:
                level = 'W'

            # Compute fade-in volume scale (bar_count = completed bars so far)
            vol_scale = (
                min(1.0, bar_count / max(1, self.fade_in_bars))
                if self.fade_in_bars > 0 else 1.0
            )

            # Play appropriate sound
            if level == 'S':
                self.sound_manager.play_sample(accented_sample_name, accented_volume * vol_scale)
            elif level == 'M':
                self.sound_manager.play_sample(accented_sample_name, accented_volume * 0.6 * vol_scale)
            else:
                self.sound_manager.play_sample(regular_sample_name, regular_volume * vol_scale)

            # Fire beat callback only on musical beats, not on every subdivision tick.
            # is_accented here means "this is beat 1 of the bar" (red flash).
            if tick_in_beat == 0 and self.on_beat is not None:
                self.on_beat(beat_in_bar == 0)

            # Fire bar callback during song flow.
            # bar_count reflects completed bars; this fires on the downbeat of each new bar,
            # so bars_remaining = total - bars_already_completed.
            if is_accented and self.on_bar is not None and self.current_section:
                bars_remaining = self.current_section.bars - bar_count
                next_sec = (self.sections[self.current_section_index + 1]
                            if self.current_section_index + 1 < len(self.sections)
                            else None)
                self.on_bar(self.current_section, bars_remaining, next_sec)

            # Increment bar counter at the end of each complete bar
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
            base = (60 / self.bpm.get()) * (2/3 if tick_in_beat == 0 else 1/3)
        else:
            base = 60 / (self.bpm.get() * self.subdivisions)
        if self.humanize > 0:
            jitter = random.uniform(0, self.humanize) / 1000
            if self.humanize_direction == 'pull':
                jitter = -jitter
            return max(0.001, base + jitter)
        return base
