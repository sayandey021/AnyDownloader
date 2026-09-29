import QtQuick
import QtQuick.Controls

Item {
    id: root

    property string text: ""
    property string iconSource: ""
    property string variant: "primary"  // "primary", "secondary", "outlined", "ghost", "danger", "success"
    property bool enabled: true
    property int customRadius: 10
    property int customPaddingHorizontal: 16
    property int customHeight: 38
    property string tooltipText: ""

    signal clicked()

    implicitWidth: Math.max(contentRow.implicitWidth + (customPaddingHorizontal * 2), 60)
    implicitHeight: customHeight
    opacity: enabled ? 1.0 : 0.5

    function getBgColor() {
        if (variant === "primary") {
            return mouseArea.containsMouse ? appController.primaryHoverColor : appController.primaryColor
        } else if (variant === "danger") {
            return mouseArea.containsMouse ? "#dc2626" : appController.errorColor
        } else if (variant === "success") {
            return mouseArea.containsMouse ? "#059669" : appController.successColor
        } else if (variant === "secondary") {
            return mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : appController.surfaceVariantColor
        } else if (variant === "outlined") {
            return mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.06) : "transparent"
        } else {
            // ghost
            return mouseArea.containsMouse ? Qt.rgba(1, 1, 1, 0.08) : "transparent"
        }
    }

    function getTextColor() {
        if (variant === "primary" || variant === "danger" || variant === "success") {
            return "#ffffff"
        } else if (variant === "outlined") {
            return mouseArea.containsMouse ? appController.primaryColor : appController.textPrimaryColor
        } else {
            return mouseArea.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor
        }
    }

    Rectangle {
        id: bgRect
        anchors.fill: parent
        radius: root.customRadius
        color: root.getBgColor()
        border.width: root.variant === "outlined" ? 1 : 0
        border.color: mouseArea.containsMouse ? appController.primaryColor : appController.borderColor

        scale: mouseArea.pressed ? 0.97 : 1.0
        Behavior on scale { NumberAnimation { duration: 90; easing.type: Easing.OutQuad } }
        Behavior on color { ColorAnimation { duration: 130 } }
        Behavior on border.color { ColorAnimation { duration: 130 } }
    }

    Row {
        id: contentRow
        anchors.centerIn: parent
        spacing: 8

        Image {
            id: btnIcon
            visible: root.iconSource !== ""
            source: root.iconSource
            width: 16
            height: 16
            anchors.verticalCenter: parent.verticalCenter
            fillMode: Image.PreserveAspectFit
        }

        Text {
            id: btnText
            visible: root.text !== ""
            text: root.text
            color: root.getTextColor()
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 13
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root.enabled
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            if (root.enabled) {
                root.clicked()
            }
        }
    }

    ToolTip.visible: root.tooltipText !== "" && mouseArea.containsMouse
    ToolTip.text: root.tooltipText
    ToolTip.delay: 500
}
