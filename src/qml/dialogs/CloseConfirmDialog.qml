import QtQuick
import QtQuick.Controls
import "../components"

Popup {
    id: root

    property bool rememberChoice: false

    width: 460
    height: 220
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
                text: "🚪"
                font.pixelSize: 20
                color: appController.primaryColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "Close Application"
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 18
                font.weight: Font.Bold
                color: appController.textPrimaryColor
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Text {
            width: parent.width
            text: "Do you want to minimize to the system tray or exit the application?"
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            color: appController.textSecondaryColor
            wrapMode: Text.Wrap
        }

        CheckBox {
            id: rememberCb
            text: "Remember my choice"
            checked: root.rememberChoice
            onToggled: root.rememberChoice = checked

            contentItem: Text {
                text: rememberCb.text
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                color: appController.textSecondaryColor
                leftPadding: rememberCb.indicator.width + 8
                verticalAlignment: Text.AlignVCenter
            }
        }

        Item { height: 4; width: 1 }

        Row {
            anchors.right: parent.right
            spacing: 10

            ModernButton {
                text: "Cancel"
                variant: "ghost"
                onClicked: root.close()
            }

            ModernButton {
                text: "Exit App"
                variant: "danger"
                onClicked: {
                    root.close()
                    appController.confirmClose("exit", root.rememberChoice)
                }
            }

            ModernButton {
                text: "Minimize to Tray"
                variant: "primary"
                onClicked: {
                    root.close()
                    appController.confirmClose("tray", root.rememberChoice)
                }
            }
        }
    }
}
