"""Setlist management functionality."""

import os
import json
import re
from typing import List
from setlist import Setlist


def _safe_filename(name: str) -> str:
    """Strip characters that are illegal in filenames on Windows/Unix."""
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


class SetlistManager:
    """Manages saving and loading of setlists."""

    def __init__(self, setlists_dir: str):
        self.setlists_dir = setlists_dir
        os.makedirs(setlists_dir, exist_ok=True)

    def save_setlist(self, setlist: Setlist):
        """Save a setlist to file."""
        safe = _safe_filename(setlist.name)
        filepath = os.path.join(self.setlists_dir, f"{safe}.json")
        try:
            with open(filepath, 'w') as f:
                json.dump(setlist.to_dict(), f, indent=2)
        except OSError as e:
            raise OSError(f"Could not save setlist: {e}") from e

    def load_setlist(self, name: str, song_manager) -> Setlist:
        """Load a setlist from file."""
        filepath = os.path.join(self.setlists_dir, f"{name}.json")
        with open(filepath, 'r') as f:
            data = json.load(f)
        return Setlist.from_dict(data, song_manager)

    def delete_setlist(self, name: str):
        """Delete a setlist file."""
        filepath = os.path.join(self.setlists_dir, f"{name}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def get_setlist_files(self) -> List[str]:
        """Get list of available setlist names."""
        files = []
        for filename in os.listdir(self.setlists_dir):
            if filename.endswith('.json'):
                files.append(filename[:-5])
        return sorted(files)
