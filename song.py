"""Song data structure for the metronome application."""

import json
import os
from dataclasses import dataclass
from typing import List
from song_section import SongSection


@dataclass
class Song:
    """Represents a complete song with multiple sections."""
    
    name: str
    sections: List[SongSection]
    
    def __post_init__(self):
        """Validate song data."""
        if not self.name:
            raise ValueError("Song name cannot be empty")
    
    def to_dict(self) -> dict:
        """Convert song to dictionary for storage.
        
        Returns:
            dict: Song data as dictionary
        """
        return {
            'name': self.name,
            'sections': [section.to_dict() for section in self.sections]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Song':
        """Create song from dictionary data.
        
        Args:
            data (dict): Song data as dictionary
            
        Returns:
            Song: New song instance
        """
        return cls(
            name=data['name'],
            sections=[SongSection.from_dict(section) for section in data['sections']]
        )
    
    def save(self, filename: str):
        """Save song to file.
        
        Args:
            filename (str): Path to save file
        """
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filename: str) -> 'Song':
        """Load song from file.
        
        Args:
            filename (str): Path to load file from
            
        Returns:
            Song: Loaded song instance
        """
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class SongManager:
    """Manages saving and loading songs."""
    
    def __init__(self, songs_dir: str):
        """Initialize the song manager.
        
        Args:
            songs_dir (str): Directory to store song files
        """
        self.songs_dir = songs_dir
        os.makedirs(songs_dir, exist_ok=True)
    
    def get_song_files(self) -> List[str]:
        """Get list of available song files.
        
        Returns:
            List[str]: List of song filenames
        """
        return [
            f for f in os.listdir(self.songs_dir)
            if f.endswith('.json')
        ]
    
    def get_song_path(self, filename: str) -> str:
        """Get full path for a song file.
        
        Args:
            filename (str): Song filename
            
        Returns:
            str: Full path to song file
        """
        return os.path.join(self.songs_dir, filename)
    
    def save_song(self, song: Song, filename: str):
        """Save a song to file.
        
        Args:
            song (Song): Song to save
            filename (str): Filename to save as
        """
        if not filename.endswith('.json'):
            filename += '.json'
        song.save(self.get_song_path(filename))
    
    def load_song(self, filename: str) -> Song:
        """Load a song from file.
        
        Args:
            filename (str): Filename to load
            
        Returns:
            Song: Loaded song
        """
        if not filename.endswith('.json'):
            filename += '.json'
        return Song.load(self.get_song_path(filename)) 