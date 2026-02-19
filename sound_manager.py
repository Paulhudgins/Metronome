"""Sound management for the metronome application."""

import os
import pygame
import tkinter as tk
from config import (
    DEFAULT_ACCENTED_SAMPLE,
    DEFAULT_REGULAR_SAMPLE,
    DEFAULT_COUNTIN_SAMPLE,
    DEFAULT_ACCENTED_VOLUME,
    DEFAULT_REGULAR_VOLUME,
    DEFAULT_COUNTIN_VOLUME,
    SAMPLES_FOLDER
)


class SoundManager:
    def __init__(self):
        """Initialize the sound manager."""
        pygame.mixer.init()
        
        # Initialize volume controls
        self.accented_volume = tk.DoubleVar(value=DEFAULT_ACCENTED_VOLUME)
        self.regular_volume = tk.DoubleVar(value=DEFAULT_REGULAR_VOLUME)
        self.countin_volume = tk.DoubleVar(value=DEFAULT_COUNTIN_VOLUME)
        
        # Initialize sample variables
        self.accented_sample_var = tk.StringVar(value=DEFAULT_ACCENTED_SAMPLE)
        self.regular_sample_var = tk.StringVar(value=DEFAULT_REGULAR_SAMPLE)
        self.countin_sample_var = tk.StringVar(value=DEFAULT_COUNTIN_SAMPLE)
        
        # Initialize sample storage
        self.samples = {}
        self.default_accented_sample = DEFAULT_ACCENTED_SAMPLE
        self.default_regular_sample = DEFAULT_REGULAR_SAMPLE
        self.default_countin_sample = DEFAULT_COUNTIN_SAMPLE
        
        # Preload all available samples
        self._preload_samples()

    def _preload_samples(self):
        """Preload all available samples."""
        self.samples.clear()
        for sample_name in self.get_available_samples():
            try:
                sample_path = os.path.join(SAMPLES_FOLDER, sample_name)
                if os.path.exists(sample_path):
                    self.samples[sample_name] = pygame.mixer.Sound(sample_path)
            except Exception as e:
                print(f"Error loading sample {sample_name}: {e}")

    def get_available_samples(self):
        """Get list of available sample files.

        Returns:
            List[str]: List of sample filenames
        """
        if not os.path.exists(SAMPLES_FOLDER):
            os.makedirs(SAMPLES_FOLDER)

        samples = []
        for file in os.listdir(SAMPLES_FOLDER):
            if file.endswith(".wav"):
                samples.append(file)
        return sorted(samples)

    def play_sample(self, sample_name, volume=1.0):
        """Play a sample with specified volume.
        
        Args:
            sample_name (str): Name of sample to play
            volume (float): Volume level (0.0 to 1.0)
        """
        if sample_name in self.samples:
            self.samples[sample_name].set_volume(volume)
            self.samples[sample_name].play() 