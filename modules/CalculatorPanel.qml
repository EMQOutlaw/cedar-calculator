pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import ".."
import "../components"

FocusScope {
    id: root
    required property CalculatorModel model
    signal closed()
    property bool copied: false
    property bool historyExpanded: false
    property alias historyToggle: historyToggle
    property alias resultLabel: resultLabel
    property alias input: expression
    property alias keypad: keys
    property alias historyList: history
    property alias scrollView: scroll
    readonly property var keyLabels: ["AC", "(", ")", "⌫", "7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ".", "%", "+", "^", "="]

    function evaluate() { model.calculate(); expression.forceActiveFocus(); }
    function copyResult() {
        if (!model.canCopy) return;
        Quickshell.clipboardText = model.result;
        copied = true;
    }
    function press(value) {
        copied = false;
        if (value === "=") { evaluate(); return; }
        if (value === "AC") model.clear();
        else if (value === "⌫") {
            if (expression.selectedText) expression.remove(expression.selectionStart, expression.selectionEnd);
            else if (expression.cursorPosition > 0) expression.remove(expression.cursorPosition - 1, expression.cursorPosition);
            model.edit(expression.text);
        } else {
            const token = value === "×" ? "*" : value === "÷" ? "/" : value === "−" ? "-" : value;
            if (model.completed) model.append(token);
            else {
                const start = expression.selectionStart, end = expression.selectionEnd;
                model.edit(expression.text.slice(0, start) + token + expression.text.slice(end));
                expression.cursorPosition = start + token.length;
            }
        }
        expression.forceActiveFocus();
    }
    function handleKey(event) {
        if (event.key === Qt.Key_Escape) { closed(); event.accepted = true; }
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Equal) { evaluate(); event.accepted = true; }
        else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_L) { model.clear(); expression.forceActiveFocus(); event.accepted = true; }
        else if ((event.modifiers & Qt.ControlModifier) && (event.modifiers & Qt.ShiftModifier) && event.key === Qt.Key_C) { copyResult(); event.accepted = true; }
        else if (!(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) && /^[0-9.+*/()%^\-]$/.test(event.text)) {
            if (model.completed || !expression.activeFocus) { press(event.text); event.accepted = true; }
        } else if (event.key === Qt.Key_Backspace && !expression.activeFocus) { model.backspace(); expression.forceActiveFocus(); event.accepted = true; }
    }
    Keys.onPressed: event => handleKey(event)
    Connections { target: root.model; function onExpressionChanged() { root.copied = false; } }
    Component.onCompleted: expression.forceActiveFocus()

    Rectangle { anchors.fill: parent; color: Theme.background }
    ScrollView {
        id: scroll
        ScrollBar.vertical: ScrollBar {
            policy: scroll.contentHeight > scroll.availableHeight ? ScrollBar.AlwaysOn : ScrollBar.AsNeeded
            contentItem: Rectangle { implicitWidth: Theme.spaceXs; radius: Theme.focusInset; color: Theme.muted }
            background: Rectangle { color: Theme.transparent }
        }
        anchors.fill: parent
        anchors.margins: Theme.spaceMd
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: scroll.availableWidth
            spacing: Theme.spaceSm
            RowLayout {
                Layout.fillWidth: true
                Text { text: "CEDAR Calculator"; textFormat: Text.PlainText; font.family: Theme.labelFont; font.pixelSize: Theme.title; color: Theme.text; Layout.fillWidth: true }
                StationButton { text: "Close"; hint: "Close calculator (Escape)"; onClicked: root.closed() }
            }
            ChamferFrame {
                Layout.fillWidth: true
                implicitHeight: readout.implicitHeight + Theme.spaceMd * 2
                fill: Theme.surface; stroke: Theme.border; cut: Theme.chamfer; topLine: true
                ColumnLayout {
                    id: readout
                    anchors.fill: parent; anchors.margins: Theme.spaceMd
                    spacing: Theme.spaceSm
                    Text { text: "EXPRESSION"; textFormat: Text.PlainText; font.family: Theme.dataFont; font.pixelSize: Theme.small; color: Theme.muted }
                    StationField {
                        id: expression
                        objectName: "calculator-expression"
                        Layout.fillWidth: true
                        implicitHeight: Theme.controlHeight
                        font.pixelSize: Theme.normal
                        leftPadding: Theme.spaceMd; rightPadding: Theme.spaceMd
                        placeholderText: "Type a calculation"
                        text: root.model.expression
                        maximumLength: root.model.inputLimit
                        Accessible.name: "Expression"
                        selectByMouse: true
                        onTextEdited: root.model.edit(text)
                        Keys.onPressed: event => root.handleKey(event)
                    }
                    Text {
                        id: resultLabel
                        Layout.fillWidth: true
                        text: root.model.error ? root.model.error : root.model.canCopy ? "Approx. " + root.model.result : "Enter to calculate"
                        textFormat: Text.PlainText
                        font.family: Theme.dataFont
                        font.pixelSize: root.model.canCopy ? Theme.title : Theme.normal
                        color: root.model.error ? Theme.ember : root.model.canCopy ? Theme.green : Theme.muted
                        wrapMode: Text.WrapAnywhere
                        Accessible.role: Accessible.StaticText
                        Accessible.name: text
                    }
                    StationButton {
                        text: root.copied ? "Copied" : "Copy result"
                        hint: "Copy result (Ctrl+Shift+C)"
                        enabled: root.model.canCopy
                        onClicked: root.copyResult()
                    }
                }
            }
            GridLayout {
                id: keys
                objectName: "calculator-keypad"
                Layout.fillWidth: true
                columns: 4; rowSpacing: Theme.spaceXs; columnSpacing: Theme.spaceXs
                Repeater {
                    id: buttons
                    model: root.keyLabels
                    StationButton {
                        required property string modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.columnSpan: modelData === "=" ? 3 : 1
                        implicitHeight: Theme.controlHeight
                        text: modelData
                        checked: modelData === "="
                        accent: modelData === "AC" ? Theme.ember : Theme.teal
                        hint: modelData === "⌫" ? "Backspace" : modelData === "AC" ? "Clear expression (Ctrl+L)" : modelData === "=" ? "Equals (Enter)" : modelData === "^" ? "Power" : modelData === "%" ? "Percent: divide by 100" : modelData
                        onClicked: root.press(modelData)
                        Keys.onPressed: event => {
                            let next = index;
                            if (event.key === Qt.Key_Left) next--;
                            else if (event.key === Qt.Key_Right) next++;
                            else if (event.key === Qt.Key_Up) next -= 4;
                            else if (event.key === Qt.Key_Down) next += 4;
                            else { root.handleKey(event); return; }
                            buttons.itemAt(Math.max(0, Math.min(buttons.count - 1, next))).forceActiveFocus(Qt.TabFocusReason);
                            event.accepted = true;
                        }
                    }
                }
            }
            Text {
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: "Parentheses · powers · % divides by 100"
                textFormat: Text.PlainText; font.family: Theme.dataFont; font.pixelSize: Theme.small; color: Theme.muted
            }
            RowLayout {
                Layout.fillWidth: true
                StationButton {
                    id: historyToggle
                    text: (root.historyExpanded ? "Hide history" : "History") + " (" + root.model.history.length + ")"
                    Layout.fillWidth: true
                    checkable: true
                    checked: root.historyExpanded
                    onClicked: root.historyExpanded = !root.historyExpanded
                    Accessible.description: root.historyExpanded ? "Expanded" : "Collapsed"
                }
                StationButton { visible: root.historyExpanded; text: "Clear history"; enabled: root.model.history.length > 0; onClicked: root.model.clearHistory() }
            }
            Text {
                visible: root.historyExpanded && root.model.history.length === 0
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                text: "Your calculations stay here for this session only."
                textFormat: Text.PlainText; font.family: Theme.labelFont; font.pixelSize: Theme.normal; color: Theme.muted
            }
            ListView {
                id: history
                visible: root.historyExpanded
                Layout.fillWidth: true
                implicitHeight: Math.min(contentHeight, Theme.settingRowHeight * 3)
                clip: true; spacing: Theme.spaceXs
                model: root.model.history
                ScrollBar.vertical: ScrollBar {
                    contentItem: Rectangle { implicitWidth: Theme.spaceXs; radius: Theme.focusInset; color: Theme.muted }
                    background: Rectangle { color: Theme.transparent }
                }
                delegate: StationButton {
                    required property var modelData
                    required property int index
                    width: history.width; implicitHeight: Theme.controlHeight
                    text: modelData.expression + " = " + modelData.result
                    hint: "Recall " + text
                    onClicked: { root.model.recall(index); expression.forceActiveFocus(); expression.cursorPosition = expression.length; }
                }
            }
        }
    }
}
