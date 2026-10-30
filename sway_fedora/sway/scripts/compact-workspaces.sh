#!/bin/sh
# Renumber numbered workspaces on the focused output to close gaps.
# `rename workspace` keeps windows, layout and tabs intact.
# Numbers held by other outputs are skipped, since workspace names are global.
# Ascending order is safe: each target number is <= its source and already free.
# Pass --dry-run to print the sway command instead of running it.
cmds=$(swaymsg -t get_workspaces | jq -r '
  (.[] | select(.focused).output) as $out
  | ([.[] | select(.output != $out and .num > 0) | .num]) as $taken
  | ([range(1; 100)] - $taken) as $free
  | [.[] | select(.output == $out and .num > 0)] | sort_by(.num)
  | [to_entries[] | $free[.key] as $n | select(.value.num != $n)
     | "rename workspace \"\(.value.name)\" to \"\(.value.name | sub("^[0-9]+"; "\($n)"))\""]
  | join("; ")')

[ -z "$cmds" ] && exit 0
[ "$1" = "--dry-run" ] && { echo "$cmds"; exit 0; }
swaymsg "$cmds"
