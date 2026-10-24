pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

// Bundled palette only. No shell configuration, user files or persistence.
Singleton {
    id: root
    property var palette: ({})
    FileView {
        path: Quickshell.shellPath("themes/palettes/cedar.json")
        printErrors: false
        onLoaded: { try { root.palette = JSON.parse(text()).colors || ({}); } catch (_) { root.palette = ({}); } }
    }
    function token(name, fallback) {
        const value = palette[name];
        return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value) ? value : fallback;
    }
    function resolveFont(requested, fallback) { return availableFonts.includes(requested) ? requested : fallback; }
    readonly property color background: token("background", "#080F0D")
    readonly property color surface: token("surface", "#101E19")
    readonly property color border: token("border", "#315C4D")
    readonly property color green: token("green", "#9DFFB0")
    readonly property color teal: token("teal", "#3FE0C5")
    readonly property color ember: token("ember", "#E58B73")
    readonly property color text: token("text", "#E3F2E9")
    readonly property color muted: token("muted", "#A0B9AD")
    readonly property color transparent: Qt.alpha(background, 0)
    readonly property var availableFonts: Qt.fontFamilies()
    property string labelFont: resolveFont("Rajdhani", "sans-serif")
    property string dataFont: resolveFont("JetBrainsMono Nerd Font", "monospace")
    property real fontScale: 1
    readonly property int small: Math.round(12*fontScale)
    readonly property int normal: Math.round(14*fontScale)
    readonly property int title: Math.round(23*fontScale)
    readonly property int spaceXs: 4
    readonly property int spaceSm: 8
    readonly property int spaceMd: 12
    readonly property int spaceLg: 16
    readonly property int spaceXl: 24
    readonly property int controlHeight: 36
    readonly property int settingRowHeight: 52
    readonly property int controlRadius: 8
    readonly property int focusWidth: 2
    readonly property int focusInset: 2
    readonly property int chamfer: 12
    readonly property int transition: 180
    property bool reducedMotion: false
}
