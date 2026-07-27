# MP3 to M4B Audiobook Converter

A desktop GUI for merging a folder of MP3 files into a single `.m4b`
audiobook file with an embedded cover image, built with PyQt6 and ffmpeg.

## Features

- Drag-and-drop MP3 files, folders, or a cover image directly onto the window
- Reorderable file list (drag rows, or use Move Up / Move Down)
- Add individual files or an entire folder of MP3s at once
- Cover image preview before conversion
- Adjustable audio bitrate
- Conversion runs in the background so the UI never freezes
- Live ffmpeg log output and a Cancel button mid-conversion

## Requirements

- Python 3.9+
- [ffmpeg](https://ffmpeg.org/download.html) installed and available on your system `PATH`
- Python packages listed in `requirements.txt`

## Installation

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
```

Make sure ffmpeg is installed:

- **Windows:** download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your `PATH`, or install via `winget install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (or your distro's package manager)

## Usage

```bash
python m4b_converter_gui.py
```

1. Add your MP3 files or a folder using the buttons, or drag them into the file list
2. Reorder tracks if needed (drag, or Move Up / Move Down)
3. Choose a cover image
4. Set the output `.m4b` path
5. (Optional) adjust the audio bitrate — defaults to `64k`
6. Click **Convert to M4B**

Progress and any ffmpeg output are shown live in the log panel at the
bottom of the window.

## How it works

The app writes a temporary ffmpeg concat list of your MP3 files in order,
then runs a single ffmpeg command that:

- Concatenates the audio into AAC
- Embeds the chosen image as cover art (`attached_pic`)
- Wraps the result in an MP4/M4B container with `faststart` for quick
  seeking in audiobook players

## License

MIT — feel free to modify and reuse.
