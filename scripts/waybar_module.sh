#!/usr/bin/env bash
# Waybar custom module for HyperX mouse battery.
#
# Add to your waybar config:
#
#   "custom/hyperx": {
#       "exec": "waybar_module.sh",
#       "return-type": "json",
#       "interval": 60,
#       "format": "{icon} {}",
#       "format-icons": ["", "", "", "", ""],
#       "on-click": "hyperx-battery-notify"
#   }

RESULT=$(hyperx-battery --json 2>&1)

if echo "$RESULT" | grep -q '"error"'; then
    echo '{"text": "N/A", "tooltip": "Mouse not connected", "class": "disconnected"}'
else
    BATTERY=$(echo "$RESULT" | grep -o '"battery_percent": [0-9]*' | grep -o '[0-9]*')
    CHARGING=$(echo "$RESULT" | grep -o '"is_charging": [a-z]*' | grep -o 'true\|false')

    if [ "$CHARGING" = "true" ]; then
        CLASS="charging"
        TOOLTIP="HyperX Pulsefire Dart: ${BATTERY}% (Charging)"
    elif [ "$BATTERY" -le 10 ]; then
        CLASS="critical"
        TOOLTIP="HyperX Pulsefire Dart: ${BATTERY}% (Critical!)"
    elif [ "$BATTERY" -le 25 ]; then
        CLASS="warning"
        TOOLTIP="HyperX Pulsefire Dart: ${BATTERY}% (Low)"
    else
        CLASS="good"
        TOOLTIP="HyperX Pulsefire Dart: ${BATTERY}%"
    fi

    echo "{\"text\": \"${BATTERY}%\", \"tooltip\": \"$TOOLTIP\", \"class\": \"$CLASS\", \"percentage\": $BATTERY}"
fi
