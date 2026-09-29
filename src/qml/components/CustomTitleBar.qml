import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    height: 38
    color: appController.surfaceColor

    property string title: "Any Downloader"

    // Bottom subtle border
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: appController.borderColor
    }

    // Draggable Window Area
    DragHandler {
        target: null
        onActiveChanged: {
            if (active) {
                mainWindow.startSystemMove()
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        anchors.rightMargin: windowControlsRow.width
        onDoubleClicked: {
            appController.maximizeOrRestoreWindow()
        }
    }

    Row {
        id: leftContentRow
        anchors.left: parent.left
        anchors.leftMargin: 14
        anchors.verticalCenter: parent.verticalCenter
        spacing: 10

        Image {
            id: appIcon
            width: 18
            height: 18
            source: "qrc:/assets/icon.png"
            fillMode: Image.PreserveAspectFit
            anchors.verticalCenter: parent.verticalCenter

            // Fallback to local file if not loaded from qrc
            onStatusChanged: {
                if (status === Image.Error) {
                    source = "file:///" + (settingsController.get("default_download_path") ? "" : "") + applicationDirPath + "/assets/icon.png"
                }
            }
        }

        Text {
            text: root.title
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 12
            font.weight: Font.Medium
            color: appController.textSecondaryColor
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    // Window controls: Minimize, Maximize/Restore, Close
    Row {
        id: windowControlsRow
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        spacing: 0

        // Minimize
        Rectangle {
            id: btnMinimize
            width: 46
            height: parent.height
            color: mouseMin.pressed ? Qt.rgba(1, 1, 1, 0.15) : (mouseMin.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent")

            Canvas {
                anchors.centerIn: parent
                width: 10
                height: 10
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = mouseMin.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor
                    ctx.lineWidth = 1.2
                    ctx.beginPath()
                    ctx.moveTo(0, 5)
                    ctx.lineTo(10, 5)
                    ctx.stroke()
                }
                Connections {
                    target: mouseMin
                    function onEntered() { btnMinimize.children[0].requestPaint() }
                    function onExited() { btnMinimize.children[0].requestPaint() }
                }
            }

            MouseArea {
                id: mouseMin
                anchors.fill: parent
                hoverEnabled: true
                onClicked: appController.minimizeWindow()
            }
        }

        // Maximize / Restore
        Rectangle {
            id: btnMaximize
            width: 46
            height: parent.height
            color: mouseMax.pressed ? Qt.rgba(1, 1, 1, 0.15) : (mouseMax.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent")

            Canvas {
                anchors.centerIn: parent
                width: 10
                height: 10
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = mouseMax.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor
                    ctx.lineWidth = 1.2

                    if (appController.isMaximized) {
                        // Restore icon: two overlapping squares
                        ctx.strokeRect(0, 2, 8, 8)
                        ctx.beginPath()
                        ctx.moveTo(2, 2)
                        ctx.lineTo(2, 0)
                        ctx.lineTo(10, 0)
                        ctx.lineTo(10, 8)
                        ctx.lineTo(8, 8)
                        ctx.stroke()
                    } else {
                        // Maximize icon: single square
                        ctx.strokeRect(0, 0, 10, 10)
                    }
                }
                Connections {
                    target: appController
                    function onMaximizedChanged() { btnMaximize.children[0].requestPaint() }
                }
                Connections {
                    target: mouseMax
                    function onEntered() { btnMaximize.children[0].requestPaint() }
                    function onExited() { btnMaximize.children[0].requestPaint() }
                }
            }

            MouseArea {
                id: mouseMax
                anchors.fill: parent
                hoverEnabled: true
                onClicked: appController.maximizeOrRestoreWindow()
            }
        }

        // Close
        Rectangle {
            id: btnClose
            width: 46
            height: parent.height
            color: mouseClose.pressed ? "#c42b1c" : (mouseClose.containsMouse ? "#e81123" : "transparent")

            Canvas {
                anchors.centerIn: parent
                width: 10
                height: 10
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.reset()
                    ctx.strokeStyle = mouseClose.containsMouse ? "#ffffff" : appController.textSecondaryColor
                    ctx.lineWidth = 1.2
                    ctx.beginPath()
                    ctx.moveTo(0, 0)
                    ctx.lineTo(10, 10)
                    ctx.moveTo(10, 0)
                    ctx.lineTo(0, 10)
                    ctx.stroke()
                }
                Connections {
                    target: mouseClose
                    function onEntered() { btnClose.children[0].requestPaint() }
                    function onExited() { btnClose.children[0].requestPaint() }
                }
            }

            MouseArea {
                id: mouseClose
                anchors.fill: parent
                hoverEnabled: true
                onClicked: appController.requestCloseWindow()
            }
        }
    }
}
