"""Local settings only. Secrets never belong in this module."""
import json
import os
from pathlib import Path
from .ai import PROVIDERS

DEFAULTS = dict(width=420, monitor="", position=0.5, topmost=True,
                auto_hide=False, pinned=False, minimized=True, animation=True,
                compact=False, accent="#dddddd", hidden=False, extensions=True,
                confirm_delete=True, default_path=str(Path.home()), sort=0,
                favorites=[], hotkey="Ctrl+Alt+G", ai_enabled=False,
                provider="OpenAI", models={"OpenAI": "", "Gemini": "", "xAI": ""},
                quick_favorites=False, quick_search=False, startup=False,
                view_mode="list", columns=[1], wide_columns=[2, 1, 3], descending=False)


class Settings:
    def __init__(self, root=None):
        self.root = Path(root or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GROK")
        self.path = self.root / "settings.json"
        self.data = json.loads(json.dumps(DEFAULTS))
        self.recovered = False
        try:
            raw = json.loads(self.path.read_text("utf-8"))
            for key, default in DEFAULTS.items():
                value = raw.get(key, default)
                if type(value) is type(default):
                    self.data[key] = value
        except FileNotFoundError:
            pass
        except (ValueError, OSError, AttributeError):
            self.recovered = True
        self.data["width"] = min(700, max(360, self.data["width"]))
        self.data["position"] = min(1.0, max(0.0, self.data["position"]))
        self.data["favorites"] = [x for x in self.data["favorites"] if isinstance(x, str)]
        self.data["models"] = {p: str(self.data["models"].get(p, "")) for p in PROVIDERS}

    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), "utf-8")
        tmp.replace(self.path)


class History:
    def __init__(self):
        self.paths = []
        self.index = -1

    def push(self, path):
        if self.index >= 0 and self.paths[self.index] == path:
            return
        self.paths = self.paths[:self.index + 1] + [path]
        self.index = len(self.paths) - 1

    def step(self, offset):
        target = self.index + offset
        if 0 <= target < len(self.paths):
            return self.paths[target]
        return None
