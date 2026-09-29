import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    signal openLogsRequested(string taskId, string title, string logText)
    signal redownloadRequested(var infoMap)
    signal deleteRequested(string taskId, string title, string finalFilepath)

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Page Header
        Row {
            width: parent.width

            Text {
                text: "Media Downloader"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 24
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: Math.max(0, parent.width - 340); height: 1 }

            ModernButton {
                text: "Clear Finished"
                variant: "ghost"
                onClicked: {
                    downloaderController.clearFinishedHistory()
                    appController.showToast("Finished downloads cleared", "info")
                }
            }
        }

        // Toolbar: Filter + Pause All, Resume All, Stop All, Open Global Folder
        Rectangle {
            width: parent.width
            height: 52
            radius: 10
            color: appController.surfaceColor
            border.width: 1
            border.color: appController.borderColor

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                ModernDropdown {
                    width: 140
                    customHeight: 34
                    currentValue: "All"
                    model: ["All", "Active", "Paused", "Queued", "Completed", "Stopped", "Error"]
                    anchors.verticalCenter: parent.verticalCenter
                    onActivated: function(idx, val) {
                        downloaderController.setFilter(val)
                    }
                }

                Item { width: Math.max(0, parent.width - 480); height: 1 }

                ModernButton {
                    text: "Pause"
                    variant: "outlined"
                    customHeight: 32
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: downloaderController.pauseAll()
                }

                ModernButton {
                    text: "Resume"
                    variant: "outlined"
                    customHeight: 32
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: downloaderController.resumeAll()
                }

                ModernButton {
                    text: "Stop"
                    variant: "danger"
                    customHeight: 32
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: downloaderController.stopAll()
                }

                ModernButton {
                    text: "Folder"
                    variant: "secondary"
                    customHeight: 32
                    anchors.verticalCenter: parent.verticalCenter
                    onClicked: downloaderController.openGlobalDownloadFolder()
                }
            }
        }

        // Downloads List View
        ListView {
            id: downloadsList
            width: parent.width
            height: parent.height - 130
            clip: true
            spacing: 10
            model: downloaderController.model

            // Empty state placeholder
            Item {
                anchors.centerIn: parent
                visible: downloadsList.count === 0
                width: 260
                height: 140

                Column {
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        text: "📥"
                        font.pixelSize: 36
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: "No Downloads Yet"
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        color: appController.textPrimaryColor
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: "Paste a media link in Search to begin."
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 12
                        color: appController.textSecondaryColor
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }

            delegate: DownloadCard {
                taskId: model.taskId
                title: model.title
                thumbnail: model.thumbnail
                isAudio: model.isAudio
                isImage: model.isImage
                formatId: model.formatId
                outputPath: model.outputPath
                statusText: model.statusText
                statusColorKey: model.statusColorKey
                downloadState: model.downloadState
                progress: model.progress
                speedText: model.speedText
                finalFilepath: model.finalFilepath
                logText: model.logText
                isLive: model.isLive
                infoMap: model.infoMap

                onOpenLogsRequested: function(tId, tTitle, lText) {
                    root.openLogsRequested(tId, tTitle, lText)
                }

                onRedownloadRequested: function(iMap) {
                    root.redownloadRequested(iMap)
                }

                onDeleteRequested: function(tId, tTitle, fPath) {
                    root.deleteRequested(tId, tTitle, fPath)
                }
            }
        }
    }
}
