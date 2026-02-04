/*
 * PlasmaNGenuity - KDE Plasma 6 System Tray Widget
 * Monitor HyperX Pulsefire Dart mouse battery and settings
 */

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents
import org.kde.plasma.extras as PlasmaExtras
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    property int batteryLevel: -1
    property bool isCharging: false
    property string connectionMode: ""
    property bool connected: false
    property bool loading: true
    property string lastError: ""

    Plasmoid.icon: Qt.resolvedUrl("../icons/mouse-battery.svg")
    toolTipMainText: "PlasmaNGenuity"
    toolTipSubText: getTooltipText()

    switchWidth: Kirigami.Units.gridUnit * 10
    switchHeight: Kirigami.Units.gridUnit * 8

    readonly property string backendPath: Qt.resolvedUrl("../code/backend.py").toString().replace("file://", "")

    function getTooltipText() {
        if (!connected) return "Mouse not connected"
        if (batteryLevel < 0) return "Unknown"
        var text = batteryLevel + "%"
        if (isCharging) text += " (Charging)"
        if (connectionMode) text += " • " + connectionMode
        return text
    }

    function getBatteryColor() {
        if (!connected || batteryLevel < 0) return Kirigami.Theme.disabledTextColor
        if (isCharging) return "#54b4ff"  // Blue for charging
        if (batteryLevel <= 10) return "#ff3c3c"  // Red
        if (batteryLevel <= 25) return "#ffa500"  // Orange
        if (batteryLevel <= 50) return "#ffff00"  // Yellow
        return "#50c850"  // Green
    }

    function refresh() {
        root.loading = true
        executable.connectSource("python3 " + backendPath)
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []

        onNewData: (source, data) => {
            var stdout = data["stdout"]
            disconnectSource(source)
            root.loading = false

            if (!stdout || stdout.trim() === "") {
                root.connected = false
                root.lastError = "No output from backend"
                return
            }

            try {
                var result = JSON.parse(stdout)

                if (result.error && !result.connected) {
                    root.connected = false
                    root.lastError = result.error
                    root.batteryLevel = -1
                    return
                }

                root.connected = result.connected || false
                root.batteryLevel = result.battery !== null ? result.battery : -1
                root.isCharging = result.charging || false
                root.connectionMode = result.mode || ""
                root.lastError = ""

            } catch (e) {
                root.connected = false
                root.lastError = "Parse error"
            }
        }
    }

    Timer {
        interval: 60000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: refresh()
    }

    // Compact representation - mouse icon with battery fill
    compactRepresentation: Item {
        id: compactRoot

        Layout.minimumWidth: Kirigami.Units.iconSizes.medium
        Layout.minimumHeight: Kirigami.Units.iconSizes.medium
        Layout.preferredWidth: Layout.minimumWidth
        Layout.preferredHeight: Layout.minimumHeight

        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }

        // Mouse silhouette with battery fill
        Canvas {
            id: mouseCanvas
            anchors.fill: parent
            anchors.margins: 2

            onPaint: {
                var ctx = getContext("2d");
                var w = width;
                var h = height;
                ctx.clearRect(0, 0, w, h);

                // Scale factors
                var sx = w / 64;
                var sy = h / 64;

                // Mouse body path
                ctx.beginPath();
                ctx.moveTo(16 * sx, 14 * sy);
                ctx.lineTo(16 * sx, 52 * sy);
                ctx.quadraticCurveTo(16 * sx, 58 * sy, 22 * sx, 58 * sy);
                ctx.lineTo(42 * sx, 58 * sy);
                ctx.quadraticCurveTo(48 * sx, 58 * sy, 48 * sx, 52 * sy);
                ctx.lineTo(48 * sx, 14 * sy);
                ctx.quadraticCurveTo(48 * sx, 6 * sy, 32 * sx, 6 * sy);
                ctx.quadraticCurveTo(16 * sx, 6 * sy, 16 * sx, 14 * sy);
                ctx.closePath();

                // Body fill (dark)
                ctx.fillStyle = "#3c3c3c";
                ctx.fill();

                // Battery fill
                if (root.connected && root.batteryLevel > 0) {
                    ctx.save();
                    ctx.clip();
                    var fillHeight = (root.batteryLevel / 100.0) * 42 * sy;
                    ctx.fillStyle = getBatteryColor();
                    ctx.fillRect(20 * sx, (52 * sy) - fillHeight, 24 * sx, fillHeight);
                    ctx.restore();
                }

                // Outline
                ctx.strokeStyle = "#787878";
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Divider line
                ctx.beginPath();
                ctx.moveTo(32 * sx, 8 * sy);
                ctx.lineTo(32 * sx, 28 * sy);
                ctx.strokeStyle = "#5a5a5a";
                ctx.lineWidth = 1;
                ctx.stroke();

                // Scroll wheel
                ctx.fillStyle = "#323232";
                ctx.strokeStyle = "#8c8c8c";
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(29 * sx, 14 * sy, 6 * sx, 10 * sy, 2);
                ctx.fill();
                ctx.stroke();

                // Percentage text or question mark
                ctx.fillStyle = "#ffffff";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";

                if (!root.connected || root.batteryLevel < 0) {
                    ctx.font = "bold " + (16 * sy) + "px sans-serif";
                    ctx.fillText("?", 32 * sx, 38 * sy);
                } else if (!root.isCharging) {
                    var text = root.batteryLevel.toString();
                    var fontSize = text.length <= 2 ? 11 : 9;
                    ctx.font = "bold " + (fontSize * sy) + "px sans-serif";
                    ctx.fillText(text, 32 * sx, 42 * sy);
                }

                // Charging bolt
                if (root.isCharging) {
                    ctx.beginPath();
                    ctx.moveTo(36 * sx, 32 * sy);
                    ctx.lineTo(30 * sx, 42 * sy);
                    ctx.lineTo(33 * sx, 42 * sy);
                    ctx.lineTo(28 * sx, 54 * sy);
                    ctx.lineTo(38 * sx, 42 * sy);
                    ctx.lineTo(35 * sx, 42 * sy);
                    ctx.lineTo(40 * sx, 32 * sy);
                    ctx.closePath();
                    ctx.fillStyle = "#ffdc32";
                    ctx.fill();
                    ctx.strokeStyle = "#ffc800";
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }

            Connections {
                target: root
                function onBatteryLevelChanged() { mouseCanvas.requestPaint() }
                function onIsChargingChanged() { mouseCanvas.requestPaint() }
                function onConnectedChanged() { mouseCanvas.requestPaint() }
            }
        }
    }

    // Full representation - popup panel
    fullRepresentation: PlasmaExtras.Representation {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 16
        Layout.minimumHeight: Kirigami.Units.gridUnit * 12
        Layout.preferredWidth: Kirigami.Units.gridUnit * 18
        Layout.preferredHeight: contentLayout.implicitHeight + Kirigami.Units.largeSpacing * 2

        header: PlasmaExtras.PlasmoidHeading {
            RowLayout {
                anchors.fill: parent

                PlasmaExtras.Heading {
                    level: 1
                    text: "HyperX Pulsefire Dart"
                    Layout.fillWidth: true
                }

                PlasmaComponents.ToolButton {
                    icon.name: "view-refresh"
                    onClicked: refresh()
                    PlasmaComponents.ToolTip { text: "Refresh" }
                }
            }
        }

        ColumnLayout {
            id: contentLayout
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            // Connection status section
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                // Mouse icon with battery
                Rectangle {
                    width: Kirigami.Units.gridUnit * 4
                    height: Kirigami.Units.gridUnit * 5
                    color: "transparent"

                    Canvas {
                        id: panelMouseCanvas
                        anchors.fill: parent

                        onPaint: {
                            var ctx = getContext("2d");
                            var w = width;
                            var h = height;
                            ctx.clearRect(0, 0, w, h);

                            var sx = w / 64;
                            var sy = h / 64;

                            // Mouse body
                            ctx.beginPath();
                            ctx.moveTo(16 * sx, 14 * sy);
                            ctx.lineTo(16 * sx, 52 * sy);
                            ctx.quadraticCurveTo(16 * sx, 58 * sy, 22 * sx, 58 * sy);
                            ctx.lineTo(42 * sx, 58 * sy);
                            ctx.quadraticCurveTo(48 * sx, 58 * sy, 48 * sx, 52 * sy);
                            ctx.lineTo(48 * sx, 14 * sy);
                            ctx.quadraticCurveTo(48 * sx, 6 * sy, 32 * sx, 6 * sy);
                            ctx.quadraticCurveTo(16 * sx, 6 * sy, 16 * sx, 14 * sy);
                            ctx.closePath();

                            ctx.fillStyle = "#3c3c3c";
                            ctx.fill();

                            if (root.connected && root.batteryLevel > 0) {
                                ctx.save();
                                ctx.clip();
                                var fillHeight = (root.batteryLevel / 100.0) * 42 * sy;
                                ctx.fillStyle = getBatteryColor();
                                ctx.fillRect(20 * sx, (52 * sy) - fillHeight, 24 * sx, fillHeight);
                                ctx.restore();
                            }

                            ctx.strokeStyle = "#787878";
                            ctx.lineWidth = 2;
                            ctx.stroke();

                            // Divider
                            ctx.beginPath();
                            ctx.moveTo(32 * sx, 8 * sy);
                            ctx.lineTo(32 * sx, 28 * sy);
                            ctx.strokeStyle = "#5a5a5a";
                            ctx.lineWidth = 1;
                            ctx.stroke();

                            // Scroll wheel
                            ctx.fillStyle = "#323232";
                            ctx.strokeStyle = "#8c8c8c";
                            ctx.beginPath();
                            ctx.roundRect(29 * sx, 14 * sy, 6 * sx, 10 * sy, 2);
                            ctx.fill();
                            ctx.stroke();

                            // Charging bolt
                            if (root.isCharging) {
                                ctx.beginPath();
                                ctx.moveTo(36 * sx, 32 * sy);
                                ctx.lineTo(30 * sx, 42 * sy);
                                ctx.lineTo(33 * sx, 42 * sy);
                                ctx.lineTo(28 * sx, 54 * sy);
                                ctx.lineTo(38 * sx, 42 * sy);
                                ctx.lineTo(35 * sx, 42 * sy);
                                ctx.lineTo(40 * sx, 32 * sy);
                                ctx.closePath();
                                ctx.fillStyle = "#ffdc32";
                                ctx.fill();
                            }
                        }

                        Connections {
                            target: root
                            function onBatteryLevelChanged() { panelMouseCanvas.requestPaint() }
                            function onIsChargingChanged() { panelMouseCanvas.requestPaint() }
                            function onConnectedChanged() { panelMouseCanvas.requestPaint() }
                        }
                    }
                }

                // Status info
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    PlasmaComponents.Label {
                        text: root.connected ? (root.batteryLevel >= 0 ? root.batteryLevel + "%" : "Unknown") : "Not Connected"
                        font.pixelSize: Kirigami.Theme.defaultFont.pixelSize * 2
                        font.bold: true
                        color: root.connected ? getBatteryColor() : Kirigami.Theme.disabledTextColor
                    }

                    PlasmaComponents.Label {
                        visible: root.connected && root.isCharging
                        text: "Charging"
                        color: "#54b4ff"
                    }

                    PlasmaComponents.Label {
                        visible: root.connected && root.connectionMode
                        text: root.connectionMode.charAt(0).toUpperCase() + root.connectionMode.slice(1) + " mode"
                        opacity: 0.7
                    }

                    PlasmaComponents.Label {
                        visible: !root.connected
                        text: root.lastError || "Mouse not detected"
                        font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                        opacity: 0.7
                    }
                }
            }

            // Separator
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Kirigami.Theme.disabledTextColor
                opacity: 0.3
            }

            // Battery bar
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: root.connected

                RowLayout {
                    Layout.fillWidth: true

                    PlasmaComponents.Label {
                        text: "Battery Level"
                        font.bold: true
                    }

                    Item { Layout.fillWidth: true }

                    PlasmaComponents.Label {
                        text: root.batteryLevel >= 0 ? root.batteryLevel + "%" : "—"
                        color: getBatteryColor()
                    }
                }

                // Progress bar
                Rectangle {
                    Layout.fillWidth: true
                    height: Kirigami.Units.gridUnit * 0.5
                    radius: height / 2
                    color: Kirigami.Theme.backgroundColor
                    border.color: Kirigami.Theme.disabledTextColor
                    border.width: 1
                    opacity: 0.5

                    Rectangle {
                        anchors {
                            left: parent.left
                            top: parent.top
                            bottom: parent.bottom
                            margins: 2
                        }
                        width: Math.max(0, (parent.width - 4) * (root.batteryLevel >= 0 ? root.batteryLevel / 100 : 0))
                        radius: height / 2
                        color: getBatteryColor()

                        Behavior on width {
                            NumberAnimation { duration: 300; easing.type: Easing.OutQuad }
                        }
                    }
                }
            }

            // Not connected help
            ColumnLayout {
                Layout.fillWidth: true
                visible: !root.connected
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    text: "Make sure the wireless dongle is plugged in, or connect via USB cable."
                    wrapMode: Text.WordWrap
                    font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                    opacity: 0.6
                }
            }

            Item { Layout.fillHeight: true }

            // Action buttons
            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Button {
                    Layout.fillWidth: true
                    text: "Configuration Panel"
                    icon.name: "configure"
                    visible: root.connected
                    onClicked: {
                        var proc = executable.connectSource("hyperx-battery-tray &")
                    }
                }

                PlasmaComponents.Button {
                    Layout.fillWidth: true
                    text: "Refresh"
                    icon.name: "view-refresh"
                    onClicked: refresh()
                }
            }
        }
    }
}
