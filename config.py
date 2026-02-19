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
DEFAULT_COUNTIN_SAMPLE = "hihat-808.wav"
DEFAULT_ACCENTED_SAMPLE = "kick-808.wav"
DEFAULT_REGULAR_SAMPLE = "hihat-808.wav"

# Volume defaults
DEFAULT_ACCENTED_VOLUME = 1.0
DEFAULT_REGULAR_VOLUME = 0.8
DEFAULT_COUNTIN_VOLUME = 0.6

# UI settings
PADDING = 5
BUTTON_PADDING = 5
FRAME_PADDING = 10
WINDOW_PADDING = 20

# Samples folder path
SAMPLES_FOLDER = os.path.join(os.path.dirname(__file__), "Samples") 