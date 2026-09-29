import QtQuick
import QtQuick.Controls

Item {
    id: root

    property string label: ""
    property var model: []
    property var currentValue: ""
    property string currentText: ""
    property bool enabled: true
    property int customRadius: 10
    property int customHeight: 40

    signal activated(int index, var value)

    implicitWidth: 240
    implicitHeight: (label !== "" ? 22 : 0) + customHeight

    onModelChanged: updateSelectionFromValue()
    onCurrentValueChanged: updateSelectionFromValue()

    function updateSelectionFromValue() {
        if (!model) return
        for (var i = 0; i < model.length; i++) {
            var item = model[i]
            var val = (typeof item === 'object') ? (item.key !== undefined ? item.key : item.value) : item
            var txt = (typeof item === 'object') ? item.text : item
            if (val === currentValue || String(val) === String(currentValue)) {
                root.currentText = txt
                return
            }
        }
        if (model.length > 0) {
            var first = model[0]
            root.currentText = (typeof first === 'object') ? first.text : first
        }
    }

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
            id: comboButton
            width: parent.width
            height: root.customHeight
            radius: root.customRadius
            color: popup.opened ? appController.surfaceVariantColor : (mouseArea.containsMouse ? appController.surfaceVariantColor : appController.surfaceColor)
            border.width: 1
            border.color: popup.opened ? appController.primaryColor : (mouseArea.containsMouse ? appController.primaryColor : appController.borderColor)

            Behavior on color { ColorAnimation { duration: 120 } }
            Behavior on border.color { ColorAnimation { duration: 120 } }

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Text {
                    width: parent.width - 24
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.currentText
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 13
                    font.weight: Font.Normal
                    color: root.enabled ? appController.textPrimaryColor : appController.textSecondaryColor
                    elide: Text.ElideRight
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: popup.opened ? "▲" : "▼"
                    font.pixelSize: 9
                    color: appController.textSecondaryColor
                }
            }

            MouseArea {
                id: mouseArea
                anchors.fill: parent
                hoverEnabled: root.enabled
                cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                onClicked: {
                    if (root.enabled) {
                        if (popup.opened) popup.close()
                        else popup.open()
                    }
                }
            }
        }
    }

    Popup {
        id: popup
        y: comboButton.y + comboButton.height + 4
        width: comboButton.width
        implicitHeight: Math.min(listView.contentHeight + 12, 260)
        padding: 6
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: root.customRadius
            color: appController.surfaceColor
            border.width: 1
            border.color: appController.borderColor
            // Shadow / elevation
            layer.enabled: true
        }

        contentItem: ListView {
            id: listView
            clip: true
            model: root.model
            spacing: 2
            delegate: Rectangle {
                id: delegateRect
                width: listView.width
                height: 34
                radius: 6

                property var itemData: modelData
                property var itemValue: (typeof itemData === 'object') ? (itemData.key !== undefined ? itemData.key : itemData.value) : itemData
                property string itemText: (typeof itemData === 'object') ? itemData.text : itemData
                property bool isSelected: itemValue === root.currentValue || String(itemValue) === String(root.currentValue)

                color: isSelected ? appController.primaryColor : (delMouse.containsMouse ? appController.surfaceVariantColor : "transparent")

                Behavior on color { ColorAnimation { duration: 100 } }

                Text {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    text: delegateRect.itemText
                    color: delegateRect.isSelected ? "#ffffff" : (delMouse.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor)
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 13
                    font.weight: delegateRect.isSelected ? Font.DemiBold : Font.Normal
                    elide: Text.ElideRight
                }

                MouseArea {
                    id: delMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.currentValue = delegateRect.itemValue
                        root.currentText = delegateRect.itemText
                        popup.close()
                        root.activated(index, delegateRect.itemValue)
                    }
                }
            }
        }
    }
}
