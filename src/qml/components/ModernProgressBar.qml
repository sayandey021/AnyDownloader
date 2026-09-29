import QtQuick

Rectangle {
    id: root

    property real value: 0.0  // 0.0 to 1.0
    property bool indeterminate: false
    property color fillColor: appController.primaryColor
    property color trackColor: appController.surfaceVariantColor
    property int barHeight: 4

    height: barHeight
    radius: barHeight / 2
    color: trackColor
    clip: true

    Rectangle {
        id: fillBar
        height: parent.height
        radius: parent.radius
        color: root.fillColor
        width: root.indeterminate ? parent.width * 0.35 : Math.max(0, Math.min(parent.width, parent.width * root.value))

        Behavior on width {
            enabled: !root.indeterminate
            NumberAnimation { duration: 180; easing.type: Easing.OutQuad }
        }

        // Indeterminate marquee animation
        SequentialAnimation on x {
            running: root.indeterminate
            loops: Animation.Infinite
            NumberAnimation {
                from: -fillBar.width
                to: root.width
                duration: 1200
                easing.type: Easing.InOutQuad
            }
        }
    }
}
