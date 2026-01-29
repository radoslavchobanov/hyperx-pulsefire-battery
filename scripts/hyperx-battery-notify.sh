#!/usr/bin/env bash
# Desktop notification showing HyperX Pulsefire Dart battery status.
# Requires: notify-send (libnotify)

RESULT=$(hyperx-battery --json 2>&1)

if echo "$RESULT" | grep -q '"error"'; then
    ERROR=$(echo "$RESULT" | grep -o '"error": "[^"]*"' | cut -d'"' -f4)
    notify-send -u critical "HyperX Mouse" "Error: $ERROR" -i input-mouse
else
    BATTERY=$(echo "$RESULT" | grep -o '"battery_percent": [0-9]*' | grep -o '[0-9]*')
    CHARGING=$(echo "$RESULT" | grep -o '"is_charging": [a-z]*' | grep -o 'true\|false')

    if [ "$CHARGING" = "true" ]; then
        ICON="battery-good-charging"
        STATUS="Charging"
    elif [ "$BATTERY" -le 10 ]; then
        ICON="battery-empty"
        STATUS="Low Battery!"
    elif [ "$BATTERY" -le 25 ]; then
        ICON="battery-low"
        STATUS="Low"
    elif [ "$BATTERY" -le 50 ]; then
        ICON="battery-medium"
        STATUS="Medium"
    else
        ICON="battery-full"
        STATUS="Good"
    fi

    notify-send "HyperX Pulsefire Dart" "Battery: ${BATTERY}% ($STATUS)" -i "$ICON"
fi
