#!/usr/bin/env python3
"""
waybar custom module: windows grouped and ordered by workspace.

wlr/taskbar uses the foreign-toplevel protocol, which carries no workspace
information, so it can only list windows in creation order. This reads sway's
IPC instead, which knows the workspace layout.

Streams: emits once at startup, then again on every sway window/workspace event.
"""

import html
import json
import select
import subprocess
import sys

# nerd font glyphs, keyed by app_id (wayland) / WM class (x11).
# every codepoint below is verified present in Symbols Nerd Font.
ICONS = {
    "AmneziaVPN": "\uf132",
    "azote": "\uf302",
    "blueman-adapters": "\uf293",
    "blueman-manager": "\uf293",
    "chromium": "\uf268",
    "Chromium-browser": "\uf268",
    "chromium-browser": "\uf268",
    "code": "\uf1c9",
    "dqf-license-creator": "\ueb11",
    "firefox": "\uf269",
    "foot": "\uf120",
    "foot-server": "\uf120",
    "footclient": "\uf120",
    "it.mijorus.gearlever": "\uf0ad",
    "jetbrains-idea": "\ue7b5",
    "jetbrains-idea-ce": "\ue7b5",
    "jetbrains-toolbox": "\ue808",
    "kdenlive": "\uefab",
    "kse": "\ueb11",
    "Mattermost": "\uf27a",
    "mpv": "\uf008",
    "nwg-clipman": "\uf0ea",
    "nwg-displays": "\uf108",
    "nwg-look": "\uf1fc",
    "nwg-panel-config": "\uf1de",
    "nwg-shell-config": "\uf1de",
    "obs": "\uf03d",
    "obsidian": "\uf40e",
    "ONLYOFFICE": "\uf376",
    "org.freedesktop.GnomeAbrt": "\uf188",
    "org.gnome.DiskUtility": "\uf0a0",
    "org.gnome.Nautilus": "\uf07b",
    "org.kde.discover": "\uf466",
    "org.kde.kdeconnect.app": "\ued08",
    "org.kde.kdeconnect.nonplasma": "\ued08",
    "org.kde.kdeconnect.sms": "\uf27a",
    "org.mozilla.firefox": "\uf269",
    "org.pulseaudio.pavucontrol": "\uf028",
    "org.telegram.desktop": "\uf2c6",
    "panel-preferences": "\uf1de",
    "pavucontrol": "\uf028",
    "rofi": "\uf002",
    "rofi-theme-selector": "\uf002",
    "setroubleshoot": "\ued25",
    "system-config-language": "\uf1ab",
    "system-config-printer": "\uef70",
    "TelegramDesktop": "\uf2c6",
    "throne": "\uf132",
    "thunar": "\uf07b",
    "thunar-bulk-rename": "\uf07b",
    "thunar-settings": "\uf07b",
    "thunderbird": "\ueb1c",
    "thunderbird-esr": "\ueb1c",
    "vlc": "\uf008",
    "xarchiver": "\uf1c6",
}
DEFAULT_ICON = ""

WS_COLOR = "#88c0d0"      # nord8, workspace number
FOCUS_BG = "#8fbcbb"      # nord7, focused window pill
FOCUS_FG = "#2e3440"
DIM = "#d8dee9"

# progressively shorter titles, then icon-only (0) when the bar gets crowded
TIERS = (22, 12, 0)
MAX_CHARS = 185   # rough width budget for the taskbar half of the bar
DEBOUNCE = 0.05   # seconds to coalesce a burst of sway events


def sway(*args):
    out = subprocess.run(["swaymsg", "-r", *args], capture_output=True, text=True)
    return json.loads(out.stdout)


def collect(node, ws, acc):
    """Walk the tree, bucketing windows under their workspace."""
    if node.get("type") == "workspace":
        ws = node.get("name")
    app = node.get("app_id") or (node.get("window_properties") or {}).get("class")
    if app and ws is not None:
        acc.setdefault(ws, []).append(
            {"app": app, "title": node.get("name") or app, "focused": node.get("focused", False)}
        )
    for key in ("nodes", "floating_nodes"):
        for child in node.get(key, []):
            collect(child, ws, acc)


def ws_sort_key(name):
    """Numeric workspaces first, in numeric order; named ones after, alphabetically."""
    try:
        return (0, int(name.split(":")[0]))
    except ValueError:
        return (1, name)


def shorten(text, limit):
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build(acc, title_limit):
    """Render one layout tier. title_limit of 0 means icon-only.

    Returns (markup, visible_length). Length counts only what the user sees,
    so it can be compared against the character budget.
    """
    groups = []
    length = 0
    for ws in sorted(acc, key=ws_sort_key):
        wins = acc[ws]
        if not wins:
            continue
        parts = []
        for w in wins:
            icon = ICONS.get(w["app"], DEFAULT_ICON)
            text = icon if title_limit == 0 else f"{icon} {shorten(w['title'], title_limit)}"
            length += len(text) + 2          # + the padding spaces
            label = html.escape(text)
            if w["focused"]:
                parts.append(f"<span background='{FOCUS_BG}' color='{FOCUS_FG}'> {label} </span>")
            else:
                parts.append(f"<span color='{DIM}'> {label} </span>")
        num = html.escape(str(ws))
        length += len(str(ws)) + 2
        groups.append(f"<span color='{WS_COLOR}'><b>{num}</b></span>{''.join(parts)}")
    return "  ".join(groups), length


def render():
    acc = {}
    collect(sway("-t", "get_tree"), None, acc)
    # the scratchpad is not a real workspace
    acc.pop("__i3_scratch", None)

    # richest tier that still fits the bar; last one (icon-only) always wins
    for limit in TIERS:
        markup, length = build(acc, limit)
        if length <= MAX_CHARS or limit == TIERS[-1]:
            break

    plain = [
        f"{ws}: " + ", ".join(f"{w['app']} — {w['title']}" for w in acc[ws])
        for ws in sorted(acc, key=ws_sort_key)
        if acc[ws]
    ]
    return {
        "text": markup,
        "tooltip": html.escape("\n".join(plain)) or "No windows",
    }


def emit(last):
    """Render and print, but only when the output actually changed."""
    try:
        payload = render()
    except Exception as exc:  # never let one bad tree kill the module
        payload = {"text": "", "tooltip": f"error: {exc}"}
    line = json.dumps(payload)
    if line == last:
        return last
    try:
        print(line, flush=True)
    except BrokenPipeError:  # waybar went away
        sys.exit(0)
    return line


def main():
    last = emit(None)
    proc = subprocess.Popen(
        ["swaymsg", "-t", "subscribe", "-m", "-r", '["window","workspace"]'],
        stdout=subprocess.PIPE,
        text=True,
    )
    stream = proc.stdout
    while True:
        if not stream.readline():
            break
        # sway emits bursts (focus + title + workspace for one action); drain
        # whatever is already buffered so we walk the tree once, not N times
        while select.select([stream], [], [], DEBOUNCE)[0]:
            if not stream.readline():
                break
        last = emit(last)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
