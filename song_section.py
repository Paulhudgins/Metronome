"""Song section data structure for the metronome application."""

from dataclasses import dataclass
from config import MIN_BPM, MAX_BPM


@dataclass
class SongSection:
    """Represents a section of a song with specific timing and settings."""

    name: str
    bars: int
    bpm: int
    beats_per_bar: int
    subdivisions: int
    swing_enabled: bool = False
    repeat: int = 1
    count_in: bool = False

    def __post_init__(self):
        """Validate section parameters."""
        if self.bars <= 0:
            raise ValueError("Number of bars must be positive")
        if self.bpm <= 0:
            raise ValueError("BPM must be positive")
        if not (MIN_BPM <= self.bpm <= MAX_BPM):
            raise ValueError(f"BPM must be between {MIN_BPM} and {MAX_BPM}")
        if self.beats_per_bar <= 0:
            raise ValueError("Beats per bar must be positive")
        if self.subdivisions <= 0:
            raise ValueError("Subdivisions must be positive")
        if self.repeat < 1:
            raise ValueError("Repeat must be at least 1")

    def get_total_ticks(self) -> int:
        """Calculate total number of ticks in this section."""
        return self.bars * self.beats_per_bar * self.subdivisions

    def to_dict(self) -> dict:
        """Convert section to dictionary for storage."""
        return {
            'name': self.name,
            'bars': self.bars,
            'bpm': self.bpm,
            'beats_per_bar': self.beats_per_bar,
            'subdivisions': self.subdivisions,
            'swing_enabled': self.swing_enabled,
            'repeat': self.repeat,
            'count_in': self.count_in,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SongSection':
        """Create section from dictionary data."""
        try:
            return cls(
                name=data['name'],
                bars=data['bars'],
                bpm=data['bpm'],
                beats_per_bar=data['beats_per_bar'],
                subdivisions=data['subdivisions'],
                swing_enabled=data['swing_enabled'],
                repeat=data.get('repeat', 1),
                count_in=data.get('count_in', False),
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid section data: {e}") from e
