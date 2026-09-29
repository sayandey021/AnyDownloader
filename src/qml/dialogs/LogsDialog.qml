import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    property string taskId: ""
    property string itemTitle: ""
    property string logContent: ""

    width: 680
    height: 500
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
        anchors.margins: 18
        spacing: 14

        Row {
            width: parent.width
            spacing: 10

            Text {
                text: "📄"
                font.pixelSize: 18
                anchors.verticalCenter: parent.verticalCenter
            }

            Column {
                width: parent.width - 32
                spacing: 2

                Text {
                    text: "Download Logs"
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 16
                    font.weight: Font.Bold
                    color: appController.textPrimaryColor
                }

                Text {
                    width: parent.width
                    text: root.itemTitle
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 11
                    color: appController.textSecondaryColor
                    elide: Text.ElideRight
                }
            }
        }

        Rectangle {
            width: parent.width
            height: 1
            color: appController.borderColor
        }

        // Log viewer text area
        Rectangle {
            width: parent.width
            height: parent.height - 110
            radius: 8
            color: "#080c16"
            border.width: 1
            border.color: appController.borderColor

            ScrollView {
                id: logScroll
                anchors.fill: parent
                anchors.margins: 10
                clip: true

                TextArea {
                    id: logTextArea
                    text: root.logContent
                    readOnly: true
                    color: "#94a3b8"
                    font.family: "Consolas, 'Cascadia Code', monospace"
                    font.pixelSize: 11
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    background: null
                }
            }
        }

        // Bottom action buttons
        Row {
            anchors.right: parent.right
            spacing: 10

            ModernButton {
                text: "Copy Logs"
                variant: "secondary"
                onClicked: {
                    logTextArea.selectAll()
                    logTextArea.copy()
                    appController.showToast("Logs copied to clipboard!", "success")
                }
            }

            ModernButton {
                text: "Close"
                variant: "primary"
                onClicked: root.close()
            }
        }
    }
}
