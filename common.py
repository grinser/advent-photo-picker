"""Shared helpers: the photo folder, the model check, progress output, and the network block."""
import os, sys, socket

HERE = os.path.dirname(os.path.abspath(__file__))
SAVED = os.path.join(HERE, "work", "photos.txt")
WIN = sys.platform == "win32"


def photos_dir(required=True):
    """PHOTOS from the environment, without stray quotes. Falls back to the folder process.py used last."""
    raw = os.environ.get("PHOTOS", "").strip().strip('"').strip("'")
    if not raw and os.path.exists(SAVED):
        raw = open(SAVED, encoding="utf-8").read().strip()
    if not raw and interactive():
        raw = clean_path(ask("Which folder are your photos in? Drag the folder into this window, then press Enter:\n> "))
    if raw: os.environ["PHOTOS"] = raw   # worker processes inherit it
    path = os.path.abspath(os.path.expanduser(raw)) if raw else ""
    if required and not os.path.isdir(path):
        hint = "set PHOTOS=C:\\Users\\you\\Pictures\\advent-export" if WIN else "export PHOTOS=\"$HOME/Pictures/advent-export\""
        what = "PHOTOS is not set." if not raw else "No folder at " + path + "."
        sys.exit(what + " Point it at your photo folder first, for example:\n  " + hint)
    return path


def interactive():
    """True in a terminal a person types into, never in worker processes."""
    import multiprocessing
    return sys.stdin.isatty() and multiprocessing.parent_process() is None


def ask(question):
    """input() that returns "" where nobody can answer (Windows reports NUL as a terminal, then input() hits the end)."""
    try: return input(question)
    except EOFError: print(); return ""


def clean_path(text):
    """A path typed or dragged into the terminal: quotes, a trailing space and the Mac's backslash escapes removed."""
    text = text.strip().strip('"').strip("'")
    return text if WIN else text.replace("\\ ", " ").replace("\\(", "(").replace("\\)", ")").replace("\\'", "'")


def need_models(*names):
    missing = [n for n in names if not os.path.exists(os.path.join(HERE, "models", n))]
    if missing:
        sys.exit("Missing in models/: " + ", ".join(missing) + ". Run  python download_models.py  first.")


def progress(n, total, t0, now):
    left = (now - t0) / max(n, 1) * (total - n)
    print("\r  %d of %d photos, about %d min left   " % (n, total, left // 60 + 1), end="", flush=True)


def _offline(*a, **k):
    raise OSError("advent-photo-picker: network access is switched off in the scripts that read your photos")


def offline():
    """Blocks every internet connection from this process and its workers. Only download_models.py goes online."""
    for name in ("connect", "connect_ex"):
        orig = getattr(socket.socket, name)
        def guard(self, addr, _orig=orig):
            if self.family in (socket.AF_INET, socket.AF_INET6): _offline()
            return _orig(self, addr)
        setattr(socket.socket, name, guard)
    socket.create_connection = socket.getaddrinfo = _offline


offline()   # on import, so every script that imports this module is offline


def outside_photos(path, src):
    """Refuses to write anything inside the photo folder."""
    p, s = os.path.realpath(path), os.path.realpath(src)
    if p == s or p.startswith(s.rstrip(os.sep) + os.sep):
        sys.exit("This folder is inside your photo folder " + src + ". Put the picker somewhere else, so it never "
                 "writes next to your photos.")
