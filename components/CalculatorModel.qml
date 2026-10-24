import QtQuick
import "CalculatorEngine.js" as Engine

// One bounded, memory-only session. No persistence, processes or expression eval.
QtObject {
    id: root
    property string expression: ""
    property string result: ""
    property string error: ""
    property var history: []

    property bool completed: false
    readonly property bool canCopy: completed && result !== "" && error === ""
    readonly property int inputLimit: Engine.MAX_LENGTH

    function edit(value) {
        if (value.length > inputLimit) { error = "Expression is too long (maximum " + inputLimit + " characters)."; completed = false; return; }
        expression = value;
        error = "";
        completed = false;
    }
    function append(value) {
        let base = expression;
        if (completed) base = /^[+*/^%\-]/.test(value) ? "(" + result + ")" : "";
        edit(base + value);
    }
    function backspace() { edit(expression.slice(0, -1)); }
    function clear() { edit(""); result = ""; }
    function recall(index) { if (index >= 0 && index < history.length) edit(history[index].expression); }
    function clearHistory() { history = []; }
    function calculate() {
        const answer = Engine.evaluate(expression);
        if (!answer.ok) { error = answer.error; completed = false; return false; }
        result = answer.text;
        error = "";
        completed = true;
        history = [{expression: expression, result: result}].concat(history).slice(0, 30);
        return true;
    }
}
