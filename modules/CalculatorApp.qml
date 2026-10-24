import QtQuick
import Quickshell
import ".."
import "../components"

FloatingWindow {
    id: root
    required property CalculatorModel model
    signal dismissRequested()
    property alias panel: panel
    title: "CEDAR Calculator"
    color: Theme.background
    implicitWidth: Theme.controlHeight * 10
    implicitHeight: Theme.controlHeight * 15 + Theme.spaceLg + Theme.spaceXs
    minimumSize: Qt.size(Theme.controlHeight * 9, Theme.controlHeight * 12)
    visible: true
    onVisibleChanged: if (!visible) dismissRequested()
    CalculatorPanel { id: panel; anchors.fill: parent; model: root.model; focus: true; onClosed: root.dismissRequested() }
}
