from __future__ import annotations

import platform
import shutil
import subprocess


def desktop_notification(title: str, message: str) -> bool:
    """Best-effort local notification; never makes the watcher fail."""
    try:
        if platform.system() == "Darwin" and shutil.which("osascript"):
            script = f'display notification {message!r} with title {title!r}'
            subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
            return True
        if platform.system() == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=False, capture_output=True)
            return True
    except OSError:
        pass
    return False
