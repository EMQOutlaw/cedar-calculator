# CEDAR Calculator

A standalone native Quickshell calculator. No CEDAR Shell checkout, service,
configuration or installation is needed. No Omarchy dependency, web view,
network access, shell arithmetic or persisted calculation history.

## Run

Requires Linux, Quickshell 0.3.x with Qt 6 Quick/Controls/Layouts/Shapes, and a
working Wayland or X11 desktop. Python 3 is needed only for install/tests; Node.js
only for engine tests. Rajdhani and JetBrainsMono Nerd Font are optional; system
sans-serif/monospace fonts are the fallback. No fonts or dependency binaries ship.

```sh
./launch.sh
# or
qs -p shell.qml
```

The launcher resolves its own location, so it also works from another directory.
It uses `qs -d` and redirects stdout/stderr to `/dev/null`, returning promptly
without holding an Applications launch-response pipe open or mixing logs into it.
For foreground diagnostics use `qs -p shell.qml` directly.
This is the real standalone app, titled **CEDAR Calculator**, not the shell preview.
Closing it exits the process and forgets its memory-only history. It neither owns
nor manages a session lock; the desktop compositor provides lock protection.

The default is **360 × 560**, resizable down to 324 × 432. History is collapsed
initially. Empty and ordinary successful calculations fit without scrolling.
Expanded history, long errors, large fonts and narrow/short windows can scroll.
Theme tokens and the bundled palette have built-in fallback colors; the app does
not read or write CEDAR Shell configuration. Reduced Motion is safe: no production
animation loops or polling are used.

## User installation (explicit, optional)

```sh
python3 scripts/install.py install
python3 scripts/install.py uninstall
```

Installation copies an explicit runtime file list into a content-addressed version
under `$XDG_DATA_HOME/cedar-calculator/releases/`, default `~/.local/share`.
It creates `$XDG_BIN_HOME/cedar-calculator` (default `~/.local/bin`) and
`$XDG_DATA_HOME/applications/cedar-calculator.desktop`. Add the bin directory to
PATH if you want to run `cedar-calculator` in a terminal. The desktop entry uses
an absolute, escaped command and works independently of PATH.

Existing regular launchers are backed up with original bytes and modes in
`$XDG_STATE_HOME/cedar-calculator/install.json` (default `~/.local/state`).
Repeat installs preserve the original backup. Uninstall restores it or removes
only the installed entry when none existed. User edits cause refusal, not data
loss. Symlinks at install targets or their ancestors are refused. A per-user lock
serializes installer operations. Versioned app files and the empty lock file are
retained on uninstall for recovery; there is no recursive purge. Neither command
starts a window, reloads a compositor, modifies shell configuration or installs
packages. Do not move XDG locations between install and uninstall.

## Floating placement

`FloatingWindow` is a normal application toplevel: tiling compositors decide
whether it actually floats. A narrowly scoped Hyprland **Lua API** example is:

```lua
hl.window_rule({
    name = "cedar-calculator-compact",
    match = {
        class = "^org\\.quickshell$",
        title = "^CEDAR Calculator$",
    },
    float = true,
    size = {360, 560},
    center = true,
})
```

This example needs the Hyprland build with the Lua `hl.window_rule` API; older
hyprlang-based builds need their corresponding rule syntax. It does not require
Omarchy. Back up your compositor configuration before adding a rule; the installer
does not apply one. Check the actual app class/title on your compositor. The size
is an initial placement, not a maximum; the window remains resizable.

## Arithmetic and keyboard

- Enter or `=` calculates. Backspace edits; Ctrl+L clears input; Escape closes.
- Ctrl+Shift+C or **Copy result** copies the numeric result, not the “Approx.” label.
- Tab moves focus, Space activates buttons; arrow keys move within the keypad.
- History's button expands/collapses with Space. Recall edits the original
  expression; Clear history forgets it. At most 30 successful results stay in memory.
- After a result, a digit starts fresh and an operator chains the result. Selection,
  cursor edits and Ctrl+V work. Invalid input stays available for correction.
- Decimals/scientific notation, `+ - * /`, parentheses, unary signs, `^`, postfix `%`.
  `200*10%` is 20: percent divides its own operand by 100, not contextual markup.
  Powers associate right: `2^3^2` is 512; `-2^2` is -4.

The unchanged bounded parser accepts at most 256 characters, 128 tokens and 32
levels of nesting, with exponent magnitude limited to 1000. Errors, division by
zero and overflow disable copy but preserve input. Zero to a negative power is a
division-by-zero error. IEEE doubles are rounded to 14 significant digits for the
result; magnitudes >= `1e14` use scientific notation and round-trip for chaining.
Small increments can be lost beside large numbers, underflow quietly becomes 0,
and cancellation residue is preserved (`0.1+0.2-0.3` → `5.5511151231258e-17`).
Results are approximate, not financial arbitrary-precision arithmetic.

## Tests

```sh
node tests/core/calculator_engine_test.js components/CalculatorEngine.js
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/check_calculator.py
/usr/lib/qt6/bin/qmllint -I /usr/lib/qt6/qml Theme.qml shell.qml components/*.qml modules/*.qml
```

The true offscreen QML harness copies only this tree, uses private XDG dirs,
QtTest keyboard events, clipboard readback, default/narrow renders, bounded
history, scientific chaining and pasted-error recovery. It smokes the real entry
point and asserts no config/state writes. A temporary `.r-*` runtime directory
under this tree keeps Unix socket paths short and is cleaned automatically.
Optional render output: `python3 tests/check_calculator.py /absolute/scratch/dir`.
`QT_IM_MODULE=compose` isolates tests from host input-method configuration writes.

CI runs Python and Node checks on Ubuntu and real offscreen QML on an Arch
container with Quickshell. CI does not claim native compositor focus, installed
launcher discovery, screen-reader or external-app clipboard interoperability.
No release or publishing action is configured.

## Development and licensing

All future development and updates target **dev**, not main. Main is a controlled
baseline; the Coordinator owns repository initialization, branch creation and
promotion. See AGENTS.md, NOTICE.md and DEPENDENCIES.json.

Licensed under **GNU GPL version 3 only (GPL-3.0-only)** by the rights holder.
See LICENSE for the full terms. Distributed modified versions must comply with
GPLv3, including its source-availability requirements. External runtime dependencies
retain their own licenses; this grant does not relicense the CEDAR Shell repository.
