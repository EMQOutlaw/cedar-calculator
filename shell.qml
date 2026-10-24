import QtQuick
import Quickshell
import "components"
import "modules"

ShellRoot {
    CalculatorModel { id: session }
    CalculatorApp { model: session; onDismissRequested: Qt.quit() }
}
