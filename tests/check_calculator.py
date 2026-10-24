#!/usr/bin/env python3
"""Isolated, offscreen calculator: real QML model and UI, private XDG state."""
from pathlib import Path
import os
import json
import time
import re
import shutil
import sys
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    assert (ROOT / 'modules/CalculatorApp.qml').exists(), 'Calculator window is not implemented'
    assert (ROOT / 'components/CalculatorModel.qml').exists(), 'Calculator model is not implemented'
    with tempfile.TemporaryDirectory(prefix='calc-') as tmp, tempfile.TemporaryDirectory(prefix='.r-', dir=ROOT) as runtime_tmp:
        work = Path(tmp)
        source = work / 'source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'calculator-renders', 'calculator-artifacts', '.r-*', work.name))
        shots = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else work / 'shots'
        shots.mkdir(parents=True, exist_ok=True)
        runtime = Path(runtime_tmp)
        (source / 'calculator-test.qml').write_text('''
import QtQuick
import QtTest
import Quickshell
import "components"
import "modules"
import "."
ShellRoot {
    property int step: 0
    property int rendered: 0
    function shot(name, window) { (window || app).panel.grabToImage(image => { check(image.saveToFile(Quickshell.env("CEDAR_SCREENSHOT_DIR") + "/" + name + ".png"), "render saved"); rendered++; }); }
    CalculatorModel { id: calc }
    CalculatorApp { id: app; model: calc; TestCase { id: keyboard; when: false } }
    CalculatorApp { id: wide; model: calc; visible: false; implicitWidth: 480; implicitHeight: 700 }
    CalculatorApp { id: narrow; model: calc; visible: false; implicitWidth: 324; implicitHeight: 432 }
    function check(ok, message) { if (!ok) { console.error("FAIL: " + message); Qt.exit(1); throw new Error(message); } }
    Timer { interval: 150; running: true; repeat: true; onTriggered: {
        switch (step++) {
        case 0:

        check(app.width === 360 && app.height === 560, "compact default is 360x560, got " + app.width + "x" + app.height);
        check(app.panel.scrollView.contentHeight <= app.panel.scrollView.availableHeight, "empty default fits without scrolling");
        check(!app.panel.historyList.visible, "history starts collapsed");
        check(calc.expression === "" && calc.history.length === 0, "starts empty");
        calc.edit("2 + 3 * 4");
        calc.calculate();
        check(calc.result === "14" && calc.error === "", "arithmetic evaluates");
        check(app.panel.resultLabel.text === "Approx. " + calc.result, "visible floating-point approximation cue");
        check(calc.history.length === 1 && calc.history[0].expression === "2 + 3 * 4", "successful history");
        calc.edit("1 / 0");
        check(!calc.calculate() && calc.error.length > 0 && !calc.canCopy, "error never exposes stale result");
        check(calc.history.length === 1, "errors not recorded");
        calc.clear(); calc.append("7"); calc.append("*"); calc.append("8"); calc.calculate();
        check(calc.result === "56" && calc.canCopy, "clear and keypad recover");
        calc.append("+"); calc.append("4"); calc.calculate();
        check(calc.result === "60", "operator continues a result");
        calc.edit("2^1000"); calc.calculate();
        const largeResult = calc.result;
        calc.append("*"); calc.append("2");
        check(calc.expression === "(" + largeResult + ")*2" && calc.calculate() && isFinite(Number(calc.result)) && Number(calc.result) > Number(largeResult), "model chains large scientific result");
        calc.edit("1e-100"); calc.calculate();
        app.panel.press("×"); app.panel.press("2"); app.panel.press("=");
        check(calc.result === "2e-100" && calc.error === "", "keypad chains tiny scientific result");
        calc.append("9");
        check(calc.expression === "9" && !calc.canCopy, "digit starts new calculation");
        calc.backspace(); check(calc.expression === "", "backspace edits");
        calc.edit("123"); calc.calculate(); calc.backspace();
        check(calc.expression === "12" && !calc.canCopy, "backspace edits completed expression");
        calc.edit("a".repeat(257));
        check(calc.inputLimit === 256 && calc.expression.length <= 256 && calc.error.length > 0, "oversized input refused");
        for (let i = 0; i < 35; i++) { calc.edit(String(i)); calc.calculate(); }
        check(calc.history.length === 30 && calc.history[0].result === "34", "history bounded newest first");
        calc.recall(1); check(calc.expression === "33" && !calc.canCopy, "recall editable expression");
        calc.clearHistory(); check(calc.history.length === 0, "forget history");
        check(app.title === "CEDAR Calculator" && app.visible, "real calculator window");
        check(app.panel.input.activeFocus, "expression initially focused");
        app.panel.press("AC"); app.panel.press("6"); app.panel.press("×"); app.panel.press("7"); app.panel.press("=");
        check(calc.result === "42", "visible keypad action path");
        app.panel.copyResult(); check(Quickshell.clipboardText === "42" && app.panel.copied, "clipboard copies result");
        app.panel.handleKey({key: Qt.Key_L, modifiers: Qt.ControlModifier, text: ""});
        check(calc.expression === "", "keyboard clear");
        app.panel.handleKey({key: Qt.Key_7, modifiers: 0, text: "7"});
        calc.edit("8+9");
        app.panel.handleKey({key: Qt.Key_Return, modifiers: 0, text: ""});
        check(calc.result === "17", "Enter calculates");
        calc.clear(); app.panel.input.forceActiveFocus();
        Quickshell.clipboardText = "2 + * 3";
        keyboard.keyClick(Qt.Key_V, Qt.ControlModifier); keyboard.keyClick(Qt.Key_Return);
        check(calc.error.length > 0 && calc.expression === "2 + * 3", "invalid paste preserves useful input");
        app.panel.input.select(4, 6); keyboard.keyClick(Qt.Key_Backspace); keyboard.keyClick(Qt.Key_Return);
        check(calc.error === "" && calc.result === "5", "pasted error recovers by editing without clear");
        calc.clear(); app.panel.input.forceActiveFocus();
        keyboard.keyClick(Qt.Key_2); keyboard.keyClick(Qt.Key_Plus); keyboard.keyClick(Qt.Key_3); keyboard.keyClick(Qt.Key_Return);
        check(calc.result === "5", "real keyboard types and evaluates");
        keyboard.keyClick(Qt.Key_7); keyboard.keyClick(Qt.Key_Return);
        check(calc.expression === "7" && calc.result === "7", "real keyboard starts fresh after result");
        keyboard.keyClick(Qt.Key_Backspace);
        check(calc.expression === "" && !calc.canCopy, "real backspace invalidates result");
        calc.edit("123"); app.panel.input.select(1, 2); app.panel.press("9");
        check(calc.expression === "193", "keypad replaces selected input");
        app.panel.input.cursorPosition = 1; app.panel.press("⌫");
        check(calc.expression === "93", "keypad backspace respects cursor");
        calc.edit("4"); calc.calculate();
        function focused(item) { if (item.activeFocus && item.text !== undefined) return item; for (const child of item.children || []) { const found = focused(child); if (found) return found; } return null; }
        app.panel.input.forceActiveFocus(); keyboard.keyClick(Qt.Key_Tab);
        check(focused(app.panel).text === "Copy result", "Tab reaches copy result");
        keyboard.keyClick(Qt.Key_Tab);
        check(focused(app.panel).text === "AC" && focused(app.panel).visualFocus, "Tab reaches visibly focused clear key");
        keyboard.keyClick(Qt.Key_Right); keyboard.keyClick(Qt.Key_Space);
        check(calc.expression === "(", "Tab, arrows and Space operate keypad with visible focus");
        check(app.panel.input.activeFocus, "keypad returns focus to expression");
        keyboard.keyClick(Qt.Key_Tab);
        check(!app.panel.input.activeFocus, "Tab reaches an accessible action");
        let closed = false; app.dismissRequested.connect(function() { closed = true; });
        keyboard.keyClick(Qt.Key_Escape);
        check(closed, "Escape closes");
            app.panel.historyToggle.forceActiveFocus(Qt.TabFocusReason);
            check(app.panel.historyToggle.visualFocus, "history disclosure has visible keyboard focus");
            keyboard.keyClick(Qt.Key_Space);
            check(app.panel.historyExpanded && app.panel.historyList.visible, "Space expands history");
            keyboard.keyClick(Qt.Key_Space);
            check(!app.panel.historyExpanded && !app.panel.historyList.visible && calc.history.length > 0, "Space collapses history without forgetting it");
            app.panel.historyExpanded = true;
            check(app.panel.historyToggle.checked, "programmatic history change preserves toggle binding");
            app.panel.historyExpanded = false;
        calc.clear(); calc.clearHistory();
        shot("calculator-empty");
        break;
        case 1:
            wide.visible = true;
            calc.edit("(18 + 24) / 7"); calc.calculate();
            break;
        case 2:
            check(app.panel.scrollView.contentHeight <= app.panel.scrollView.availableHeight, "successful default fits without scrolling");
            const bottom = app.panel.keypad.mapToItem(app.panel, 0, app.panel.keypad.height);
            check(bottom.y <= app.height, "all keypad rows visible at default size");
            check(wide.panel.keypad.width > 0 && wide.panel.keypad.width < 480, "keypad fits 480px");
            shot("calculator-480", wide);
            Theme.reducedMotion = true;
            narrow.visible = true;
            break;
        case 3:
            check(narrow.panel.input.width > 0 && narrow.panel.input.width < 324, "input fits narrow window");
            check(narrow.panel.keypad.width > 0 && narrow.panel.keypad.width < 324, "keypad fits narrow window");
            shot("calculator-narrow-reduced-motion", narrow);
            break;
        case 4:
            check(narrow.panel.scrollView.contentHeight > narrow.panel.scrollView.availableHeight, "narrow window scrolls");
            narrow.panel.scrollView.contentItem.contentY = narrow.panel.scrollView.contentHeight - narrow.panel.scrollView.availableHeight;
            calc.edit("1/0"); calc.calculate();
            break;
        case 5:
            check(narrow.panel.scrollView.contentItem.contentY > 0, "lower controls reachable by scrolling");
            shot("calculator-error");
            break;
        case 6:
            check(rendered === 4, "all asynchronous renders complete");
            console.log("PASS: calculator");
            Qt.quit();
        }
    } }
}
''')
        env = {**os.environ, 'CEDAR_TEST': '1', 'QT_QPA_PLATFORM': 'offscreen',
               'QT_QPA_PLATFORMTHEME': 'basic', 'QT_IM_MODULE': 'compose', 'QT_QUICK_CONTROLS_STYLE': 'Basic',
               'QSG_RHI_BACKEND': 'software', 'QSG_RENDER_LOOP': 'basic', 'XDG_RUNTIME_DIR': str(runtime),
               'XDG_CONFIG_HOME': str(work / 'config'), 'XDG_STATE_HOME': str(work / 'state'),
               'XDG_CACHE_HOME': str(work / 'cache'), 'CEDAR_SCREENSHOT_DIR': str(shots)}
        env.pop('WAYLAND_DISPLAY', None)
        result = subprocess.run(['qs', '-p', str(source / 'calculator-test.qml')], env=env,
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        print(output)
        assert result.returncode == 0 and 'PASS: calculator' in output, 'calculator harness failed'
        assert not list((work / 'config').rglob('*')), 'standalone UI wrote configuration: ' + str(list((work / 'config').rglob('*')))
        assert not list((work / 'state').rglob('*')), 'standalone UI wrote state'
        # Smoke the exact standalone entry point, not just the test host.
        preview = subprocess.Popen(['qs', '-p', str(source / 'shell.qml')], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            preview_output, _ = preview.communicate(timeout=2)
            raise AssertionError('preview exited unexpectedly: ' + preview_output)
        except subprocess.TimeoutExpired:
            preview.terminate()
            preview_output, _ = preview.communicate(timeout=5)
        print(preview_output)
        assert 'Configuration Loaded' in preview_output, preview_output
        assert not list((work / 'config').rglob('*')), 'preview wrote configuration'
        assert not list((work / 'state').rglob('*')), 'preview wrote state'
        output += preview_output
        # Real launcher: must return promptly with clean provider response pipes.
        try:
            launched = subprocess.run(['sh', str(source / 'launch.sh')], env=env,
                                      capture_output=True, text=True, timeout=5)
            assert launched.returncode == 0, launched.stderr
            assert launched.stdout == '' and launched.stderr == '', 'launcher polluted response pipes'
            instances = []
            for attempt in range(30):
                listed = subprocess.run(['qs', 'list', '-j', '-p', str(source / 'shell.qml')], env=env,
                                        capture_output=True, text=True, timeout=5)
                if listed.stdout.lstrip().startswith('['):
                    instances = json.loads(listed.stdout)
                if instances:
                    break
                time.sleep(.1)
            assert instances, 'detached calculator did not remain running'
            print('PASS: actual detached launcher returns clean stdout/stderr and stays running')
        finally:
            subprocess.run(['qs', 'kill', '-p', str(source / 'shell.qml')], env=env,
                           capture_output=True, text=True, timeout=5)
        assert not re.search(r'Failed to start IPC|Failed to load configuration|ReferenceError|TypeError|Binding loop|Cannot assign|is not defined|Unable to assign|invalid override|Duplicate signal|FAIL:', output), output


if __name__ == '__main__':
    main()
