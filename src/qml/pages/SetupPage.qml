import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    property real progressPercent: 0.0
    property string statusMessage: "Initializing..."
    property bool isComplete: false
    property bool isError: false

    signal setupCompleted()

    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 500)
        spacing: 20

        Rectangle {
            width: 76
            height: 76
            radius: 20
            color: root.isComplete ? Qt.rgba(16, 185, 129, 0.1) : Qt.rgba(1, 1, 1, 0.05)
            border.width: 1
            border.color: root.isComplete ? appController.successColor : appController.borderColor
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: root.isComplete ? "✔" : (root.isError ? "✖" : "⚙")
                font.pixelSize: 32
                color: root.isComplete ? appController.successColor : (root.isError ? appController.errorColor : appController.primaryColor)
            }
        }

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: root.isComplete ? "Setup Complete!" : "First Time Setup"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 24
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                width: 440
                text: root.isComplete ? "FFmpeg has been installed successfully.\nYou can now start downloading high quality media." : "Downloading media conversion tools (FFmpeg).\nThis is a one-time process and keeps the app lightweight."
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                color: appController.textSecondaryColor
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
                wrapMode: Text.Wrap
            }
        }

        ModernProgressBar {
            visible: !root.isComplete
            width: 380
            value: root.progressPercent / 100.0
            fillColor: root.isError ? appController.errorColor : appController.primaryColor
            barHeight: 6
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Text {
            text: root.statusMessage
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 12
            color: root.isError ? appController.errorColor : appController.textSecondaryColor
            horizontalAlignment: Text.AlignHCenter
            anchors.horizontalCenter: parent.horizontalCenter
        }

        ModernButton {
            visible: root.isComplete
            text: "Continue to Any Downloader"
            variant: "primary"
            customRadius: 10
            customHeight: 40
            anchors.horizontalCenter: parent.horizontalCenter
            onClicked: root.setupCompleted()
        }
    }
}
