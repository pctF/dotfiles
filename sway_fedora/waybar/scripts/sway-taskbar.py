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

# Nerd Font glyphs, keyed by app_id (wayland) / WM class (x11), lowercased.
#
# Codepoints verified present in Symbols Nerd Font (Fedora nerd-fonts 3.5.0,
# /usr/share/fonts/nerd-fonts/SymbolsNerdFont-Regular.ttf). Re-verify after an
# edit by dumping these escapes against the font cmap with fontTools. Glyphs in
# the U+F0000+ (nf-md-*) plane silently truncate when pasted as literal
# characters, so write those as \U000fXXXX escapes only, never pasted glyphs.
#
# Names follow the nerdfonts.com/cheat-sheet convention: fa- (Font Awesome),
# md- (Material Design), dev- (Devicons), cod- (Codicons), linux- (distro/app),
# custom- (Nerd Fonts originals).
ICONS = {
    # terminals -----------------------------------------------------------
    "foot": "",                    # fa-terminal
    "foot-server": "",
    "footclient": "",
    "kitty": "",
    "alacritty": "",
    "org.wezfurlong.wezterm": "",
    # browsers ----------------------------------------------------------
    "firefox": "",                 # fa-firefox
    "org.mozilla.firefox": "",
    "librewolf": "",
    "chromium": "",                # fa-chrome
    "chromium-browser": "",
    "chrome": "",
    "google-chrome": "",
    "brave-browser": "",
    # editors / IDEs ------------------------------------------------
    "code": "",                    # dev-vscode
    "code-oss": "",
    "codium": "",
    "vscodium": "",
    "jetbrains-idea": "",          # dev-intellij
    "jetbrains-idea-ce": "",
    "idea": "",
    "jetbrains-toolbox": "",       # dev-jetbrains
    "toolbox": "",
    "nvim": "\ue6ae",                 # custom-neovim
    "neovide": "\ue6ae",
    # chat / social ----------------------------------------------
    "org.telegram.desktop": "\ue217",    # fae-telegram
    "telegramdesktop": "\ue217",
    "telegram-desktop": "\ue217",
    "com.mattermost.desktop": "\U000f018e",  # md-card-account-mail (no brand glyph)
    "mattermost": "\U000f018e",
    "slack": "",                   # fa-slack
    "discord": "",                 # fa-discord
    "webcord": "",
    "signal": "",
    # mail --------------------------------------------------------
    "org.mozilla.thunderbird_esr": "󰻧",  # md-email_multiple
    "thunderbird": "󰻧",
    "thunderbird-esr": "󰻧",
    "org.gnome.evolution": "\U000f01ee",       # md-email
    # notes / office --------------------------------------------
    "md.obsidian.obsidian": "\ue6bb",  # custom-obsidian
    "obsidian": "\ue6bb",
    "onlyoffice": "",              # linux-libreoffice
    "onlyoffice-desktopeditors": "",
    "libreoffice": "",
    "libreoffice-writer": "",
    "libreoffice-calc": "",
    "libreoffice-impress": "",
    # media ----------------------------------------------------
    "mpv": "\U000f0381",                 # md-movie
    "vlc": "\U000f057c",                 # md-vlc
    "org.kde.kdenlive": "",        # linux-kdenlive
    "kdenlive": "",
    "obs": "\ueba7",                     # cod-record
    "com.obsproject.studio": "\ueba7",
    "spotify": "",                 # fa-spotify
    # file managers / archives -----------------------------
    "org.gnome.nautilus": "",     # fa-folder
    "nautilus": "",
    "thunar": "",
    "thunar-settings": "",
    "thunar-bulk-rename": "",
    "nemo": "",
    "org.kde.dolphin": "",
    "pcmanfm": "",
    "xarchiver": "\U000f05c4",           # md-zip-box
    "file-roller": "\U000f05c4",
    "org.gnome.fileroller": "\U000f05c4",
    # audio / bluetooth -----------------------------------
    "org.pulseaudio.pavucontrol": "",  # fa-volume-up
    "pavucontrol": "",
    "blueman-manager": "",        # fa-bluetooth
    "blueman-adapters": "",
    ".blueman-manager-wrapped": "",
    # system / settings ----------------------------------
    "nwg-displays": "",           # fa-desktop
    "nwg-look": "\U000f03d8",           # md-palette
    "nwg-clipman": "",            # fa-paste
    "nwg-panel-config": "",       # fa-sliders
    "nwg-shell-config": "",
    "nwg-panel": "",
    "panel-preferences": "",
    "rofi": "",                   # fa-search
    "rofi-theme-selector": "",
    "it.mijorus.gearlever": "\U000f03d3",  # md-package
    "gearlever": "\U000f03d3",
    "org.kde.discover": "",       # fa-store
    "discover": "",
    "org.gnome.diskutility": "",  # fa-hdd-o
    "gnome-disks": "",
    "system-config-printer": "\U000f042a",  # md-printer
    "system-config-language": "",     # fa-language
    "org.freedesktop.gnomeabrt": "",  # fa-bug
    "org.gnome.gnomeabrt": "",
    "setroubleshoot": "",         # fa-shield-halved
    # vpn / secrets ------------------------------------
    "amneziavpn": "\U000f0582",         # md-vpn
    "throne": "\U000f0582",
    "nekoray": "\U000f0582",
    "kse": "\U000f0124",                # md-certificate
    "dqf-license-creator": "\U000f0124",
    "org.keepassxc.keepassxc": "",  # fa-key
    "keepassxc": "",
    "bitwarden": "",
    # kde connect -------------------------------------
    "org.kde.kdeconnect.app": "\U000f0121",  # md-cellphone-link
    "org.kde.kdeconnect.nonplasma": "\U000f0121",
    "kdeconnect": "\U000f0121",
    "org.kde.kdeconnect.sms": "",      # fa-message
    # wallpaper / images -----------------------------
    "azote": "\U000f02e9",              # md-image
    "org.gnome.eog": "\U000f02e9",
    "imv": "\U000f02e9",
    "swappy": "\U000f02e9",
}
DEFAULT_ICON = ""                 # fa-window-maximize


