#!/bin/sh
# Renumber numbered workspaces on the focused output to close gaps.
# `rename workspace` keeps windows, layout and tabs intact.
# Numbers held by other outputs are skipped, since workspace names are global.
# Numbers pinned to other outputs (`workspace N output X` in ~/.config/sway/workspaces) are skipped too.
# Order avoids collisions: downward moves ascending first, then upward moves descending.
# Pass --dry-run to print the sway command instead of running it.
pinned=$(awk '$1 == "workspace" && $3 == "output" { gsub(/"/, "", $4); printf "{\"num\":%d,\"output\":\"%s\"}\n", $2, $4 }' \
  "$HOME/.config/sway/workspaces" 2>/dev/null | jq -s .)
cmds=$(swaymsg -t get_workspaces | jq -r --argjson pinned "${pinned:-[]}" '
  (.[] | select(.focused).output) as $out
  | ([.[] | select(.output != $out and .num > 0) | .num]
     + [$pinned[] | select(.output != $out) | .num]) as $taken
  | ([range(1; 100)] - $taken) as $free
  | [.[] | select(.output == $out and .num > 0)] | sort_by(.num)
  | [to_entries[] | {ws: .value, n: $free[.key]} | select(.ws.num != .n)]
  | sort_by(if .n < .ws.num then [0, .ws.num] else [1, -.ws.num] end)
  | map(.n as $n | .ws
     | "rename workspace \"\(.name)\" to \"\(.name | sub("^[0-9]+"; "\($n)"))\"")
  | join("; ")')

[ -z "$cmds" ] && exit 0
[ "$1" = "--dry-run" ] && { echo "$cmds"; exit 0; }
swaymsg "$cmds"
