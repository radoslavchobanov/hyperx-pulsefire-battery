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

    // Device data
    property int batteryLevel: -1
    property bool isCharging: false
    property string connectionMode: ""
    property bool connected: false
    property bool loading: true
    property string lastError: ""

    // Hardware info
    property string firmware: ""
    property string deviceName: ""
    property string vendorId: ""
    property string productId: ""

    // DPI settings
    property var dpiProfiles: []
    property int activeDpiProfile: 0

    // LED settings
    property string ledEffect: ""
    property string ledTarget: ""
    property string ledColor: "#000000"
    property int ledBrightness: 0
    property int ledSpeed: 0

    property string currentTab: "info"

    Plasmoid.icon: Qt.resolvedUrl("../icons/mouse-battery.svg")
    toolTipMainText: "PlasmaNGenuity"
    toolTipSubText: getTooltipText()

    switchWidth: Kirigami.Units.gridUnit * 14
    switchHeight: Kirigami.Units.gridUnit * 16

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
        if (isCharging) return "#54b4ff"
        if (batteryLevel <= 10) return "#ff3c3c"
        if (batteryLevel <= 25) return "#ffa500"
        if (batteryLevel <= 50) return "#ffff00"
        return "#50c850"
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

                // Hardware info
                if (result.hw_info) {
                    root.firmware = result.hw_info.firmware || ""
                    root.deviceName = result.hw_info.device_name || ""
                    root.vendorId = result.hw_info.vendor_id || ""
                    root.productId = result.hw_info.product_id || ""
                }

                // DPI settings
                if (result.dpi) {
                    root.dpiProfiles = result.dpi.profiles || []
                    root.activeDpiProfile = result.dpi.active_profile || 0
                }

                // LED settings
                if (result.led) {
                    root.ledEffect = result.led.effect || ""
                    root.ledTarget = result.led.target || ""
                    root.ledColor = result.led.color || "#000000"
                    root.ledBrightness = result.led.brightness || 0
                    root.ledSpeed = result.led.speed || 0
                }

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

    // Compact representation - square mouse icon with battery fill
    compactRepresentation: Item {
        id: compactRoot

        Layout.minimumWidth: Kirigami.Units.iconSizes.medium
        Layout.minimumHeight: Kirigami.Units.iconSizes.medium
        Layout.preferredWidth: Kirigami.Units.iconSizes.medium
        Layout.preferredHeight: Kirigami.Units.iconSizes.medium

        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }

        Canvas {
            id: mouseCanvas
            anchors.centerIn: parent
            width: Math.min(parent.width, parent.height)
            height: width

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

                // Battery fill
                if (root.connected && root.batteryLevel > 0) {
                    ctx.save();
                    ctx.clip();
                    var fillHeight = (root.batteryLevel / 100.0) * 42 * sy;
                    ctx.fillStyle = getBatteryColor();
                    ctx.fillRect(20 * sx, (52 * sy) - fillHeight, 24 * sx, fillHeight);
                    ctx.restore();
                }

                ctx.strokeStyle = "#787878";
                ctx.lineWidth = 1.5;
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
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.roundRect(29 * sx, 14 * sy, 6 * sx, 10 * sy, 2);
                ctx.fill();
                ctx.stroke();

                // Text or charging bolt
                ctx.fillStyle = "#ffffff";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";

                if (!root.connected || root.batteryLevel < 0) {
                    ctx.font = "bold " + (14 * sy) + "px sans-serif";
                    ctx.fillText("?", 32 * sx, 40 * sy);
                } else if (root.isCharging) {
                    // Lightning bolt
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
                } else {
                    var text = root.batteryLevel.toString();
                    var fontSize = text.length <= 2 ? 10 : 8;
                    ctx.font = "bold " + (fontSize * sy) + "px sans-serif";
                    ctx.fillText(text, 32 * sx, 44 * sy);
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

    // Full representation - tabbed panel
    fullRepresentation: PlasmaExtras.Representation {
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        Layout.minimumHeight: Kirigami.Units.gridUnit * 18
        Layout.preferredWidth: Kirigami.Units.gridUnit * 22
        Layout.preferredHeight: Kirigami.Units.gridUnit * 22

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
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            // Tab bar
            RowLayout {
                Layout.fillWidth: true
                spacing: 2

                Repeater {
                    model: [
                        {id: "info", label: "Info", icon: "dialog-information"},
                        {id: "dpi", label: "DPI", icon: "speedometer"},
                        {id: "led", label: "LED", icon: "preferences-desktop-color"},
                        {id: "buttons", label: "Buttons", icon: "input-mouse"},
                        {id: "settings", label: "Settings", icon: "configure"}
                    ]

                    PlasmaComponents.TabButton {
                        Layout.fillWidth: true
                        text: modelData.label
                        checked: root.currentTab === modelData.id
                        onClicked: root.currentTab = modelData.id
                    }
                }
            }

            // Tab content
            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: {
                    switch(root.currentTab) {
                        case "info": return 0
                        case "dpi": return 1
                        case "led": return 2
                        case "buttons": return 3
                        case "settings": return 4
                        default: return 0
                    }
                }

                // Info Tab
                InfoTab {}

                // DPI Tab
                DpiTab {}

                // LED Tab
                LedTab {}

                // Buttons Tab
                ButtonsTab {}

                // Settings Tab
                SettingsTab {}
            }
        }
    }

    // Info Tab Component
    component InfoTab: ScrollView {
        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            // Battery Status Section
            PlasmaExtras.Heading {
                level: 4
                text: "Battery Status"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.largeSpacing

                // Mouse icon
                Canvas {
                    id: infoMouseCanvas
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 4
                    Layout.preferredHeight: Kirigami.Units.gridUnit * 5

                    onPaint: {
                        var ctx = getContext("2d");
                        var w = width; var h = height;
                        ctx.clearRect(0, 0, w, h);
                        var sx = w / 64; var sy = h / 64;

                        ctx.beginPath();
                        ctx.moveTo(16*sx, 14*sy); ctx.lineTo(16*sx, 52*sy);
                        ctx.quadraticCurveTo(16*sx, 58*sy, 22*sx, 58*sy);
                        ctx.lineTo(42*sx, 58*sy);
                        ctx.quadraticCurveTo(48*sx, 58*sy, 48*sx, 52*sy);
                        ctx.lineTo(48*sx, 14*sy);
                        ctx.quadraticCurveTo(48*sx, 6*sy, 32*sx, 6*sy);
                        ctx.quadraticCurveTo(16*sx, 6*sy, 16*sx, 14*sy);
                        ctx.closePath();
                        ctx.fillStyle = "#3c3c3c"; ctx.fill();

                        if (root.connected && root.batteryLevel > 0) {
                            ctx.save(); ctx.clip();
                            var fh = (root.batteryLevel / 100.0) * 42 * sy;
                            ctx.fillStyle = getBatteryColor();
                            ctx.fillRect(20*sx, (52*sy)-fh, 24*sx, fh);
                            ctx.restore();
                        }
                        ctx.strokeStyle = "#787878"; ctx.lineWidth = 2; ctx.stroke();
                        ctx.beginPath(); ctx.moveTo(32*sx, 8*sy); ctx.lineTo(32*sx, 28*sy);
                        ctx.strokeStyle = "#5a5a5a"; ctx.lineWidth = 1; ctx.stroke();
                        ctx.fillStyle = "#323232"; ctx.strokeStyle = "#8c8c8c";
                        ctx.beginPath(); ctx.roundRect(29*sx, 14*sy, 6*sx, 10*sy, 2);
                        ctx.fill(); ctx.stroke();

                        if (root.isCharging) {
                            ctx.beginPath();
                            ctx.moveTo(36*sx, 32*sy); ctx.lineTo(30*sx, 42*sy);
                            ctx.lineTo(33*sx, 42*sy); ctx.lineTo(28*sx, 54*sy);
                            ctx.lineTo(38*sx, 42*sy); ctx.lineTo(35*sx, 42*sy);
                            ctx.lineTo(40*sx, 32*sy); ctx.closePath();
                            ctx.fillStyle = "#ffdc32"; ctx.fill();
                        }
                    }
                    Connections {
                        target: root
                        function onBatteryLevelChanged() { infoMouseCanvas.requestPaint() }
                        function onIsChargingChanged() { infoMouseCanvas.requestPaint() }
                        function onConnectedChanged() { infoMouseCanvas.requestPaint() }
                    }
                }

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
                        visible: root.connected
                        text: root.isCharging ? "Charging" : "Discharging"
                        color: root.isCharging ? "#54b4ff" : Kirigami.Theme.textColor
                    }

                    // Battery bar
                    Rectangle {
                        Layout.fillWidth: true
                        height: Kirigami.Units.gridUnit * 0.4
                        radius: height / 2
                        color: Kirigami.Theme.backgroundColor
                        border.color: Kirigami.Theme.disabledTextColor
                        border.width: 1
                        visible: root.connected

                        Rectangle {
                            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 2 }
                            width: Math.max(0, (parent.width - 4) * (root.batteryLevel >= 0 ? root.batteryLevel / 100 : 0))
                            radius: height / 2
                            color: getBatteryColor()
                            Behavior on width { NumberAnimation { duration: 300 } }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: Kirigami.Theme.disabledTextColor; opacity: 0.3 }

            // Device Information Section
            PlasmaExtras.Heading {
                level: 4
                text: "Device Information"
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label { text: "Firmware:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.connected ? root.firmware || "---" : "---" }

                PlasmaComponents.Label { text: "Device Name:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.connected ? root.deviceName || "---" : "---" }

                PlasmaComponents.Label { text: "Vendor ID:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.connected ? root.vendorId || "---" : "---" }

                PlasmaComponents.Label { text: "Product ID:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.connected ? root.productId || "---" : "---" }

                PlasmaComponents.Label { text: "Connection:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.connected ? (root.connectionMode.charAt(0).toUpperCase() + root.connectionMode.slice(1)) : "Disconnected" }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // DPI Tab Component
    component DpiTab: ScrollView {
        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            PlasmaExtras.Heading {
                level: 4
                text: "DPI Profiles"
            }

            PlasmaComponents.Label {
                visible: !root.connected
                text: "Connect mouse to view DPI settings"
                opacity: 0.7
            }

            Repeater {
                model: root.dpiProfiles

                Rectangle {
                    Layout.fillWidth: true
                    height: Kirigami.Units.gridUnit * 2.5
                    radius: 4
                    color: modelData.active ? Kirigami.Theme.highlightColor : (modelData.enabled ? Kirigami.Theme.backgroundColor : "transparent")
                    opacity: modelData.enabled ? 1.0 : 0.5
                    border.color: modelData.active ? Kirigami.Theme.highlightColor : Kirigami.Theme.disabledTextColor
                    border.width: modelData.active ? 2 : 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: Kirigami.Units.smallSpacing
                        spacing: Kirigami.Units.smallSpacing

                        Rectangle {
                            width: Kirigami.Units.gridUnit
                            height: Kirigami.Units.gridUnit
                            radius: 2
                            color: modelData.color
                        }

                        PlasmaComponents.Label {
                            text: "Profile " + modelData.index
                            font.bold: modelData.active
                        }

                        Item { Layout.fillWidth: true }

                        PlasmaComponents.Label {
                            text: modelData.dpi + " DPI"
                            font.bold: true
                        }

                        PlasmaComponents.Label {
                            visible: modelData.active
                            text: "(Active)"
                            color: Kirigami.Theme.positiveTextColor
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // LED Tab Component
    component LedTab: ScrollView {
        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            PlasmaExtras.Heading {
                level: 4
                text: "LED Settings"
            }

            PlasmaComponents.Label {
                visible: !root.connected
                text: "Connect mouse to view LED settings"
                opacity: 0.7
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: Kirigami.Units.largeSpacing
                rowSpacing: Kirigami.Units.smallSpacing
                visible: root.connected

                PlasmaComponents.Label { text: "Effect:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.ledEffect || "---" }

                PlasmaComponents.Label { text: "Target:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.ledTarget || "---" }

                PlasmaComponents.Label { text: "Color:"; opacity: 0.7 }
                RowLayout {
                    spacing: Kirigami.Units.smallSpacing
                    Rectangle {
                        width: Kirigami.Units.gridUnit * 1.5
                        height: Kirigami.Units.gridUnit
                        radius: 2
                        color: root.ledColor
                        border.color: Kirigami.Theme.disabledTextColor
                        border.width: 1
                    }
                    PlasmaComponents.Label { text: root.ledColor }
                }

                PlasmaComponents.Label { text: "Brightness:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.ledBrightness + "%" }

                PlasmaComponents.Label { text: "Speed:"; opacity: 0.7 }
                PlasmaComponents.Label { text: root.ledSpeed + "%" }
            }

            Item { Layout.fillHeight: true }
        }
    }

    // Buttons Tab Component
    component ButtonsTab: ScrollView {
        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            PlasmaExtras.Heading {
                level: 4
                text: "Button Mappings"
            }

            PlasmaComponents.Label {
                text: "Button configuration requires the full configuration panel."
                wrapMode: Text.WordWrap
                opacity: 0.7
            }

            PlasmaComponents.Button {
                text: "Open Configuration Panel"
                icon.name: "configure"
                onClicked: executable.connectSource("hyperx-battery-tray &")
            }

            Item { Layout.fillHeight: true }
        }
    }

    // Settings Tab Component
    component SettingsTab: ScrollView {
        ColumnLayout {
            width: parent.width
            spacing: Kirigami.Units.largeSpacing

            PlasmaExtras.Heading {
                level: 4
                text: "Settings"
            }

            PlasmaComponents.Label {
                text: "Polling rate, battery alerts, and other settings require the full configuration panel."
                wrapMode: Text.WordWrap
                opacity: 0.7
            }

            PlasmaComponents.Button {
                text: "Open Configuration Panel"
                icon.name: "configure"
                onClicked: executable.connectSource("hyperx-battery-tray &")
            }

            Item { Layout.fillHeight: true }
        }
    }
}
