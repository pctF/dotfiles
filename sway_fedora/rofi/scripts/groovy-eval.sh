#!/usr/bin/env bash
# rofi script-mode: quick Groovy expression evaluator.
# Type an expression + Enter -> result shown & copied to clipboard.
# Select the result again -> re-copy & exit.
# Empty input shows snippets: Enter runs one.

# rofi is launched from the compositor, which never sources SDKMAN's shell init,
# so `groovy` is not on PATH here. Resolve it explicitly.
GROOVY="$(command -v groovy 2>/dev/null)"
if [ -z "$GROOVY" ]; then
    GROOVY="$HOME/.sdkman/candidates/groovy/current/bin/groovy"
fi
export JAVA_HOME="${JAVA_HOME:-$HOME/.sdkman/candidates/java/current}"

evaluate() {
    local expr="$1" result status
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
}

# Everyday one-liners that are easy to forget; they also keep the list the
# same height as the other tabs. Enter runs one, Ctrl+Space copies it into the input to edit.
SNIPPETS=(
    'UUID.randomUUID()'
    'System.currentTimeMillis()'
    '"text".bytes.encodeBase64()'
    'new String("dGV4dA==".decodeBase64())'
    'URLEncoder.encode("a b&c=d", "UTF-8")'
    '"text".sha256()'
    'java.time.Instant.ofEpochMilli(1700000000000)'
    'java.time.LocalDate.now().plusDays(30)'
)

case "$ROFI_RETV" in
0)
    printf '\x00message\x1fType a Groovy expression, or Enter on a snippet (Ctrl+Space to edit it)\n'
    for s in "${SNIPPETS[@]}"; do printf '%s\x00info\x1fsnippet\n' "$s"; done
    ;;
2)
    evaluate "$1"
    ;;
1)
    if [ "$ROFI_INFO" = snippet ]; then
        evaluate "$1"
        exit 0
    fi
    printf '%s' "$1" | wl-copy
    notify-send -t 1500 "Groovy" "Copied: $1" 2>/dev/null
    ;;
esac
