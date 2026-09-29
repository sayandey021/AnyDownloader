import QtQuick
import QtQuick.Controls

Item {
    id: root

    property bool checked: false
    property string text: ""
    property string subtitle: ""
    property bool enabled: true
    property string tooltipText: ""

    signal toggled(bool newState)

    implicitWidth: contentRow.implicitWidth
    implicitHeight: Math.max(switchTrack.height, textCol.implicitHeight)
    opacity: enabled ? 1.0 : 0.45

    Row {
        id: contentRow
        spacing: 12
        anchors.verticalCenter: parent.verticalCenter

        Rectangle {
            id: switchTrack
            width: 44
            height: 24
            radius: 12
            anchors.verticalCenter: parent.verticalCenter
            color: root.checked ? appController.primaryColor : appController.surfaceVariantColor
            border.width: 1
            border.color: root.checked ? appController.primaryHoverColor : appController.borderColor

            Behavior on color { ColorAnimation { duration: 180 } }

            Rectangle {
                id: switchThumb
                width: 18
                height: 18
                radius: 9
                color: "#ffffff"
                anchors.verticalCenter: parent.verticalCenter
                x: root.checked ? (switchTrack.width - width - 3) : 3

                Behavior on x { NumberAnimation { duration: 180; easing.type: Easing.OutCubic } }
            }
        }

        Column {
            id: textCol
            visible: root.text !== "" || root.subtitle !== ""
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2

            Text {
                visible: root.text !== ""
                text: root.text
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 13
                font.weight: Font.Medium
                color: appController.textPrimaryColor
            }

            Text {
                visible: root.subtitle !== ""
                text: root.subtitle
                font.family: "Segoe UI, Inter, sans-serif"
                font.pixelSize: 11
                color: appController.textSecondaryColor
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.enabled) {
                root.checked = !root.checked
                root.toggled(root.checked)
            }
        }
    }

    ToolTip.visible: root.tooltipText !== "" && mouseArea.containsMouse
    ToolTip.text: root.tooltipText
    ToolTip.delay: 500
}
