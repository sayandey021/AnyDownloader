import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    property string currentFilter: "all"

    signal searchAgainRequested(string url)
    signal redownloadRequested(var rawData)

    Column {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        // Page Header + Segmented filter + Clear
        Row {
            width: parent.width

            Text {
                text: "History"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 24
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Item { width: Math.max(0, parent.width - 480); height: 1 }

            // Segmented Filter Bar
            Rectangle {
                height: 36
                width: 250
                radius: 8
                color: appController.surfaceColor
                border.width: 1
                border.color: appController.borderColor
                anchors.verticalCenter: parent.verticalCenter

                Row {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 2

                    Repeater {
                        model: [
                            { key: "all", label: "All" },
                            { key: "downloads", label: "Downloads" },
                            { key: "searches", label: "Searches" }
                        ]

                        delegate: Rectangle {
                            width: (parent.width - 4) / 3
                            height: parent.height
                            radius: 6
                            color: root.currentFilter === modelData.key ? appController.primaryColor : "transparent"

                            Behavior on color { ColorAnimation { duration: 120 } }

                            Text {
                                anchors.centerIn: parent
                                text: modelData.label
                                font.family: "Segoe UI, Inter, sans-serif"
                                font.pixelSize: 12
                                font.weight: root.currentFilter === modelData.key ? Font.Bold : Font.Medium
                                color: root.currentFilter === modelData.key ? "#ffffff" : appController.textSecondaryColor
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    root.currentFilter = modelData.key
                                    historyController.setFilter(modelData.key)
                                }
                            }
                        }
                    }
                }
            }

            ModernButton {
                text: "Clear History"
                variant: "danger"
                customHeight: 36
                anchors.verticalCenter: parent.verticalCenter
                onClicked: {
                    historyController.clearAll()
                    appController.showToast("History cleared", "info")
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        // History Items Grid / List
        GridView {
            id: historyGrid
            width: parent.width
            height: parent.height - 80
            clip: true
            cellWidth: parent.width > 900 ? parent.width / 2 : parent.width
            cellHeight: 102
            model: historyController.model

            // Empty state placeholder
            Item {
                anchors.centerIn: parent
                visible: historyGrid.count === 0
                width: 260
                height: 140

                Column {
                    anchors.centerIn: parent
                    spacing: 10

                    Text {
                        text: "🕒"
                        font.pixelSize: 36
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: "No History Records"
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 16
                        font.weight: Font.Bold
                        color: appController.textPrimaryColor
                        anchors.horizontalCenter: parent.horizontalCenter
                    }

                    Text {
                        text: "Previous searches and downloads will appear here."
                        font.family: "Segoe UI, Inter, sans-serif"
                        font.pixelSize: 12
                        color: appController.textSecondaryColor
                        anchors.horizontalCenter: parent.horizontalCenter
                    }
                }
            }

            delegate: Item {
                width: historyGrid.cellWidth
                height: historyGrid.cellHeight

                HistoryCard {
                    anchors.fill: parent
                    anchors.margins: 5
                    itemType: model.itemType
                    taskId: model.taskId
                    title: model.title
                    thumbnail: model.thumbnail
                    url: model.url
                    isAudio: model.isAudio
                    finalFilepath: model.finalFilepath
                    outputPath: model.outputPath
                    downloadState: model.downloadState
                    formattedDate: model.formattedDate
                    formattedSize: model.formattedSize
                    formatBadge: model.formatBadge
                    rawData: model.rawData

                    onSearchAgainRequested: function(url) {
                        root.searchAgainRequested(url)
                    }

                    onRedownloadRequested: function(rData) {
                        root.redownloadRequested(rData)
                    }

                    onDeleteRequested: function(iType, idVal) {
                        if (iType === "download") {
                            historyController.removeDownload(idVal)
                        } else {
                            historyController.removeSearch(idVal)
                        }
                    }
                }
            }
        }
    }
}
