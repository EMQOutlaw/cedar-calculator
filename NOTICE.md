# Provenance and dependency notices

Calculator App, Panel, Model and Engine, StationButton, StationField, ChamferFrame,
Theme tokens and cedar.json were extracted from the owner's CEDAR Shell working
source on branch feat/cedar-calculator (base cc6f446). DEPENDENCIES.json records
SHA-256 of the extraction inputs, not necessarily the adapted standalone outputs.
The engine and its Node tests are byte-for-byte copies; they are not reimplemented.

The rights holder has selected GNU GPL version 3 for this standalone repository.
CEDAR Calculator's first-party source and bundled palette are licensed under
GPL-3.0-only; see LICENSE. Copyright (C) 2026 EMQOutlaw.
This grant applies to this standalone project, not to the entire CEDAR Shell repository.
No Omarchy menu, Field Notes, third-party artwork or bundled font files are used;
therefore unrelated upstream notices/assets were not copied into this app.
Qt, Quickshell, Linux and optional fonts are external dependencies under their own
licenses. This extraction does not redistribute their binaries or fonts.

## Runtime inventory and adaptations

- shell.qml → modules/CalculatorApp.qml → CalculatorPanel.qml.
- Panel → components/CalculatorModel.qml → CalculatorEngine.js (unchanged).
- Panel → StationButton.qml, StationField.qml, ChamferFrame.qml.
- All UI → Theme.qml singleton with only required tokens, bundled cedar.json and
  fallback colors/fonts. No optional shell-theme reads or shell configuration.
- ChamferFrame's unused Config.barOpacity default is replaced with fixed token
  alpha, eliminating its sole shell dependency.
- Minimal root/components/modules qmldirs register only these runtime types.
- launch.sh resolves its own path; scripts/install.py copies an explicit runtime
  allowlist and journals user launcher backups. No shell IPC or lock service.
- tests/check_calculator.py adapts the original real-QML harness, removes shell
  lock-service checks and smokes standalone shell.qml. Installer tests are new.

The copied history-toggle binding passed a regression after keyboard activation
and programmatic state changes; no speculative rewrite was made.
