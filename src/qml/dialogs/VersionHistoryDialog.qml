import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    width: 660
    height: 540
    anchors.centerIn: parent
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape

    background: Rectangle {
        radius: 14
        color: appController.surfaceColor
        border.width: 1
        border.color: appController.borderColor
    }

    contentItem: Column {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 14

        Row {
            spacing: 10

            Text {
                text: "📜"
                font.pixelSize: 20
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Version History"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        ScrollView {
            width: parent.width
            height: parent.height - 120
            clip: true

            Column {
                width: parent.width - 12
                spacing: 14

                // v1.9.6
                Text { text: "v1.9.6 (Current — Qt 6 / QML Edition)"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }
                Text {
                    width: parent.width
                    text: "• Migrated from Flet to native PySide6 and Qt 6 / Qt Quick QML for 10x faster rendering and silky-smooth responsiveness.\n• Windows 11 fluent dark design with dynamic vibrant accent system.\n• High-performance asynchronous QML models for instant tab switching.\n• Fully responsive layouts supporting all window sizes with zero stutter.\n• Native Windows desktop integration without child-process overhead."
                    font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 13; color: appController.textSecondaryColor; wrapMode: Text.Wrap
                }

                Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                // v1.9.4
                Text { text: "v1.9.4"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }
                Text {
                    width: parent.width
                    text: "• Fixed backend engine version detection (yt-dlp & spotdl) in packaged executable.\n• Single-instance enforcement: relaunching restores existing window to front.\n• Fixed version string formatting in Settings and force-refresh on manual checks."
                    font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 13; color: appController.textSecondaryColor; wrapMode: Text.Wrap
                }

                Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                // v1.9.1
                Text { text: "v1.9.1"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }
                Text {
                    width: parent.width
                    text: "• Custom frameless Title Bar with native dragging, Windows 11-style controls.\n• Responsive 2-column card grid in History with 16:9 thumbnails and metadata tags.\n• Enhanced floating context menu with color-coded actions."
                    font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 13; color: appController.textSecondaryColor; wrapMode: Text.Wrap
                }

                Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                // v1.9.0
                Text { text: "v1.9.0"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }
                Text {
                    width: parent.width
                    text: "• Backend Engines & Dependencies updater (yt-dlp, spotdl, curl_cffi) with auto-check schedule.\n• SponsorBlock integration for YouTube: automatically cut or mark sponsors, intros, promos.\n• Save with Chapters: preserve and embed chapter markers in downloads.\n• Multi-subtitle embedding: specify multiple languages or 'all'."
                    font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 13; color: appController.textSecondaryColor; wrapMode: Text.Wrap
                }

                Rectangle { width: parent.width; height: 1; color: appController.borderColor }

                // v1.8.0
                Text { text: "v1.8.0"; font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 14; font.weight: Font.Bold; color: appController.primaryColor }
                Text {
                    width: parent.width
                    text: "• PDF and EPUB support added for manga and comic sites.\n• Playlist auto-grouping and subfolders to organize downloads.\n• Expanded site support to 1000+ domains."
                    font.family: "Segoe UI, Inter, sans-serif"; font.pixelSize: 13; color: appController.textSecondaryColor; wrapMode: Text.Wrap
                }
            }
        }

        Row {
            anchors.right: parent.right
            ModernButton {
                text: "Close"
                variant: "primary"
                onClicked: root.close()
            }
        }
    }
}
