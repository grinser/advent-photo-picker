# Instructions for AI agents

You are setting up the Advent photo picker for a person who wants 24 photos and a cover for a photo Advent calendar.
They may not be a developer. Do the technical steps yourself, explain each one in a sentence, and ask them only for
what you cannot find out.

## Rules

- **Never look at the photos yourself.** Do not open, view, describe or analyze any photo, preview, thumbnail or face
  crop (`PHOTOS`, `prev/`, `thumbs/`, `faces/`, `calendar-photos/`). Do not print or read the contents of `data.js` or
  `work/` either, which hold dates, places and face data; scripts you write may use them on this computer. Anything you
  look at may go to your model provider. Work only from the scripts' output and their error messages.
- **Do not look at the page either.** Do not screenshot, read or inspect `index.html` once it shows their photos. To
  check that the page works, run `make_demo.py` and look at `demo/index.html`, which shows sketches.
- Everything stays on this computer. Never upload, send or copy the person's photos anywhere else.
- Never write to the photo folder. The scripts only read it and refuse to run from a folder inside it.
- Do not switch off the safeguards in `common.py` (no network access in the scripts that read photos) or the Content
  Security Policy in `index.html`, and do not add code that sends data anywhere.
- The picking is theirs. Set up and run the tool, then hand over the page.

## Steps

0. **Get the code** if this folder does not have it yet: clone the repository or download and unzip its ZIP. Do not
   put it inside the photo folder.
1. **Ask** where their photos are and from which day on they want to include them (default: the last 365 days).
   Subfolders are fine. If the photos are still on the phone or only in the Photos app, help them export first (see
   README, "Get your photos into a folder"). Mac Photos: File › Export › Export Unmodified Originals.
2. **Python:** check for Python 3.10 or newer (`python3 --version` on macOS and Linux, `py --version` on Windows). If
   it is missing, tell the person to install it from python.org; it needs their password.
3. **Environment**, in the repo folder:
   - macOS and Linux: `python3 -m venv .venv`, then use `.venv/bin/python` for every step.
   - Windows: `py -m venv .venv`, then use `.venv\Scripts\python.exe` for every step. Run commands in cmd.exe or pass
     environment variables in a way that works in your shell; `set` in PowerShell does nothing.
   - Install with `<python> -m pip install -r requirements.txt`.
4. **Models:** `<python> download_models.py` (about 330 MB, once).
5. **Run**, with the environment variables `PHOTOS` set to the photo folder and `START` to the first day
   (`YYYY-MM-DD`, there is no end date). Without them, `process.py` asks in a terminal. Where there is no terminal,
   it stops with "PHOTOS is not set." The commands are
   `<python> process.py`, then `<python> arc.py`, then `<python> build.py`. `process.py` takes about half an hour
   per 6,000 photos. Run it in the background if your tool allows it, and tell the person how far it is from its
   output (`n of total photos`). If it stops, run it again and it continues. Each script prints what to run next.
6. **Optional:** `look2.py` estimates whether eyes are open and looking at the camera. It needs Python 3.12 or older
   and its own environment with `requirements-look.txt`, then `build.py` again. Offer it, do not insist.
7. **Hand over:** tell the person the full path of `index.html` and open it in their browser. Explain in three
   sentences: the star puts a photo on the shortlist, the + under the star makes it a door, and a photo opened in the
   large view can become the cover. "0 places" or "0 people" in the output of `build.py` is normal when the photos
   have no GPS data or no faces. When they are done, "Export …" at the top of the page shows one command. It holds
   full paths and needs no `PHOTOS` or `START`, so you can run it for them from any folder. It writes 25 JPEGs into
   `calendar-photos/`.
8. **Into the photo service:** they drag the files into their photo service's software. If they want you to fill the
   calendar project file instead, follow [RECIPE.md](RECIPE.md).

## When something fails

- `CERTIFICATE_VERIFY_FAILED` while downloading models: `download_models.py` falls back to `curl` by itself. If curl is
  missing too, download the three files with the URLs in `download_models.py` and put them in `models/`.
- "No photos from … on": check `START` and the folder. The message says whether older photos exist.
- "The work folder belongs to …": the person switched photo folders. Delete `work`, `prev` and `thumbs` and start
  again.
- The page says "No data yet": `build.py` has not run, or ran in another folder.
- `HOME_COUNTRY` (for example `AT`) before `build.py` drops the country code from place names at home.

When they are done, offer to delete `prev`, `thumbs`, `faces`, `work`, `calendar-photos` and `data.js`. `models/`
(330 MB) and `.venv` can go too if they will not use the picker again.
