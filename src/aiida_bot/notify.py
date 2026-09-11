from __future__ import annotations

import platform
import shutil
import subprocess


def desktop_notification(title: str, message: str) -> bool:
    """Best-effort local notification; never makes the watcher fail."""
    try:
        if platform.system() == "Darwin" and shutil.which("osascript"):
            quote = lambda value: '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
            script = f"display notification {quote(message)} with title {quote(title)}"
            subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
            return True
        if platform.system() == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=False, capture_output=True)
            return True
    except OSError:
        pass
    return False
