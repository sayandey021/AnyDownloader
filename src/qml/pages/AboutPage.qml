import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    signal openVersionHistoryRequested()

    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 680)
        spacing: 16

        // Logo
        Rectangle {
            width: 76
            height: 76
            radius: 20
            color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 1
            border.color: appController.borderColor
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: "⬇"
                font.pixelSize: 34
                color: appController.primaryColor
            }
        }

        // Title + Version + Author
        Column {
            spacing: 4
            width: parent.width

            Text {
                text: "Any Downloader"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 28
                font.weight: Font.Bold
                color: appController.primaryColor
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: "Version 1.9.6 (PySide6 / QML Edition)"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                color: appController.textSecondaryColor
                anchors.horizontalCenter: parent.horizontalCenter
            }

            Text {
                text: "Developed by Sayan Dey"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: appController.textPrimaryColor
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }

        Text {
            width: Math.min(parent.width, 500)
            text: "A fast and lightweight media and audio download client.\nRebuilt with Python, PySide6, Qt Quick, and yt-dlp."
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            color: appController.textSecondaryColor
            horizontalAlignment: Text.AlignHCenter
            anchors.horizontalCenter: parent.horizontalCenter
            wrapMode: Text.Wrap
        }

        // Action Links
        Flow {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 10

            ModernButton {
                text: "GitHub"
                variant: "secondary"
                onClicked: Qt.openUrlExternally("https://github.com/sayandey021/AnyDownloader")
            }

            ModernButton {
                text: "LinkedIn"
                variant: "secondary"
                onClicked: Qt.openUrlExternally("https://www.linkedin.com/in/sayan-dey021/")
            }

            ModernButton {
                text: "Report a Bug"
                variant: "secondary"
                onClicked: Qt.openUrlExternally("https://github.com/sayandey021/AnyDownloader/issues")
            }

            ModernButton {
                text: "Rate the App"
                variant: "secondary"
                onClicked: Qt.openUrlExternally("ms-windows-store://review/?ProductId=9N8S0WBRF23F")
            }

            ModernButton {
                text: "Version History"
                variant: "outlined"
                onClicked: root.openVersionHistoryRequested()
            }
        }

        Rectangle {
            width: Math.min(parent.width, 450)
            height: 1
            color: appController.borderColor
            anchors.horizontalCenter: parent.horizontalCenter
        }

        // Support on Ko-fi
        Column {
            spacing: 10
            width: parent.width

            Text {
                width: Math.min(parent.width, 460)
                text: "Building free software takes time and passion.\nIf Any Downloader has helped you, please consider supporting its development.\nEvery coffee counts! ☕❤️"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                font.italic: true
                color: appController.textSecondaryColor
                horizontalAlignment: Text.AlignHCenter
                anchors.horizontalCenter: parent.horizontalCenter
                wrapMode: Text.Wrap
            }

            ModernButton {
                text: "Support me on Ko-fi"
                variant: "danger"
                customRadius: 20
                customHeight: 40
                anchors.horizontalCenter: parent.horizontalCenter
                onClicked: Qt.openUrlExternally("https://ko-fi.com/sayandey")
            }
        }
    }
}
