"""Song section data structure for the metronome application."""

from dataclasses import dataclass


@dataclass
class SongSection:
    """Represents a section of a song with specific timing and settings."""

    name: str
    bars: int
    bpm: int
    beats_per_bar: int
    subdivisions: int
    swing_enabled: bool = False
    
    def __post_init__(self):
        """Validate section parameters."""
        if self.bars <= 0:
            raise ValueError("Number of bars must be positive")
        if self.bpm <= 0:
            raise ValueError("BPM must be positive")
        if self.beats_per_bar <= 0:
            raise ValueError("Beats per bar must be positive")
        if self.subdivisions <= 0:
            raise ValueError("Subdivisions must be positive")
    
    def get_total_ticks(self) -> int:
        """Calculate total number of ticks in this section.
        
        Returns:
            int: Total number of ticks
        """
        return self.bars * self.beats_per_bar * self.subdivisions
    
    def to_dict(self) -> dict:
        """Convert section to dictionary for storage.
        
        Returns:
            dict: Section data as dictionary
        """
        return {
            'name': self.name,
            'bars': self.bars,
            'bpm': self.bpm,
            'beats_per_bar': self.beats_per_bar,
            'subdivisions': self.subdivisions,
            'swing_enabled': self.swing_enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SongSection':
        """Create section from dictionary data.
        
        Args:
            data (dict): Section data as dictionary
            
        Returns:
            SongSection: New section instance
        """
        return cls(
            name=data['name'],
            bars=data['bars'],
            bpm=data['bpm'],
            beats_per_bar=data['beats_per_bar'],
            subdivisions=data['subdivisions'],
            swing_enabled=data['swing_enabled']
        ) 