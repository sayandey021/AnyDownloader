import QtQuick
import QtQuick.Controls

Rectangle {
    id: root
    width: 104
    color: appController.surfaceColor

    // Right subtle border
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: appController.borderColor
    }

    Column {
        anchors.fill: parent
        spacing: 0

        // App Branding Header
        Item {
            width: parent.width
            height: 90

            Column {
                anchors.centerIn: parent
                spacing: 6

                Rectangle {
                    width: 38
                    height: 38
                    radius: 10
                    color: Qt.rgba(1, 1, 1, 0.05)
                    anchors.horizontalCenter: parent.horizontalCenter

                    Text {
                        anchors.centerIn: parent
                        text: "⬇"
                        font.pixelSize: 18
                        color: appController.primaryColor
                    }
                }

                Text {
                    text: "Any\nDownloader"
                    font.family: "Segoe UI, Inter, sans-serif"
                    font.pixelSize: 12
                    font.weight: Font.Bold
                    color: appController.primaryColor
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                    lineHeight: 1.1
                }
            }
        }

        Rectangle {
            width: parent.width - 24
            height: 1
            color: appController.borderColor
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Item { height: 12; width: 1 }

        // Navigation Items
        Repeater {
            model: [
                { index: 0, label: "Search", icon: "🔍" },
                { index: 1, label: "History", icon: "🕒" },
                { index: 2, label: "Downloads", icon: "📥" },
                { index: 3, label: "Settings", icon: "⚙" },
                { index: 4, label: "About", icon: "ℹ" }
            ]

            delegate: Item {
                id: navItem
                width: root.width
                height: 64

                property bool isSelected: appController.currentPage === modelData.index

                Rectangle {
                    id: navBg
                    anchors.fill: parent
                    anchors.leftMargin: 8
                    anchors.rightMargin: 8
                    radius: 10
                    color: navItem.isSelected ? Qt.rgba(1, 1, 1, 0.08) : (itemMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.04) : "transparent")

                    Behavior on color { ColorAnimation { duration: 140 } }

                    // Active indicator bar
                    Rectangle {
                        visible: navItem.isSelected
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        width: 3.5
                        height: 24
                        radius: 2
                        color: appController.primaryColor
                    }

                    Column {
                        anchors.centerIn: parent
                        spacing: 4

                        Text {
                            text: modelData.icon
                            font.pixelSize: 18
                            color: navItem.isSelected ? appController.primaryColor : (itemMouse.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor)
                            anchors.horizontalCenter: parent.horizontalCenter

                            Behavior on color { ColorAnimation { duration: 140 } }
                        }

                        Text {
                            text: modelData.label
                            font.family: "Segoe UI, Inter, sans-serif"
                            font.pixelSize: 11
                            font.weight: navItem.isSelected ? Font.DemiBold : Font.Medium
                            color: navItem.isSelected ? appController.primaryColor : (itemMouse.containsMouse ? appController.textPrimaryColor : appController.textSecondaryColor)
                            anchors.horizontalCenter: parent.horizontalCenter

                            Behavior on color { ColorAnimation { duration: 140 } }
                        }
                    }
                }

                MouseArea {
                    id: itemMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        appController.setPage(modelData.index)
                    }
                }
            }
        }
    }
}
