#!/usr/bin/env bash
# rofi script-mode: quick Groovy expression evaluator.
# Type an expression + Enter -> result shown & copied to clipboard.
# Select the result again -> re-copy & exit.

# rofi is launched from the compositor, which never sources SDKMAN's shell init,
# so `groovy` is not on PATH here. Resolve it explicitly.
GROOVY="$(command -v groovy 2>/dev/null)"
if [ -z "$GROOVY" ]; then
    GROOVY="$HOME/.sdkman/candidates/groovy/current/bin/groovy"
fi
export JAVA_HOME="${JAVA_HOME:-$HOME/.sdkman/candidates/java/current}"

case "$ROFI_RETV" in
0)
    printf '\x00message\x1fType a Groovy expression and press Enter\n'
    ;;
2)
    expr="$1"
    result="$("$GROOVY" -e "println(($expr))" 2>&1)"
    status=$?
    if [ "$status" -ne 0 ]; then
        printf '\x00message\x1fError evaluating: %s\n' "$expr"
        printf '%s\n' "$result"
    else
        printf '%s' "$result" | wl-copy
        printf '\x00message\x1f%s = %s  (copied)\n' "$expr" "$result"
        printf '%s\n' "$result"
    fi
    ;;
1)
    printf '%s' "$1" | wl-copy
    notify-send -t 1500 "Groovy" "Copied: $1" 2>/dev/null
    ;;
esac
