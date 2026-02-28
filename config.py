"""Configuration settings for the metronome application."""

import os

# Default settings
DEFAULT_BPM = 120
DEFAULT_BEATS_PER_BAR = 4
DEFAULT_SUBDIVISIONS = 1
DEFAULT_TIMER_DURATION = 0  # in seconds; 0 means run indefinitely
DEFAULT_TEMPO_CHANGE_STEP = 5
DEFAULT_TEMPO_CHANGE_INTERVAL = 4
DEFAULT_COUNT_IN_BARS = 2

# BPM limits
MIN_BPM = 20
MAX_BPM = 250

# Default sample assignments
DEFAULT_ACCENTED_SAMPLE = "click-high.wav"   # beat 1 — high-pitched click
DEFAULT_REGULAR_SAMPLE  = "click-low.wav"    # other beats — lower-pitched click
DEFAULT_COUNTIN_SAMPLE  = "click-mid.wav"    # count-in — mid-pitched click

# Volume defaults
DEFAULT_ACCENTED_VOLUME = 1.0
DEFAULT_REGULAR_VOLUME = 0.8
DEFAULT_COUNTIN_VOLUME = 0.6

# UI settings
PADDING = 5
BUTTON_PADDING = 5
FRAME_PADDING = 10
WINDOW_PADDING = 20

# Samples folder path — use abspath so it works regardless of launch directory
SAMPLES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Samples")