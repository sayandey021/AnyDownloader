import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    property string taskId: ""
    property string itemTitle: ""
    property string finalFilepath: ""
    property bool deleteFileFromDisk: false

    width: 460
    height: (finalFilepath !== "" ? 220 : 180)
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
                text: "🗑"
                font.pixelSize: 20
                color: appController.errorColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Remove Download"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            width: parent.width
            text: "Are you sure you want to remove \"" + root.itemTitle + "\" from your downloads list?"
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            color: appController.textSecondaryColor
            wrapMode: Text.Wrap
            elide: Text.ElideRight
            maximumLineCount: 2
        }

        CheckBox {
            id: delDiskCb
            visible: root.finalFilepath !== ""
            text: "Also delete downloaded file from storage"
            checked: root.deleteFileFromDisk
            onToggled: root.deleteFileFromDisk = checked

            contentItem: Text {
                text: delDiskCb.text
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                color: appController.errorColor
                leftPadding: delDiskCb.indicator.width + 8
                verticalAlignment: Text.AlignVCenter
            }
        }

        Row {
            anchors.right: parent.right
            spacing: 10

            ModernButton {
                text: "Cancel"
                variant: "ghost"
                onClicked: root.close()
            }

            ModernButton {
                text: "Delete"
                variant: "danger"
                onClicked: {
                    root.close()
                    downloaderController.deleteDownload(root.taskId, root.deleteFileFromDisk)
                    appController.showToast("Item deleted", "info")
                }
            }
        }
    }
}
