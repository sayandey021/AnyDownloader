import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string itemType: "download"  // "download" or "search"
    property string taskId: ""
    property string title: ""
    property string thumbnail: ""
    property string url: ""
    property bool isAudio: false
    property string finalFilepath: ""
    property string outputPath: ""
    property string downloadState: ""
    property string formattedDate: ""
    property string formattedSize: ""
    property string formatBadge: ""
    property var rawData: null

    signal searchAgainRequested(string url)
    signal redownloadRequested(var rawData)
    signal deleteRequested(string itemType, string identifier)

    width: parent ? parent.width : 340
    height: 90
    radius: 12
    color: cardMouse.containsMouse ? appController.surfaceCardColor : appController.surfaceColor
    border.width: 1
    border.color: cardMouse.containsMouse ? appController.primaryColor : appController.borderColor

    Behavior on color { ColorAnimation { duration: 130 } }
    Behavior on border.color { ColorAnimation { duration: 130 } }

    MouseArea {
        id: cardMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Row {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 12

        // Thumbnail
        Rectangle {
            id: thumbRect
            width: root.isAudio ? 68 : 88
            height: 68
            radius: 8
            color: appController.surfaceVariantColor
            clip: true
            anchors.verticalCenter: parent.verticalCenter

            Image {
                anchors.fill: parent
                source: root.thumbnail !== "" ? root.thumbnail : ""
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: status === Image.Ready

                onStatusChanged: {
                    if (status === Image.Error) visible = false
                }
            }

            Text {
                anchors.centerIn: parent
                visible: !thumbRect.children[0].visible
                text: root.itemType === "search" ? "🔍" : (root.isAudio ? "🎵" : "🎬")
                font.pixelSize: 22
                color: appController.textSecondaryColor
            }
        }

        // Details Column
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - thumbRect.width - actionsRow.width - 24
            spacing: 5

            Text {
                width: parent.width
                text: root.title
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: appController.textPrimaryColor
                elide: Text.ElideRight
            }

            Row {
                spacing: 8

                // Badge
                Rectangle {
                    height: 18
                    width: badgeText.implicitWidth + 10
                    radius: 4
                    color: Qt.rgba(1, 1, 1, 0.08)

                    Text {
                        id: badgeText
                        anchors.centerIn: parent
                        text: root.formatBadge
                        font.pixelSize: 10
                        font.weight: Font.Bold
                        color: appController.primaryColor
                    }
                }

                Text {
                    visible: root.formattedSize !== ""
                    text: root.formattedSize
                    font.pixelSize: 11
                    color: appController.accentCyanColor
                }

                Text {
                    text: root.formattedDate
                    font.pixelSize: 11
                    color: appController.textSecondaryColor
                }
            }
        }

        // Action buttons
        Row {
            id: actionsRow
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            // If search: Search Again
            Rectangle {
                visible: root.itemType === "search"
                width: 30; height: 30; radius: 6
                color: btnSearchMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "🔍"; font.pixelSize: 13; color: appController.primaryColor }
                MouseArea {
                    id: btnSearchMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.searchAgainRequested(root.url)
                }
                ToolTip.visible: btnSearchMouse.containsMouse
                ToolTip.text: "Search Again"
            }

            // If download: Play/Open File
            Rectangle {
                visible: root.itemType === "download" && root.finalFilepath !== ""
                width: 30; height: 30; radius: 6
                color: btnPlayMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "▶"; font.pixelSize: 13; color: appController.successColor }
                MouseArea {
                    id: btnPlayMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: historyController.openFile(root.finalFilepath)
                }
                ToolTip.visible: btnPlayMouse.containsMouse
                ToolTip.text: "Play / Open File"
            }

            // If download: Open Folder
            Rectangle {
                visible: root.itemType === "download"
                width: 30; height: 30; radius: 6
                color: btnFolderMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "📁"; font.pixelSize: 13; color: appController.textSecondaryColor }
                MouseArea {
                    id: btnFolderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: historyController.openFolder(root.finalFilepath || root.outputPath)
                }
                ToolTip.visible: btnFolderMouse.containsMouse
                ToolTip.text: "Open Folder"
            }

            // Delete
            Rectangle {
                width: 30; height: 30; radius: 6
                color: btnDelMouse.containsMouse ? Qt.rgba(244, 63, 94, 0.15) : "transparent"
                Text { anchors.centerIn: parent; text: "🗑"; font.pixelSize: 13; color: appController.errorColor }
                MouseArea {
                    id: btnDelMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (root.itemType === "download") {
                            root.deleteRequested("download", root.taskId)
                        } else {
                            root.deleteRequested("search", root.url)
                        }
                    }
                }
                ToolTip.visible: btnDelMouse.containsMouse
                ToolTip.text: "Remove from History"
            }
        }
    }
}
