#!/usr/bin/env bash
# rofi script-mode: replaces the nwg-controls drawer. Utilities + power actions.

# Fully detach a GUI app so rofi can exit and release its keyboard grab.
launch() {
    setsid -f "$@" >/dev/null 2>&1 </dev/null
}

if [ -z "$ROFI_RETV" ] || [ "$ROFI_RETV" = "0" ]; then
    printf '\x00urgent\x1f6,7\n'
    printf 'Processes\x00icon\x1futilities-system-monitor\n'
    printf 'Wallpapers\x00icon\x1fpreferences-desktop-wallpaper\n'
    printf 'GTK Settings\x00icon\x1fpreferences-desktop-theme\n'
    printf 'Displays\x00icon\x1fpreferences-desktop-display\n'
    printf 'Lock\x00icon\x1fsystem-lock-screen\n'
    printf 'Logout\x00icon\x1fsystem-log-out\n'
    printf 'Reboot\x00icon\x1fsystem-reboot\n'
    printf 'Shutdown\x00icon\x1fsystem-shutdown\n'
    exit 0
fi

case "$1" in
    Processes)        launch nwg-processes ;;
    Wallpapers)       launch azote ;;
    "GTK Settings")   launch nwg-look ;;
    Displays)         launch nwg-displays ;;
    Lock)             launch nwg-lock ;;
    Logout)           swaymsg exit ;;
    Reboot)           systemctl reboot ;;
    Shutdown)         systemctl -i poweroff ;;
esac
