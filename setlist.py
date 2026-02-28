"""Setlist management functionality."""

from dataclasses import dataclass, field
from typing import List, Optional
from song import Song


class PartialSetlistError(Exception):
    """Raised when a setlist loads but some songs were missing from disk.

    The partial setlist (with available songs only) is attached as `setlist`,
    and `missing` holds the names of songs that could not be found.
    """
    def __init__(self, setlist, missing):
        self.setlist = setlist
        self.missing = missing
        super().__init__(
            f"Loaded with {len(missing)} missing song(s): "
            + ', '.join(f"'{m}'" for m in missing)
        )


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
        self.entries.append(SetlistEntry(song, delay_after))

    def remove_entry(self, index: int):
        if 0 <= index < len(self.entries):
            self.entries.pop(index)

    def move_entry(self, from_index: int, to_index: int):
        if 0 <= from_index < len(self.entries) and 0 <= to_index < len(self.entries):
            entry = self.entries.pop(from_index)
            self.entries.insert(to_index, entry)

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'entries': [
                {'song_name': entry.song.name, 'delay_after': entry.delay_after}
                for entry in self.entries
            ]
        }

    @classmethod
    def from_dict(cls, data: dict, song_manager) -> 'Setlist':
        """Create setlist from dictionary, skipping songs that can't be loaded."""
        setlist = cls(name=data['name'])
        missing = []
        for entry_data in data['entries']:
            try:
                song = song_manager.load_song(entry_data['song_name'])
                setlist.add_entry(song, delay_after=entry_data.get('delay_after', 0.0))
            except Exception:
                missing.append(entry_data.get('song_name', '?'))
        if missing:
            raise PartialSetlistError(setlist, missing)
        return setlist
