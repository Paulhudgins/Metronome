# Metronome

A Python metronome application with song section management, setlist support, and sample-based audio playback.

## Requirements

- Python 3.8+
- pygame

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Features

### Basic Tab

- **BPM slider** — set tempo from 20–250 BPM
- **Beat indicator** — flashes red on accented beats, green on regular beats
- **Tap Tempo** — click the button in rhythm to set BPM automatically; resets if you pause more than 2 seconds
- **Space bar** — toggles start/stop (does not fire when typing in a field)
- **Beats per Bar** — set the time signature numerator (e.g. 4 for 4/4)
- **Subdivisions per Beat** — play subdivided beats (e.g. 2 for eighth notes)
- **Swing** — applies a 2:1 long/short swing ratio; automatically sets subdivisions to 2
- **Count-in Bars** — number of count-in bars before playback starts (default: 2)
- **Timer** — stop automatically after a set number of seconds (0 = run indefinitely)
- **Tempo Change Mode** — gradually speed up or slow down by a configurable step every N bars

### Song Flow Tab

Songs are made up of named **sections**, each with its own BPM, time signature, subdivision, and bar count. Sections play back in order, with settings changing automatically at each section boundary.

**Song management:**
- Create, save, and load songs (stored as JSON in the `Songs/` folder)
- Add, edit, remove, and reorder sections

**Setlist management:**
- Group songs into a setlist with configurable delays between songs
- Save and load setlists (stored as JSON in the `Setlists/` folder)
- Play through the entire setlist automatically — each song completes before the next begins

### Settings Tab

- Select samples for accented beats, regular beats, and the count-in independently
- Upload custom `.wav` samples (copied into the `Samples/` folder automatically)
- Adjust volume independently for each beat type

## Project Structure

```
Metronome/
├── main.py            # Entry point
├── metronome.py       # Core playback engine (threading, timing, swing)
├── ui.py              # Main window and all UI logic
├── dialogs.py         # Modal dialog windows
├── sound_manager.py   # Sample loading and playback (pygame)
├── song.py            # Song data model and file I/O
├── song_section.py    # SongSection data model
├── setlist.py         # Setlist data model
├── setlist_manager.py # Setlist file I/O
├── config.py          # Default values and constants
├── Samples/           # Built-in .wav sample files
├── Songs/             # Saved song files (.json)
└── Setlists/          # Saved setlist files (.json)
```

## Sample Files

The `Samples/` folder includes a collection of 808 and acoustic drum samples across multiple categories: kicks, snares, hi-hats, open hats, crashes, rides, claps, toms, and percussion. Any `.wav` file placed in this folder will appear in the sample dropdowns.
