import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string taskId: ""
    property string title: ""
    property string thumbnail: ""
    property bool isAudio: false
    property bool isImage: false
    property string formatId: ""
    property string outputPath: ""
    property string statusText: ""
    property string statusColorKey: "primary"
    property string downloadState: "active"
    property real progress: 0.0
    property string speedText: ""
    property string finalFilepath: ""
    property string logText: ""
    property bool isLive: false
    property var infoMap: null

    signal openLogsRequested(string taskId, string title, string logText)
    signal redownloadRequested(var infoMap)
    signal deleteRequested(string taskId, string title, string finalFilepath)

    width: parent ? parent.width : 600
    height: 94
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
        anchors.margins: 12
        spacing: 14

        // Thumbnail
        Rectangle {
            id: thumbContainer
            width: root.isAudio ? 70 : 100
            height: 70
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
                    if (status === Image.Error) {
                        visible = false
                    }
                }
            }

            // Fallback icon
            Text {
                anchors.centerIn: parent
                visible: !thumbContainer.children[0].visible
                text: root.isAudio ? "🎵" : (root.isImage ? "🖼" : "🎬")
                font.pixelSize: 24
                color: appController.textSecondaryColor
            }
        }

        // Title + Status + Progress
        Column {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - thumbContainer.width - actionsRow.width - 28
            spacing: 6

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
                width: parent.width
                spacing: 12

                Text {
                    text: root.statusText
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 12
                    font.weight: Font.Medium
                    color: {
                        if (root.statusColorKey === "primary") return appController.primaryColor
                        if (root.statusColorKey === "success") return appController.successColor
                        if (root.statusColorKey === "error") return appController.errorColor
                        if (root.statusColorKey === "accent") return appController.accentCyanColor
                        return appController.textSecondaryColor
                    }
                }

                Text {
                    visible: root.speedText !== ""
                    text: root.speedText
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 12
                    color: appController.textSecondaryColor
                }
            }

            ModernProgressBar {
                width: parent.width
                value: root.progress
                barHeight: 4
                fillColor: {
                    if (root.downloadState === "completed") return appController.successColor
                    if (root.downloadState === "error" || root.downloadState === "cancelled") return appController.errorColor
                    if (root.downloadState === "paused") return appController.accentCyanColor
                    return appController.primaryColor
                }
            }
        }

        // Action Buttons
        Row {
            id: actionsRow
            anchors.verticalCenter: parent.verticalCenter
            spacing: 4

            // Re-download / Download again
            Rectangle {
                visible: root.downloadState === "completed" || root.downloadState === "cancelled" || root.downloadState === "error"
                width: 32; height: 32; radius: 8
                color: btnRdMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "⬇"; font.pixelSize: 14; color: appController.primaryColor }
                MouseArea {
                    id: btnRdMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.redownloadRequested(root.infoMap)
                }
                ToolTip.visible: btnRdMouse.containsMouse
                ToolTip.text: "Download Again"
            }

            // Retry
            Rectangle {
                visible: root.downloadState === "cancelled" || root.downloadState === "error"
                width: 32; height: 32; radius: 8
                color: btnRetryMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "🔄"; font.pixelSize: 14; color: appController.primaryColor }
                MouseArea {
                    id: btnRetryMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: downloaderController.retryDownload(root.taskId)
                }
                ToolTip.visible: btnRetryMouse.containsMouse
                ToolTip.text: "Retry Download"
            }

            // Pause
            Rectangle {
                visible: root.downloadState === "active" && !root.isLive
                width: 32; height: 32; radius: 8
                color: btnPauseMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "⏸"; font.pixelSize: 14; color: appController.accentCyanColor }
                MouseArea {
                    id: btnPauseMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: downloaderController.pauseDownload(root.taskId)
                }
                ToolTip.visible: btnPauseMouse.containsMouse
                ToolTip.text: "Pause Download"
            }

            // Resume / Start Now
            Rectangle {
                visible: root.downloadState === "paused" || root.downloadState === "queued"
                width: 32; height: 32; radius: 8
                color: btnResumeMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "▶"; font.pixelSize: 14; color: appController.successColor }
                MouseArea {
                    id: btnResumeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: downloaderController.resumeDownload(root.taskId)
                }
                ToolTip.visible: btnResumeMouse.containsMouse
                ToolTip.text: root.downloadState === "queued" ? "Start Now" : "Resume Download"
            }

            // Stop
            Rectangle {
                visible: root.downloadState === "active" || root.downloadState === "paused"
                width: 32; height: 32; radius: 8
                color: btnStopMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "⏹"; font.pixelSize: 14; color: appController.errorColor }
                MouseArea {
                    id: btnStopMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: downloaderController.stopDownload(root.taskId)
                }
                ToolTip.visible: btnStopMouse.containsMouse
                ToolTip.text: "Stop Download"
            }

            // Open Folder
            Rectangle {
                visible: root.downloadState !== "queued"
                width: 32; height: 32; radius: 8
                color: btnFolderMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "📁"; font.pixelSize: 14; color: appController.textSecondaryColor }
                MouseArea {
                    id: btnFolderMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: downloaderController.openFolder(root.finalFilepath || root.outputPath)
                }
                ToolTip.visible: btnFolderMouse.containsMouse
                ToolTip.text: "Open Folder"
            }

            // View Logs
            Rectangle {
                visible: root.downloadState !== "queued"
                width: 32; height: 32; radius: 8
                color: btnLogMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                Text { anchors.centerIn: parent; text: "📄"; font.pixelSize: 14; color: appController.textSecondaryColor }
                MouseArea {
                    id: btnLogMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.openLogsRequested(root.taskId, root.title, root.logText)
                }
                ToolTip.visible: btnLogMouse.containsMouse
                ToolTip.text: "View Logs"
            }

            // Delete
            Rectangle {
                visible: root.downloadState === "completed" || root.downloadState === "cancelled" || root.downloadState === "error" || root.downloadState === "queued"
                width: 32; height: 32; radius: 8
                color: btnDelMouse.containsMouse ? Qt.rgba(244, 63, 94, 0.15) : "transparent"
                Text { anchors.centerIn: parent; text: "🗑"; font.pixelSize: 14; color: appController.errorColor }
                MouseArea {
                    id: btnDelMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: root.deleteRequested(root.taskId, root.title, root.finalFilepath)
                }
                ToolTip.visible: btnDelMouse.containsMouse
                ToolTip.text: "Delete"
            }
        }
    }
}
