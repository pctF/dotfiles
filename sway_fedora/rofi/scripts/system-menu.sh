#!/usr/bin/env bash
# rofi script-mode: replaces the nwg-controls drawer. Utilities + power actions.

if [ -z "$ROFI_RETV" ] || [ "$ROFI_RETV" = "0" ]; then
    printf '\x00urgent\x1f7,8\n'
    printf 'Processes\x00icon\x1futilities-system-monitor\n'
    printf 'Wallpapers\x00icon\x1fpreferences-desktop-wallpaper\n'
    printf 'GTK Settings\x00icon\x1fpreferences-desktop-theme\n'
    printf 'Displays\x00icon\x1fpreferences-desktop-display\n'
    printf 'Shell Settings\x00icon\x1fpreferences-system\n'
    printf 'Lock\x00icon\x1fsystem-lock-screen\n'
    printf 'Logout\x00icon\x1fsystem-log-out\n'
    printf 'Reboot\x00icon\x1fsystem-reboot\n'
    printf 'Shutdown\x00icon\x1fsystem-shutdown\n'
    exit 0
fi

case "$1" in
    Processes)      nwg-processes & disown ;;
    Wallpapers)      azote & disown ;;
    "GTK Settings")  nwg-look & disown ;;
    Displays)        nwg-displays & disown ;;
    "Shell Settings") nwg-shell-config & disown ;;
    Lock)            swaylock -f -c 000000 & disown ;;
    Logout)          swaymsg exit ;;
    Reboot)          systemctl reboot ;;
    Shutdown)        systemctl -i poweroff ;;
esac