# apps whose windows are always rendered icon-only (no title), regardless of
# the count-based tier -- they're instantly recognisable by glyph. Keys match
# the same way icon lookups do (see _cand_keys).
ICON_ONLY = {
    "org.mozilla.thunderbird_esr", "thunderbird", "thunderbird-esr",
    "md.obsidian.obsidian", "obsidian",
    "com.mattermost.desktop", "mattermost",
    "org.telegram.desktop", "telegramdesktop", "telegram-desktop",
    "com.obsproject.studio", "obs",
}


def _cand_keys(app):
    """Lookup keys to try for an app_id / WM class, most specific first.

    Wayland app_ids are usually reverse-DNS (org.mozilla.thunderbird_esr), so a
    flat dict lookup misses. Yield: the whole id, its last and second-to-last
    dotted segments, and the two joined, each also retried with a common
    packaging suffix stripped. All lowercase.
    """
    a = app.lower()
    cands = [a]
    segs = a.split(".")
    if len(segs) > 1:
        cands += [segs[-1], segs[-2], "-".join(segs[-2:]), ".".join(segs[-2:])]
    for base in list(cands):
        for suf in ("-esr", "_esr", "-bin", "-stable", "-git", "-nightly", "-dev", "-gtk"):
            if base.endswith(suf):
                cands.append(base[: -len(suf)])
    return cands


def icon_for(app):
    """Map an app_id / WM class to a glyph."""
    if not app:
        return DEFAULT_ICON
    for c in _cand_keys(app):
        if c in ICONS:
            return ICONS[c]
    return DEFAULT_ICON


def is_icon_only(app):
    """True if this app should render without a title."""
    return bool(app) and any(c in ICON_ONLY for c in _cand_keys(app))


WS_COLOR = "#81a1c1"      # nord9, workspace number
FOCUS_BG = "#5e81ac"      # matches the clock chip's color
FOCUS_FG = "#eceff4"
DIM = "#9aa5b1"           # muted, recedes against the now-colorful pill bar

# title length by window count: full -> shortened -> icon-only
FULL_UPTO = 6     # <= this many windows: full titles
SHORT_UPTO = 14   # <= this many: shortened titles; more: icons only
TITLE_FULL = 22
TITLE_SHORT = 10
# hard width guard: long titles can overflow the bar well before the count
# thresholds trigger, which squeezes the status modules off the right edge
MAX_CHARS = 275
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


def visible_len(acc, title_limit):
    """Length of what the user actually sees, ignoring markup."""
    n = 0
    for ws, wins in acc.items():
        n += len(str(ws)) + 2
        for w in wins:
            icon = icon_for(w["app"])
            icon_only = title_limit == 0 or is_icon_only(w["app"])
            n += len(icon if icon_only else f"{icon} {shorten(w['title'], title_limit)}") + 2
    return n


def build(acc, title_limit):
    """Render the taskbar. title_limit of 0 means icon-only."""
    groups = []
    for ws in sorted(acc, key=ws_sort_key):
        wins = acc[ws]
        if not wins:
            continue
        parts = []
        for w in wins:
            icon = icon_for(w["app"])
            icon_only = title_limit == 0 or is_icon_only(w["app"])
            text = icon if icon_only else f"{icon} {shorten(w['title'], title_limit)}"
            label = html.escape(text)
            if w["focused"]:
                parts.append(f"<span background='{FOCUS_BG}' color='{FOCUS_FG}'> {label} </span>")
            else:
                parts.append(f"<span color='{DIM}'> {label} </span>")
        num = html.escape(str(ws))
        groups.append(f"<span color='{WS_COLOR}'><b>{num}</b></span>{''.join(parts)}")
    return "  ".join(groups)


def render():
    acc = {}
    collect(sway("-t", "get_tree"), None, acc)
    # the scratchpad is not a real workspace
    acc.pop("__i3_scratch", None)

    # only windows that will actually carry a title drive the tier choice --
    # icon-only apps take negligible width, so a wall of chat clients shouldn't
    # collapse everyone else to glyphs
    total = sum(
        1 for wins in acc.values() for w in wins if not is_icon_only(w["app"])
    )
    if total <= FULL_UPTO:
        limit = TITLE_FULL
    elif total <= SHORT_UPTO:
        limit = TITLE_SHORT
    else:
        limit = 0          # icon-only

    # step down further if the chosen tier would still overflow the bar
    for candidate in (limit, TITLE_SHORT, 0):
        if candidate > limit:
            continue
        limit = candidate
        if visible_len(acc, limit) <= MAX_CHARS or limit == 0:
            break
    markup = build(acc, limit)

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
