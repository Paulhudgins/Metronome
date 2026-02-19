"""Setlist management functionality."""

import os
import json
from typing import List
from setlist import Setlist


class SetlistManager:
    """Manages saving and loading of setlists."""
    
    def __init__(self, setlists_dir: str):
        """Initialize the setlist manager.
        
        Args:
            setlists_dir (str): Directory to store setlist files
        """
        self.setlists_dir = setlists_dir
        os.makedirs(setlists_dir, exist_ok=True)
        
    def save_setlist(self, setlist: Setlist):
        """Save a setlist to file.
        
        Args:
            setlist (Setlist): Setlist to save
        """
        filename = f"{setlist.name}.json"
        filepath = os.path.join(self.setlists_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(setlist.to_dict(), f, indent=2)
            
    def load_setlist(self, name: str, song_manager) -> Setlist:
        """Load a setlist from file.
        
        Args:
            name (str): Name of setlist to load
            song_manager (SongManager): Song manager instance
            
        Returns:
            Setlist: Loaded setlist
        """
        filename = f"{name}.json"
        filepath = os.path.join(self.setlists_dir, filename)
        
        with open(filepath, 'r') as f:
            data = json.load(f)
            return Setlist.from_dict(data, song_manager)
            
    def get_setlist_files(self) -> List[str]:
        """Get list of available setlist files.
        
        Returns:
            List[str]: List of setlist names
        """
        files = []
        for filename in os.listdir(self.setlists_dir):
            if filename.endswith('.json'):
                files.append(filename[:-5])  # Remove .json extension
        return sorted(files) 