"""Main entry point for the metronome application."""

import os
import tkinter as tk
from config import SAMPLES_FOLDER
from sound_manager import SoundManager
from metronome import Metronome
from song import SongManager
from setlist_manager import SetlistManager
from ui import MetronomeUI


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Initialize managers
    songs_dir = os.path.join(os.path.dirname(__file__), "Songs")
    setlists_dir = os.path.join(os.path.dirname(__file__), "Setlists")
    sound_manager = SoundManager()
    song_manager = SongManager(songs_dir)
    setlist_manager = SetlistManager(setlists_dir)
    
    # Create metronome
    metronome = Metronome(sound_manager)
    
    # Create and run UI
    ui = MetronomeUI(root, metronome, sound_manager, song_manager, setlist_manager)
    root.mainloop()


if __name__ == "__main__":
    main() 