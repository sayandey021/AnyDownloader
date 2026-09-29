import QtQuick

Rectangle {
    id: root

    property string message: ""
    property string toastType: "info"  // "info", "success", "warning", "error"

    function show(msg, type) {
        message = msg
        toastType = type || "info"
        opacity = 1.0
        y = parent.height - height - 24
        dismissTimer.restart()
    }

    width: Math.min(Math.max(contentRow.implicitWidth + 32, 200), parent.width - 40)
    height: 44
    radius: 12
    anchors.horizontalCenter: parent.horizontalCenter
    y: parent.height + 20
    opacity: 0.0

    color: appController.surfaceVariantColor
    border.width: 1
    border.color: {
        if (toastType === "success") return appController.successColor
        if (toastType === "error") return appController.errorColor
        if (toastType === "warning") return "#f59e0b"
        return appController.primaryColor
    }

    Behavior on y { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }
    Behavior on opacity { NumberAnimation { duration: 200 } }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 10

        Text {
            text: {
                if (toastType === "success") return "✔"
                if (toastType === "error") return "✖"
                if (toastType === "warning") return "⚠"
                return "ℹ"
            }
            font.pixelSize: 15
            color: root.border.color
            anchors.verticalCenter: parent.verticalCenter
        }

        Text {
            text: root.message
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            font.weight: Font.Medium
            color: appController.textPrimaryColor
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Timer {
        id: dismissTimer
        interval: 3200
        repeat: false
        onTriggered: {
            root.opacity = 0.0
            root.y = root.parent.height + 20
        }
    }
}
