"""Setlist management functionality."""

from dataclasses import dataclass, field
from typing import List, Optional
from song import Song


@dataclass
class SetlistEntry:
    """Represents a song entry in a setlist."""
    song: Song
    delay_after: float = 0.0  # Delay in seconds after this song


@dataclass
class Setlist:
    """Represents a collection of songs with delays between them."""
    name: str
    entries: List[SetlistEntry] = field(default_factory=list)

    def add_entry(self, song: Song, delay_after: float = 0.0):
        """Add a song to the setlist.
        
        Args:
            song (Song): Song to add
            delay_after (float): Delay in seconds after this song
        """
        self.entries.append(SetlistEntry(song, delay_after))

    def remove_entry(self, index: int):
        """Remove a song from the setlist.
        
        Args:
            index (int): Index of song to remove
        """
        if 0 <= index < len(self.entries):
            self.entries.pop(index)

    def move_entry(self, from_index: int, to_index: int):
        """Move a song to a different position.
        
        Args:
            from_index (int): Current position
            to_index (int): New position
        """
        if 0 <= from_index < len(self.entries) and 0 <= to_index < len(self.entries):
            entry = self.entries.pop(from_index)
            self.entries.insert(to_index, entry)

    def to_dict(self) -> dict:
        """Convert setlist to dictionary for saving.
        
        Returns:
            dict: Dictionary representation
        """
        return {
            'name': self.name,
            'entries': [
                {
                    'song_name': entry.song.name,
                    'delay_after': entry.delay_after
                }
                for entry in self.entries
            ]
        }

    @classmethod
    def from_dict(cls, data: dict, song_manager) -> 'Setlist':
        """Create setlist from dictionary.
        
        Args:
            data (dict): Dictionary representation
            song_manager (SongManager): Song manager instance
            
        Returns:
            Setlist: New setlist instance
        """
        setlist = cls(name=data['name'])
        for entry_data in data['entries']:
            song = song_manager.load_song(entry_data['song_name'])
            setlist.add_entry(
                song,
                delay_after=entry_data['delay_after']
            )
        return setlist 