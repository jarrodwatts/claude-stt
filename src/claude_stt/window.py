"""Cross-platform window focus tracking and restoration."""

import logging
import platform
import subprocess
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class WindowInfo:
    """Information about a captured window."""

    window_id: str
    platform: str
    app_name: Optional[str] = None


def get_active_window() -> Optional[WindowInfo]:
    """Capture the currently active window.

    Returns:
        WindowInfo with the window identifier, or None if unable to capture.
    """
    system = platform.system()

    try:
        if system == "Darwin":
            return _get_macos_window()
        elif system == "Linux":
            return _get_linux_window()
        elif system == "Windows":
            return _get_windows_window()
    except Exception:
        logging.getLogger(__name__).debug("Failed to capture active window", exc_info=True)

    return None


def restore_focus(window_info: Optional[WindowInfo]) -> bool:
    """Restore focus to a previously captured window.

    Args:
        window_info: The window information from get_active_window().

    Returns:
        True if focus was restored, False otherwise.
    """
    if window_info is None:
        return False
    if not window_info.window_id and not window_info.app_name:
        return False

    try:
        if window_info.platform == "Darwin":
            return _restore_macos_focus(window_info)
        elif window_info.platform == "Linux":
            return _restore_linux_focus(window_info)
        elif window_info.platform == "Windows":
            return _restore_windows_focus(window_info)
    except Exception:
        logging.getLogger(__name__).debug("Failed to restore focus", exc_info=True)

    return False


def _get_macos_window() -> Optional[WindowInfo]:
    """Get active window on macOS using AppleScript."""
    script = '''
    tell application "System Events"
        set frontApp to first application process whose frontmost is true
        set appName to name of frontApp
        try
            set winId to id of front window of frontApp
            return appName & "\n" & winId
        on error
            return appName & "\n"
        end try
    end tell
    '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        app_name = lines[0].strip() if lines else None
        window_id = lines[1].strip() if len(lines) > 1 else ""
        if app_name:
            return WindowInfo(window_id=window_id, platform="Darwin", app_name=app_name)

    logging.getLogger(__name__).debug(
        "osascript get window failed: %s", result.stderr.strip()
    )
    return None


def _restore_macos_focus(window_info: WindowInfo) -> bool:
    """Restore focus on macOS using AppleScript."""
    if window_info.app_name and window_info.window_id:
        script = f'''
        tell application "System Events"
            tell process "{window_info.app_name}"
                set frontmost to true
                if (exists (first window whose id is {window_info.window_id})) then
                    perform action "AXRaise" of (first window whose id is {window_info.window_id})
                end if
            end tell
        end tell
        '''
    elif window_info.app_name:
        script = f'''
        tell application "System Events"
            tell process "{window_info.app_name}"
                set frontmost to true
            end tell
        end tell
        '''
    else:
        script = f'''
        tell application "System Events"
            set frontmost of (first process whose unix id is {window_info.window_id}) to true
        end tell
        '''

    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
    )

    if result.returncode == 0:
        time.sleep(0.1)  # Allow focus to settle
        return True

    logging.getLogger(__name__).debug(
        "osascript restore focus failed: %s", result.stderr
    )
    return False


def _get_linux_window() -> Optional[WindowInfo]:
    """Get active window on Linux using xdotool."""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            window_id = result.stdout.strip()
            return WindowInfo(window_id=window_id, platform="Linux")
    except FileNotFoundError:
        # xdotool not installed
        logging.getLogger(__name__).debug("xdotool not installed")
        pass

    return None


def _restore_linux_focus(window_info: WindowInfo) -> bool:
    """Restore focus on Linux using xdotool."""
    try:
        result = subprocess.run(
            ["xdotool", "windowactivate", window_info.window_id],
            capture_output=True,
        )

        if result.returncode == 0:
            time.sleep(0.1)  # Allow focus to settle
            return True
    except FileNotFoundError:
        logging.getLogger(__name__).debug("xdotool not installed")
        pass

    return False


def _get_windows_window() -> Optional[WindowInfo]:
    """Get active window on Windows using ctypes."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()

        if hwnd:
            return WindowInfo(window_id=str(hwnd), platform="Windows")
    except Exception:
        pass

    return None


def _restore_windows_focus(window_info: WindowInfo) -> bool:
    """Restore focus on Windows using ctypes."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = int(window_info.window_id)

        # Show and activate the window
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)

        time.sleep(0.1)  # Allow focus to settle
        return True
    except Exception:
        pass

    return False
