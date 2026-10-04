"""Filesystem mutations: explicit destinations, no replacement, no link traversal."""
import os
import shutil
import threading
from pathlib import Path


def valid_name(name):
    if not name or name in (".", "..") or name[-1] in " ." or any(c in name for c in '<>:"/\\|?*') or any(ord(c) < 32 for c in name):
        raise ValueError("Use a valid Windows filename without slashes or trailing dots/spaces.")
    if name.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise ValueError("That name is reserved by Windows.")
    return name


def is_link(path):
    p = Path(path)
    return p.is_symlink() or bool(p.lstat().st_file_attributes & 0x400) if os.name == "nt" else p.is_symlink()


def validate_folder(path):
    p = Path(os.path.expandvars(str(path).strip().strip('"'))).expanduser().absolute()
    if not p.is_dir():
        raise ValueError("This folder is unavailable. Check the path, drive, and permissions.")
    with os.scandir(p):
        pass
    return str(p)


def plan_transfer(sources, destination):
    dest = Path(validate_folder(destination)).resolve()
    planned = []
    seen = set()
    for source in sources:
        src = Path(source).absolute()
        if not src.exists():
            raise FileNotFoundError("An item no longer exists. Refresh and try again.")
        if is_link(src):
            raise ValueError("Transfers of links and junctions are not supported. Use Explorer for this item.")
        real = src.resolve()
        target = dest / src.name
        if real == target or (src.is_dir() and dest.is_relative_to(real)):
            raise ValueError("Choose a different folder; a folder cannot be copied into itself.")
        if target.exists() or target.name.casefold() in seen:
            raise FileExistsError("An item with that name already exists. Rename it or choose another destination; nothing was overwritten.")
        seen.add(target.name.casefold())
        if src.is_dir():
            for root, dirs, names in os.walk(src, followlinks=False):
                for name in dirs + names:
                    if is_link(Path(root) / name):
                        raise ValueError("This folder contains a link or junction. Use Explorer for this transfer.")
        planned.append((src, target))
    return planned


def copy_file(src, dst, cancel):
    # Exclusive create prevents racing another writer and overwriting data.
    with open(src, "rb") as inp, open(dst, "xb") as out:
        try:
            while chunk := inp.read(1024 * 1024):
                if cancel.is_set():
                    raise InterruptedError("Operation canceled. Completed items are retained.")
                out.write(chunk)
        except BaseException:
            out.close()
            Path(dst).unlink(missing_ok=True)
            raise
    shutil.copystat(src, dst)


def transfer(sources, destination, move=False, cancel=None, progress=lambda text: None):
    cancel = cancel or threading.Event()
    planned = plan_transfer(sources, destination)
    completed = []
    for i, (src, target) in enumerate(planned):
        if cancel.is_set():
            raise InterruptedError("Operation canceled. Completed items are retained.")
        progress(f"{'Moving' if move else 'Copying'} {i + 1} of {len(planned)}…")
        if move and src.drive.casefold() == target.drive.casefold():
            os.rename(src, target)  # Windows refuses an existing destination.
        else:
            if src.is_dir():
                shutil.copytree(src, target, copy_function=lambda a, b: copy_file(a, b, cancel))
            else:
                copy_file(src, target, cancel)
            if move:
                if src.is_dir():
                    shutil.rmtree(src)
                else:
                    src.unlink()
        completed.append(str(target))
    return completed


def rename(path, name):
    p = Path(path)
    target = p.with_name(valid_name(name))
    if target.exists():
        raise FileExistsError("That name already exists.")
    p.rename(target)
    return str(target)


def create_folder(parent, name):
    p = Path(parent) / valid_name(name)
    p.mkdir()
    return str(p)
