# Metronome

A Python metronome application with song section management, setlist support, and sample-based audio playback.

## Setup

1. Clone the repo
2. Add WAV files to a `Samples/` folder in the project directory
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run:
   ```bash
   python main.py
   ```

**Dependencies**
- `pygame` — audio engine (required)
- `sv-ttk` — dark theme (optional; app runs without it)

> `Samples/`, `Songs/`, `Setlists/`, and `settings.json` are local to your machine and not tracked by git.

---

## Features

### Basic Metronome

- **BPM** — slider and editable entry, 20–250 BPM; keyboard shortcuts `+`/`↑` and `-`/`↓` nudge by 1
- **Tap Tempo** — click the button or press `T` to set BPM by feel; indicator flashes cyan on each tap
- **Beat indicator** — flashes red on beat 1, green on other beats
- **Time signature** — presets from 2/4 to 12/8, or enter a custom beats-per-bar value
- **Accent pattern** — click each beat button to cycle Strong (`●`) / Medium (`◐`) / Weak (`○`)
- **Subdivisions** — quarter notes through 32nd notes
- **Swing** — 2:1 long/short ratio on eighth-note subdivisions
- **Count-in** — enable/disable with a checkbox; set 1–8 bars
- **Timer** — auto-stop after N seconds (0 = run indefinitely)
- **Tempo Change Mode** — Speed Up or Slow Down by a configurable BPM step every N bars
- **Space bar** — Start / Pause / Resume (ignored when a text field has focus)

### Playback Feel (Settings tab)

- **Humanize** — adds random ±ms timing jitter per tick for a natural feel (0–50 ms)
- **Fade-in** — ramps volume from silence to full over the first N bars (0 = off)

### Song Flow

Songs are sequences of named **sections**, each with its own BPM, time signature, subdivisions, swing, bar count, and repeat count. Settings change automatically at each section boundary.

**Sections**
- Add, edit, duplicate, reorder, and remove sections
- **Count-in before section** — optional 1-bar count-in cue on each transition into a section (shown as `↵` in the list)
- **Repeat** — play a section N times before moving on

**Playback**
- **Play Song** — plays all sections in order, showing the Now Playing panel
- **Practice Mode** — select a section and click Practice to loop it indefinitely with a count-in each repeat; Restart re-loops the same section
- **Recent songs** — last 5 loaded/saved songs in a quick-load combobox

**Now Playing panel**
- Shows current section, BPM, bar counter, and upcoming section
- **Restart** — restart the current song or practice section from bar 1
- **Skip** — jump to the next song in the setlist
- **Shuffle** — randomise the remaining setlist order
- **Loop In / Loop Out** — mark a range of sections to repeat indefinitely; a count-in plays before each repeat

### Setlists

- Group songs into an ordered setlist with configurable silence between songs
- Save and load setlists; missing songs on load show a warning and are skipped
- **Export to Text** — save a formatted `.txt` summary of the setlist

### Settings

- Three independently configurable samples: accented beat, regular beat, count-in
- Preview button for each sample
- Volume sliders for each sample type
- Upload custom `.wav` files (copied into `Samples/` automatically)
- Scrollable settings tab

---

## Project Structure

```
Metronome/
├── main.py            # Entry point
├── metronome.py       # Core playback engine (threading, timing, swing, humanize)
├── ui.py              # Main window and all UI logic
├── dialogs.py         # Modal dialog windows
├── sound_manager.py   # Sample loading and playback (pygame)
├── song.py            # Song data model and file I/O
├── song_section.py    # SongSection data model
├── setlist.py         # Setlist data model
├── setlist_manager.py # Setlist file I/O
├── config.py          # Default values and constants
├── requirements.txt   # Python dependencies
├── Samples/           # WAV sample files (not tracked by git)
├── Songs/             # Saved song files — JSON (not tracked by git)
└── Setlists/          # Saved setlist files — JSON (not tracked by git)
```
