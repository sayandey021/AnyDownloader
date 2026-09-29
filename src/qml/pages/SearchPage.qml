import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: root

    property bool isFetching: false
    property string fetchUrl: ""

    signal openSupportedSitesRequested()

    Connections {
        target: downloaderController
        function onFetchStarted() {
            root.isFetching = true
        }
        function onFetchFinished(info) {
            root.isFetching = false
            fetchDialog.info = info
            fetchDialog.open()
        }
        function onFetchError(errMsg) {
            root.isFetching = false
            appController.showToast(errMsg, "error")
        }
    }

    function doSearch(urlToSearch) {
        if (urlToSearch) {
            urlInput.text = urlToSearch
        }
        var target = urlInput.text.trim()
        if (target !== "") {
            downloaderController.fetchInfo(target)
        } else {
            appController.showToast("Please enter or paste a media link.", "warning")
        }
    }

    // Centered Content
    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 720)
        spacing: 24

        // Big Icon + Glow
        Rectangle {
            width: 84
            height: 84
            radius: 24
            color: Qt.rgba(1, 1, 1, 0.04)
            border.width: 1
            border.color: appController.borderColor
            anchors.horizontalCenter: parent.horizontalCenter

            Text {
                anchors.centerIn: parent
                text: "⚡"
                font.pixelSize: 40
            }
        }

        // Title & Subtitle
        Column {
            spacing: 8
            width: parent.width

            Text {
                width: parent.width
                text: "Download Anything"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 34
                font.weight: Font.Black
                color: appController.textPrimaryColor
                horizontalAlignment: Text.AlignHCenter
            }

            Text {
                width: parent.width
                text: "Paste a link below to instantly download video or audio in high quality."
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 14
                color: appController.textSecondaryColor
                horizontalAlignment: Text.AlignHCenter
            }
        }

        // Search Input Box & Button
        Row {
            width: parent.width
            spacing: 12
            anchors.horizontalCenter: parent.horizontalCenter

            ModernTextField {
                id: urlInput
                width: parent.width - btnSearch.width - 12
                customHeight: 48
                customRadius: 12
                prefixText: "🔗"
                placeholderText: "Paste YouTube, Spotify, Instagram, or any link here..."
                showClearButton: true
                onAccepted: root.doSearch()
            }

            ModernButton {
                id: btnSearch
                customHeight: 48
                customRadius: 12
                text: root.isFetching ? "Searching..." : "Search"
                enabled: !root.isFetching
                onClicked: root.doSearch()
            }
        }

        // Supported Platforms Chips
        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 10

            Repeater {
                model: [
                    { name: "YouTube", icon: "▶" },
                    { name: "Spotify", icon: "🎵" },
                    { name: "Instagram", icon: "📷" },
                    { name: "Twitter / X", icon: "𝕏" },
                    { name: "More...", icon: "•••", isMore: true }
                ]

                delegate: Rectangle {
                    height: 32
                    width: chipRow.implicitWidth + 24
                    radius: 16
                    color: chipMouse.containsMouse ? appController.surfaceVariantColor : appController.surfaceColor
                    border.width: 1
                    border.color: chipMouse.containsMouse ? appController.primaryColor : appController.borderColor

                    Behavior on color { ColorAnimation { duration: 120 } }
                    Behavior on border.color { ColorAnimation { duration: 120 } }

                    Row {
                        id: chipRow
                        anchors.centerIn: parent
                        spacing: 6

                        Text {
                            text: modelData.icon
                            font.pixelSize: 11
                            color: appController.primaryColor
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: modelData.name
                            font.family: "Segoe UI, Inter, sans-serif"
                            font.pixelSize: 12
                            font.weight: Font.Medium
                            color: chipMouse.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }

                    MouseArea {
                        id: chipMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (modelData.isMore) {
                                root.openSupportedSitesRequested()
                            }
                        }
                    }
                }
            }
        }
    }

    // Fetching Loading Overlay Modal
    Popup {
        id: fetchingPopup
        width: 320
        height: 140
        anchors.centerIn: parent
        modal: true
        focus: true
        closePolicy: Popup.NoAutoClose
        visible: root.isFetching

        background: Rectangle {
            radius: 14
            color: appController.surfaceColor
            border.width: 1
            border.color: appController.borderColor
        }

        contentItem: Column {
            anchors.centerIn: parent
            spacing: 14

            Text {
                text: "Fetching Metadata..."
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 15
                font.weight: Font.Bold
                color: appController.textPrimaryColor
            }

            ModernProgressBar {
                width: 240
                indeterminate: true
                barHeight: 4
            }

            ModernButton {
                text: "Cancel"
                variant: "ghost"
                customHeight: 30
                onClicked: {
                    downloaderController.cancelFetch()
                    root.isFetching = false
                }
            }
        }
    }
}
