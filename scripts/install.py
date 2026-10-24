#!/usr/bin/env python3
"""User-only standalone installation. No shell/compositor activation or network."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ['LICENSE', 'NOTICE.md', 'DEPENDENCIES.json', 'shell.qml', 'Theme.qml', 'qmldir', 'launch.sh', 'components/qmldir',
           'components/CalculatorEngine.js', 'components/CalculatorModel.qml',
           'components/StationButton.qml', 'components/StationField.qml', 'components/ChamferFrame.qml',
           'modules/qmldir', 'modules/CalculatorApp.qml', 'modules/CalculatorPanel.qml',
           'themes/palettes/cedar.json']


def safe(path):
    if not path.is_absolute():
        raise ValueError('Install paths must be absolute')
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError('Symlink refused: ' + str(item))
    if path.exists() and not path.is_file():
        raise ValueError('Expected regular file: ' + str(path))


def snapshot(path):
    safe(path)
    return {'data': base64.b64encode(path.read_bytes()).decode(), 'mode': stat.S_IMODE(path.stat().st_mode)} if path.exists() else None


def atomic(path, data, mode=0o600):
    safe(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.calculator-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def encoded(data, mode):
    return {'data': base64.b64encode(data).decode(), 'mode': mode}


def desktop_quote(value):
    if '\n' in value or '\r' in value:
        raise ValueError('Newline in install path')
    # Exec quoting is decoded AFTER the Desktop Entry string-value layer.
    # First protect Exec's reserved characters, then escape those backslashes
    # for the key-file layer. Literal percent must survive field-code expansion.
    quoted = '"' + ''.join(('\\' + char) if char in '\\"`$' else ('%%' if char == '%' else char) for char in value) + '"'
    return quoted.replace('\\', '\\\\').replace('\t', '\\t')


def run(action):
    home = Path.home()
    data = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
    state = Path(os.environ.get('XDG_STATE_HOME', str(home / '.local/state'))) / 'cedar-calculator'
    binary = Path(os.environ.get('XDG_BIN_HOME', str(home / '.local/bin'))) / 'cedar-calculator'
    desktop = data / 'applications/cedar-calculator.desktop'
    journal = state / 'install.json'
    lock = state / 'install.lock'
    safe(lock)
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        safe(journal)
        saved = json.loads(journal.read_text()) if journal.exists() else None
        targets = [binary, desktop]
        if saved:
            if [row['path'] for row in saved['entries']] != [str(p) for p in targets]:
                raise ValueError('Install locations changed; restore using original XDG paths')
            for row, path in zip(saved['entries'], targets):
                current = snapshot(path)
                if current not in (row['installed'], row['before'], row.get('previous')):
                    raise ValueError('User changes preserved; refusing to overwrite: ' + str(path))
        if action == 'uninstall':
            if not saved:
                print('No recorded installation; nothing changed.')
                return
            for row, path in zip(saved['entries'], targets):
                before = row['before']
                if before is None:
                    if path.exists():
                        path.unlink()
                else:
                    atomic(path, base64.b64decode(before['data']), before['mode'])
            journal.unlink()
            print('Launcher restored. Versioned app files retained; no user configuration changed.')
            return
        # Validate both user entry points before writing any release files.
        for path in targets:
            safe(path)
        payload = {name: (ROOT / name).read_bytes() for name in RUNTIME}
        digest = hashlib.sha256()
        for name, content in sorted(payload.items()):
            digest.update(name.encode() + b'\0' + content + b'\0')
        release = data / 'cedar-calculator/releases' / digest.hexdigest()
        for name, content in payload.items():
            path = release / name
            safe(path)
            if path.exists() and path.read_bytes() != content:
                raise ValueError('Existing release modified; refusing replacement')
            if not path.exists():
                atomic(path, content, 0o755 if name == 'launch.sh' else 0o644)
        wrapper = ('#!/bin/sh\nset -eu\nexec ' + shlex.quote(str(release / 'launch.sh')) + ' "$@"\n').encode()
        # GLib checks argv[0] before expanding %% field escapes. A stable env
        # executable lets percent-bearing launcher paths round-trip as argv[1].
        # The launcher path is absolute; no shell command string is evaluated.
        entry = ('[Desktop Entry]\nType=Application\nName=CEDAR Calculator\nComment=Standalone native calculator\nExec=/usr/bin/env ' + desktop_quote(str(binary)) + '\nIcon=accessories-calculator\nTerminal=false\nCategories=Utility;Calculator;\nStartupNotify=false\n').encode()
        contents = [encoded(wrapper, 0o755), encoded(entry, 0o644)]
        records = [{'path': str(p), 'before': saved['entries'][i]['before'] if saved else snapshot(p), 'installed': contents[i], 'previous': snapshot(p)} for i, p in enumerate(targets)]
        # Durable original backup precedes launcher writes. Uninstall also repairs
        # an interrupted initial install (each target is old or newly installed).
        atomic(journal, (json.dumps({'entries': records}, indent=2) + '\n').encode())
        for path, item in zip(targets, contents):
            atomic(path, base64.b64decode(item['data']), item['mode'])
        print('Installed standalone launcher. No app started; no shell configuration changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'uninstall'])
    args = parser.parse_args()
    try:
        run(args.action)
    except (OSError, ValueError, KeyError) as error:
        print('Calculator: ' + str(error), file=sys.stderr)
        sys.exit(1)
