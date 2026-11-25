# Changelog

All notable changes to the Advent photo picker are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version numbers follow
[Semantic Versioning](https://semver.org/):

- **Major:** results in `work/`, `data.js` or a saved selection from an older version no longer fit, so you have to run
  the scripts again or lose picks.
- **Minor:** a new feature. Your results and picks keep working.
- **Patch:** a bug fix.

Each version is a [release on GitHub](https://github.com/grinser/advent-photo-picker/releases) with a ZIP to download.

## [Unreleased]

### Added

- In the large view you can drag the crop frame to the part of the photo you want, and double-click it to centre it
  again. The position is saved per photo, separately for the door and the cover. The export still writes whole photos
  and lists every crop in `calendar-photos/crops.json`, which the recipe uses to fill the project file.

### Changed

- The strip next to the large view stays where it is when you click a photo in it, so the photo under the mouse no
  longer changes. It scrolls only when the current photo would leave the view, and only as far as needed.
- You can give more than 24 photos a door while you decide. The counter then shows how many are too many, the doors
  get a ✓ instead of a number, and the export waits until exactly 24 are left. The numbers return at 24.

### Fixed

- In the large view, the photos on the right no longer overlap when a burst has many photos.
- Closing the large view scrolls the gallery back to the last photo you looked at. If that photo is not in the
  gallery (sorted out, already seen, or opened from the row on the right), it scrolls to the nearest photo by time.
- The Doors view always shows the cover at the top, even when a filter such as month or orientation would hide it.

## [1.1.0] - 2026-11-25

### Added

- A second photo source: `EXTRA="partner=/path/to/folder"` adds another person's photo folder. Its photos are named
  `@partner/...`, so your own photos and picks stay as they are. `process.py` reads only the new photos.
- WhatsApp images get their own label: no camera data, no date and a typical WhatsApp size, or a name like
  `IMG-20250101-WA0001`.
- Photos in the second source that are copies of your own photos (perceptual hash with
  [ImageHash](https://github.com/JohannesBuchner/imagehash) and the same aspect ratio) are sorted out as "sent by you"
  and take the date of your original. `WA_T` sets how close a match has to be.
- Filter › Source in the page: all, yours, the other source, or the photos you sent.

### Changed

- `requirements.txt` includes ImageHash. Run `python -m pip install -r requirements.txt` once after the update.

## [1.0.0] - 2026-11-24

### Added

- First public version: `process.py`, `arc.py`, `build.py` and `export.py` sort out blurry and dark photos,
  screenshots, duplicates and bursts, group faces and places, and write one page to pick 24 doors and a cover.
- Optional `look2.py` for open eyes and looking at the camera.
- `make_demo.py` for a demo with sketches instead of photos.
- Interface in English and German.

[Unreleased]: https://github.com/grinser/advent-photo-picker/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/grinser/advent-photo-picker/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/grinser/advent-photo-picker/releases/tag/v1.0.0
