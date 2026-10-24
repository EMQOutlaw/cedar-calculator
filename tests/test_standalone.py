from pathlib import Path
import json
import importlib.util
from unittest.mock import patch
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Standalone(unittest.TestCase):
    def test_desktop_exec_glib_exact_argv_roundtrip(self):
        # Use system PyGObject even when this suite runs in a Python venv.
        probe = subprocess.run(['/usr/bin/python3', '-c', 'import gi; from gi.repository import Gio; assert hasattr(Gio, "DesktopAppInfo")'], capture_output=True)
        if probe.returncode:
            self.skipTest('System Python GLib/Gio introspection unavailable')
        helper = r'''
import importlib.util, json, os, subprocess, sys, tempfile, time
from pathlib import Path
from gi.repository import Gio
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('installer', root/'scripts/install.py')
installer = importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)
with tempfile.TemporaryDirectory(prefix='calc-glib-') as tmp:
    base = Path(tmp)
    capture = base/'captured.json'
    os.environ['CALCULATOR_CAPTURE'] = str(capture)
    for index, name in enumerate(['space name', 'dollar$', 'quote"', 'tick`', 'percent%f', 'back\\slash', 'all $"`%f\\ 雨']):
        folder = base/name
        folder.mkdir()
        executable = folder/'capture'
        executable.write_text('#!/usr/bin/python3\nimport json,os,sys\nfrom pathlib import Path\nPath(os.environ["CALCULATOR_CAPTURE"]).write_text(json.dumps(sys.argv))\n')
        executable.chmod(0o755)
        argument = name + ' literal %U'
        desktop = base/('case' + str(index) + '.desktop')
        desktop.write_text('[Desktop Entry]\nType=Application\nName=Quote regression\nExec=/usr/bin/env ' + installer.desktop_quote(str(executable)) + ' ' + installer.desktop_quote(argument) + '\n')
        try:
            app = Gio.DesktopAppInfo.new_from_filename(str(desktop))
        except TypeError as error:
            raise AssertionError('GLib rejected ' + repr(name) + ': ' + desktop.read_text()) from error
        assert app is not None, 'GLib rejected ' + repr(name)
        assert app.launch([], None), 'GLib launch failed: ' + repr(name)
        for attempt in range(100):
            if capture.exists(): break
            time.sleep(.02)
        assert capture.exists(), 'No execution for ' + repr(name)
        assert json.loads(capture.read_text()) == [str(executable), argument], capture.read_text()
        capture.unlink()
    # Exercise the installer-generated entry, wrapper and installed launch.sh.
    home = base/'install $"`%f\\ 雨'
    env = {**os.environ, 'HOME': str(home), 'XDG_DATA_HOME': str(home/'data'), 'XDG_STATE_HOME': str(home/'state'), 'XDG_BIN_HOME': str(home/'bin')}
    subprocess.run([sys.executable, str(root/'scripts/install.py'), 'install'], env=env, check=True, capture_output=True)
    fakebin = base/'fakebin'; fakebin.mkdir()
    fakeqs = fakebin/'qs'; fakeqs.write_bytes(executable.read_bytes()); fakeqs.chmod(0o755)
    os.environ['PATH'] = str(fakebin) + os.pathsep + os.environ['PATH']
    desktop = home/'data/applications/cedar-calculator.desktop'
    app = Gio.DesktopAppInfo.new_from_filename(str(desktop))
    assert app is not None, 'GLib rejected installed desktop entry'
    assert app.launch([], None)
    for attempt in range(100):
        if capture.exists(): break
        time.sleep(.02)
    assert capture.exists(), 'Installed launcher did not execute'
    argv = json.loads(capture.read_text())
    assert argv[:3] == [str(fakeqs), '-d', '-p'], argv
    entry = Path(argv[3])
    assert len(argv) == 4 and entry.is_relative_to(home/'data/cedar-calculator/releases'), argv
    assert entry.read_bytes() == (root/'shell.qml').read_bytes()
    subprocess.run([sys.executable, str(root/'scripts/install.py'), 'uninstall'], env=env, check=True, capture_output=True)
    assert not desktop.exists() and not (home/'bin/cedar-calculator').exists()
print('PASS: GLib exact argv for seven special paths and installed launcher')
'''
        result = subprocess.run(['/usr/bin/python3', '-c', helper, str(ROOT)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS: GLib exact argv', result.stdout)

    def test_runtime_is_self_contained(self):
        self.assertTrue((ROOT / 'shell.qml').is_file(), 'standalone entry missing')
        for folder in ('components', 'modules'):
            for path in (ROOT / folder).glob('*.qml'):
                self.assertNotIn('Config.', path.read_text())
                self.assertNotIn('ShellState', path.read_text())
        self.assertFalse((ROOT / 'services').exists())

    def test_launcher_resolves_itself_from_other_directory(self):
        with tempfile.TemporaryDirectory(prefix='calc launch 雨 ') as tmp:
            folder = Path(tmp)
            fake = folder / 'qs'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGS_FILE"\nprintf noisy\nprintf error >&2\n')
            fake.chmod(0o755)
            result = subprocess.run(['sh', str(ROOT / 'launch.sh'), '--no-duplicate'], cwd=folder,
                                    env={**os.environ, 'ARGS_FILE': str(folder/'args'), 'PATH': str(folder) + os.pathsep + os.environ['PATH']}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout + result.stderr, '')
            self.assertEqual((folder/'args').read_text().splitlines(), ['-d', '-p', str(ROOT / 'shell.qml'), '--no-duplicate'])

    def test_symlink_launcher_refused_without_touching_target(self):
        with tempfile.TemporaryDirectory(prefix='calc-symlink-') as tmp:
            base = Path(tmp)
            outside = base / 'original'
            outside.write_text('keep')
            binary = base / 'bin/cedar-calculator'
            binary.parent.mkdir()
            binary.symlink_to(outside)
            env = {**os.environ, 'HOME': tmp, 'XDG_DATA_HOME': str(base/'data'), 'XDG_STATE_HOME': str(base/'state'), 'XDG_BIN_HOME': str(base/'bin')}
            result = subprocess.run(['python3', str(ROOT/'scripts/install.py'), 'install'], env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(outside.read_text(), 'keep')
            self.assertTrue(binary.is_symlink())

    def test_interrupted_upgrade_restores_original_launchers(self):
        spec = importlib.util.spec_from_file_location('calculator_installer', ROOT/'scripts/install.py')
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory(prefix='calc-interrupt-') as tmp:
            base = Path(tmp)
            env = {'HOME': tmp, 'XDG_DATA_HOME': str(base/'data'), 'XDG_STATE_HOME': str(base/'state'), 'XDG_BIN_HOME': str(base/'bin')}
            desktop = base/'data/applications/cedar-calculator.desktop'
            desktop.parent.mkdir(parents=True)
            desktop.write_text('original')
            with patch.dict(os.environ, env):
                installer.run('install')
                source = base/'source'
                import shutil
                for name in installer.RUNTIME:
                    target = source/name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(ROOT/name, target)
                with (source/'shell.qml').open('a') as stream:
                    stream.write('\n// upgrade fixture\n')
                original_atomic = installer.atomic
                def interrupted(path, data, mode=0o600):
                    if path == base/'bin/cedar-calculator':
                        raise OSError('simulated interruption')
                    return original_atomic(path, data, mode)
                with patch.object(installer, 'ROOT', source), patch.object(installer, 'atomic', interrupted):
                    with self.assertRaises(OSError):
                        installer.run('install')
                installer.run('uninstall')
                self.assertEqual(desktop.read_text(), 'original')
                self.assertFalse((base/'bin/cedar-calculator').exists())

    def test_install_backup_repeat_restore_and_conflict(self):
        with tempfile.TemporaryDirectory(prefix='calc-install-') as tmp:
            home = Path(tmp)
            env = {**os.environ, 'HOME': tmp, 'XDG_DATA_HOME': str(home/'data'), 'XDG_STATE_HOME': str(home/'state'), 'XDG_BIN_HOME': str(home/'bin')}
            target = home/'data/applications/cedar-calculator.desktop'
            target.parent.mkdir(parents=True)
            target.write_text('existing launcher\n')
            def run(action):
                return subprocess.run(['python3', str(ROOT/'scripts/install.py'), action], env=env, capture_output=True, text=True)
            installed = run('install')
            self.assertEqual(installed.returncode, 0, installed.stderr)
            contents = target.read_text()
            self.assertIn('Name=CEDAR Calculator', contents)
            self.assertTrue((home/'bin/cedar-calculator').is_file())
            fakebin = home/'fakebin'
            fakebin.mkdir()
            fakeqs = fakebin/'qs'
            fakeqs.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGS_FILE"\nprintf noisy\nprintf error >&2\n')
            fakeqs.chmod(0o755)
            launched = subprocess.run([str(home/'bin/cedar-calculator')], cwd=home,
                                      env={**env, 'ARGS_FILE': str(home/'args'), 'PATH': str(fakebin) + os.pathsep + env['PATH']}, capture_output=True, text=True)
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertEqual(launched.stdout + launched.stderr, '')
            arguments = (home/'args').read_text().splitlines()
            self.assertEqual(arguments[:2], ['-d', '-p'])
            entry = Path(arguments[2])
            self.assertTrue(entry.is_file())
            self.assertEqual(entry.read_bytes(), (ROOT/'shell.qml').read_bytes())
            self.assertTrue((entry.parent/'LICENSE').is_file())
            self.assertEqual(run('install').returncode, 0)
            target.write_text('user changed launcher')
            self.assertNotEqual(run('uninstall').returncode, 0)
            self.assertEqual(target.read_text(), 'user changed launcher')
            target.write_text(contents)
            restored = run('uninstall')
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(target.read_text(), 'existing launcher\n')
            self.assertFalse((home/'bin/cedar-calculator').exists())

if __name__ == '__main__':
    unittest.main()
