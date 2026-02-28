"""Song data structure for the metronome application."""

import json
import os
import re
from dataclasses import dataclass
from typing import List
from song_section import SongSection


def _safe_filename(name: str) -> str:
    """Strip characters that are illegal in filenames on Windows/Unix."""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


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
        """Convert song to dictionary for storage."""
        return {
            'name': self.name,
            'sections': [section.to_dict() for section in self.sections]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Song':
        """Create song from dictionary data."""
        try:
            return cls(
                name=data['name'],
                sections=[SongSection.from_dict(s) for s in data['sections']]
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid song data: {e}") from e

    def save(self, filename: str):
        """Save song to file."""
        try:
            with open(filename, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except OSError as e:
            raise OSError(f"Could not save song: {e}") from e

    @classmethod
    def load(cls, filename: str) -> 'Song':
        """Load song from file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


class SongManager:
    """Manages saving and loading songs."""

    def __init__(self, songs_dir: str):
        self.songs_dir = songs_dir
        os.makedirs(songs_dir, exist_ok=True)

    def get_song_files(self) -> List[str]:
        return [f for f in os.listdir(self.songs_dir) if f.endswith('.json')]

    def get_song_path(self, filename: str) -> str:
        return os.path.join(self.songs_dir, filename)

    def save_song(self, song: Song, filename: str):
        """Save a song to file, sanitising the filename."""
        safe = _safe_filename(filename)
        if not safe.endswith('.json'):
            safe += '.json'
        song.save(self.get_song_path(safe))

    def delete_song(self, filename: str):
        """Delete a song file."""
        if not filename.endswith('.json'):
            filename += '.json'
        path = self.get_song_path(filename)
        if os.path.exists(path):
            os.remove(path)

    def load_song(self, filename: str) -> Song:
        """Load a song from file."""
        if not filename.endswith('.json'):
            filename += '.json'
        return Song.load(self.get_song_path(filename))
