import QtQuick
import QtQuick.Controls

Item {
    id: root

    property alias text: innerInput.text
    property string placeholderText: ""
    property string label: ""
    property bool readOnly: false
    property bool enabled: true
    property string prefixText: ""
    property string suffixText: ""
    property int customRadius: 10
    property int customHeight: 42
    property bool showClearButton: false

    signal accepted()
    signal textEdited()

    implicitWidth: 320
    implicitHeight: (label !== "" ? 22 : 0) + customHeight

    Column {
        anchors.fill: parent
        spacing: 4

        Text {
            visible: root.label !== ""
            text: root.label
            font.family: "Segoe UI, Inter, sans-serif"
            font.pixelSize: 12
            font.weight: Font.Medium
            color: appController.textSecondaryColor
        }

        Rectangle {
            id: inputBg
            width: parent.width
            height: root.customHeight
            radius: root.customRadius
            color: root.readOnly ? appController.surfaceVariantColor : appController.surfaceColor
            border.width: innerInput.activeFocus ? 1.5 : 1
            border.color: innerInput.activeFocus ? appController.primaryColor : appController.borderColor

            Behavior on border.color { ColorAnimation { duration: 150 } }

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 10
                spacing: 8

                Text {
                    visible: root.prefixText !== ""
                    text: root.prefixText
                    color: appController.textSecondaryColor
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 14
                    anchors.verticalCenter: parent.verticalCenter
                }

                TextInput {
                    id: innerInput
                    width: parent.width - (root.prefixText !== "" ? 24 : 0) - (root.suffixText !== "" ? 40 : 0) - (clearBtn.visible ? 28 : 0)
                    anchors.verticalCenter: parent.verticalCenter
                    color: appController.textPrimaryColor
                    readOnly: root.readOnly
                    enabled: root.enabled
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 13
                    selectByMouse: true
                    selectionColor: appController.primaryColor
                    selectedTextColor: "#ffffff"
                    clip: true

                    Text {
                        anchors.fill: parent
                        text: root.placeholderText
                        color: appController.textSecondaryColor
                        opacity: 0.6
                        font: innerInput.font
                        visible: !innerInput.text && !innerInput.activeFocus
                    }

                    onAccepted: root.accepted()
                    onTextEdited: root.textEdited()
                }

                Text {
                    visible: root.suffixText !== ""
                    text: root.suffixText
                    color: appController.textSecondaryColor
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }

                // Clear button
                Rectangle {
                    id: clearBtn
                    visible: root.showClearButton && innerInput.text !== "" && !root.readOnly
                    width: 20
                    height: 20
                    radius: 10
                    color: clearMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.15) : "transparent"
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        font.pixelSize: 11
                        color: appController.textSecondaryColor
                    }

                    MouseArea {
                        id: clearMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            innerInput.text = ""
                            root.textEdited()
                        }
                    }
                }
            }
        }
    }
}
