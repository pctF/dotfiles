#!/usr/bin/env bash
# rofi script-mode: IntelliJ recent projects, most recently used first.
# Rows mimic the IDEA welcome screen: colored initials badge, name, path, git branch.

IDEA="$HOME/.local/share/JetBrains/Toolbox/apps/intellij-idea/bin/idea"
BADGES="${XDG_CACHE_HOME:-$HOME/.cache}/rofi-idea-badges"
# IDEA's project colorInfo associatedIndex -> badge color
COLORS=(e5835a c29a1f 8fa35a 3fa27c 5c6ef0 c65ab4 9b5ce8 d45d6c 3b9fc9)

if [ -n "$ROFI_INFO" ]; then
    setsid -f "$IDEA" "$ROFI_INFO" >/dev/null 2>&1 </dev/null
    exit 0
fi

XML=$(ls -1d "$HOME"/.config/JetBrains/IntelliJIdea*/options/recentProjects.xml 2>/dev/null | sort -V | tail -n 1)
[ -f "$XML" ] || exit 0
mkdir -p "$BADGES"
# two-line rows (name / path + branch)
printf '\x00markup-rows\x1ftrue\n\x00delim\x1f\x1e\n'

badge() { # initials, color index -> svg path
    local f="$BADGES/$1-$2.svg"
    [ -f "$f" ] || cat > "$f" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="12" fill="#${COLORS[$2 % ${#COLORS[@]}]}"/><text x="32" y="43" text-anchor="middle" font-family="DejaVu Sans Mono" font-weight="bold" font-size="${3:-26}" fill="#fff">$1</text></svg>
SVG
    echo "$f"
}


# emit "timestamp<TAB>colorIndex<TAB>path" per entry, newest first
awk -v home="$HOME" '
    /<entry key="/ { match($0, /key="[^"]+"/); p = substr($0, RSTART+5, RLENGTH-6); sub(/\$USER_HOME\$/, home, p); ts = 0; ci = 0 }
    /name="activationTimestamp"/ { match($0, /value="[0-9]+"/); ts = substr($0, RSTART+7, RLENGTH-8) }
    /associatedIndex=/ { match($0, /associatedIndex="[0-9]+"/); ci = substr($0, RSTART+17, RLENGTH-18) }
    /<\/entry>/ && p { print ts "\t" ci "\t" p; p = "" }
' "$XML" | sort -rn | while IFS=$'\t' read -r _ ci path; do
    [ -d "$path" ] || continue
    name=${path##*/}
    # IDEA initials: first letter of first and last word
    IFS='-_. ' read -ra w <<< "$name"
    ini=${w[0]:0:1}; [ ${#w[@]} -gt 1 ] && ini+=${w[-1]:0:1}
    ini=${ini^^}
    branch=$(sed -n 's|^ref: refs/heads/||p' "$path/.git/HEAD" 2>/dev/null)
    printf '<b>%s</b>\n<span size="small" alpha="60%%">%s   %s</span>\x00info\x1f%s\x1fmeta\x1f%s %s\x1ficon\x1f%s\x1e' "$name" "${path/#$HOME/\~}" "$branch" "$path" "$path" "$branch" "$(badge "$ini" "$ci")"
done
