"""Behavioral regression tests; all command executions use isolated projects."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'evidence_guard.py'


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='evidence-guard-')
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()
        (self.project / 'src').mkdir()
        (self.project / 'src/main.py').write_text('value = 1\n')

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, code=0):
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--project', str(self.project), *args],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def require(self, identifier='F1', text='Calculate correct total'):
        return self.cli('require', '--id', identifier, '--text', text,
                        '--acceptance', 'Known fixture total matches', '--source', 'README section 2')

    def check(self, command='assert 1 + 1 == 2', identifier='T1', requirement='F1', code=0, extra=()):
        return self.cli('check', '--id', identifier, '--for', requirement, '--watch', 'src',
                        *extra, '--', sys.executable, '-c', command, code=code)

    @property
    def store(self):
        return self.project / 'exam-notes/.evidence-guard'

    def test_empty_status_is_read_only_and_blocked(self):
        before = sorted(p.relative_to(self.project).as_posix() for p in self.project.rglob('*'))
        result = self.cli('status', code=2)
        self.assertFalse(result['recorded_checks_current'])
        self.assertEqual(before, sorted(p.relative_to(self.project).as_posix() for p in self.project.rglob('*')))

    def test_success_and_status_read_only(self):
        self.require()
        self.check('from pathlib import Path; assert Path("src/main.py").is_file(); print("tested")')
        before = {p: p.read_bytes() for p in self.store.rglob('*') if p.is_file()}
        status = self.cli('status')
        self.assertTrue(status['recorded_checks_current'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.store.rglob('*') if p.is_file()})

    def test_uncovered_requirement_blocks(self):
        self.require()
        self.require('F2')
        self.check()
        self.assertIn('F2', self.cli('status', code=2)['uncovered_requirements'])

    def test_require_change_invalidates_but_identical_require_does_not(self):
        self.require()
        self.check()
        self.require()
        self.cli('status')
        self.require(text='Different acceptance target')
        self.cli('status', code=2)

    def test_later_failure_same_id_hides_no_failure(self):
        self.require()
        self.check()
        result = self.check('raise SystemExit(7)', code=7)
        self.assertEqual(result['exit_code'], 7)
        self.cli('status', code=2)

    def test_later_failure_different_id_blocks_old_success(self):
        self.require()
        self.check()
        self.check('raise SystemExit(9)', identifier='T2', code=9)
        self.cli('status', code=2)

    def test_rejected_latest_attempt_blocks_until_actual_success(self):
        self.require()
        self.check()
        for extra in (('--watch', 'missing'), ('--timeout', 'nan'), ('--watch', '../outside')):
            with self.subTest(extra=extra):
                self.check(extra=extra, code=2)
                result = self.cli('status', code=2)
                self.assertIn('rejected_attempt:T1', result['blockers'])
                self.require()
                self.cli('status', code=2)
                self.check()
                self.cli('status')

    def test_modified_added_deleted_and_renamed_files_stale(self):
        for action in ('modified', 'added', 'deleted', 'renamed'):
            with self.subTest(action=action):
                self.require()
                source = self.project / 'src/main.py'
                source.write_text('value = 1\n')
                self.check()
                if action == 'modified':
                    source.write_text('value = 2\n')
                elif action == 'added':
                    (self.project / 'src/extra.py').write_text('extra = 1')
                elif action == 'deleted':
                    source.unlink()
                else:
                    source.rename(self.project / 'src/renamed.py')
                self.cli('status', code=2)
                for p in (self.project / 'src').iterdir():
                    p.unlink()

    def test_change_during_check_does_not_count(self):
        self.require()
        result = self.check('from pathlib import Path; Path("src/main.py").write_text("changed")', code=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['fresh'])
        self.cli('status', code=2)

    def test_temporary_input_change_then_byte_restore_does_not_count(self):
        self.require()
        result = self.check(
            'from pathlib import Path; import time; p=Path("src/main.py"); '
            'original=p.read_bytes(); time.sleep(0.02); p.write_bytes(b"temporary"); '
            'assert p.read_bytes()==b"temporary"; p.write_bytes(original)', code=2)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['fresh'])
        self.cli('status', code=2)

    def test_old_snapshot_algorithm_requires_recheck_without_rewriting_state(self):
        self.require()
        self.check()
        path = self.store / 'state.json'
        state = json.loads(path.read_text(encoding='utf-8'))
        state['checks']['T1'].pop('snapshot_version', None)
        path.write_text(json.dumps(state), encoding='utf-8')
        before = path.read_bytes()
        result = self.cli('status', code=2)
        self.assertIn('snapshot_algorithm_changed', result['checks']['T1']['problems'])
        self.assertEqual(path.read_bytes(), before)
        self.check()
        self.cli('status')

    def test_input_data_change_stales(self):
        self.require()
        data = self.project / 'input.csv'
        data.write_text('value\n1\n')
        self.check(extra=('--watch', 'input.csv'))
        data.write_text('value\n2\n')
        self.cli('status', code=2)

    def test_missing_and_modified_log_block(self):
        self.require()
        self.check()
        log = next((self.store / 'logs').glob('*.log'))
        log.write_text('forged')
        self.cli('status', code=2)
        self.check()
        latest = max((self.store / 'logs').glob('*.log'), key=lambda p: p.stat().st_mtime_ns)
        latest.unlink()
        self.cli('status', code=2)

    def test_timeout_and_missing_command_are_recorded(self):
        self.require()
        result = self.check('import time; time.sleep(10)', extra=('--timeout', '0.1'), code=124)
        self.assertEqual(result['outcome'], 'timeout')
        self.cli('status', code=2)
        result = self.cli('check', '--id', 'T1', '--for', 'F1', '--watch', 'src', '--',
                          'missing-evidence-executable-0123456', code=127)
        self.assertEqual(result['outcome'], 'start_error')
        self.cli('status', code=2)

    def test_timeout_terminates_owned_child_process_tree(self):
        self.require()
        # Observe the original child process identity, rather than a short-delay
        # marker: taskkill startup/cleanup itself can exceed the marker delay.
        if os.name != 'nt' and not hasattr(os, 'pidfd_open'):
            self.skipTest('Exact child-exit observation requires Windows handles or Linux pidfd')
        child = 'import time; time.sleep(60)'
        command = ('import subprocess,sys,time; from pathlib import Path; '
                   'child=subprocess.Popen([sys.executable,"-c",' + repr(child) + ']); '
                   'Path("child-spawned.tmp").write_text(str(child.pid)); '
                   'Path("child-spawned.tmp").replace("child-spawned"); time.sleep(60)')
        process = subprocess.Popen([sys.executable, '-B', str(SCRIPT), '--project', str(self.project),
                                    'check', '--id', 'T1', '--for', 'F1', '--watch', 'src',
                                    '--timeout', '2', '--', sys.executable, '-c', command],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        child_handle = None
        kernel = None
        try:
            pidfile = self.project / 'child-spawned'
            deadline = time.monotonic() + 10
            while not pidfile.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(pidfile.exists(), 'Fixture child was not spawned')
            child_pid = int(pidfile.read_text())
            if os.name == 'nt':
                import ctypes
                from ctypes import wintypes
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.WaitForSingleObject.restype = wintypes.DWORD
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
                child_handle = kernel.OpenProcess(0x00100001, False, child_pid)
                self.assertTrue(child_handle, 'Could not observe original child process')
                self.assertEqual(kernel.WaitForSingleObject(child_handle, 0), 258)
            else:
                import select
                child_handle = os.pidfd_open(child_pid)
                self.assertEqual(select.select([child_handle], [], [], 0)[0], [])
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 124, stdout + stderr)
            self.assertEqual(json.loads(stdout)['outcome'], 'timeout')
            if os.name == 'nt':
                self.assertEqual(kernel.WaitForSingleObject(child_handle, 1000), 0,
                                 'Original fixture child remained alive after cleanup returned')
            else:
                self.assertEqual(select.select([child_handle], [], [], 1)[0], [child_handle],
                                 'Original fixture child remained alive after cleanup returned')
        finally:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                else:
                    process.kill()
                process.communicate()
            if child_handle is not None:
                if os.name == 'nt' and kernel is not None:
                    if kernel.WaitForSingleObject(child_handle, 0) == 258:
                        kernel.TerminateProcess(child_handle, 1)
                        kernel.WaitForSingleObject(child_handle, 5000)
                    kernel.CloseHandle(child_handle)
                else:
                    if not select.select([child_handle], [], [], 0)[0]:
                        import signal
                        signal.pidfd_send_signal(child_handle, signal.SIGKILL)
                    os.close(child_handle)

    def test_unreadable_subtree_cannot_produce_partial_snapshot(self):
        spec = importlib.util.spec_from_file_location('evidence_guard', SCRIPT)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        def unreadable(*args, **kwargs):
            kwargs['onerror'](PermissionError('fixture subtree cannot be read'))
            return iter(())
        with patch.object(guard.os, 'walk', side_effect=unreadable):
            with self.assertRaises(PermissionError):
                guard.snapshot(self.project, ['src'], self.store)

    def test_unsafe_watch_and_unknown_requirement_rejected(self):
        self.require()
        self.cli('check', '--id', 'T1', '--for', 'unknown', '--watch', 'src', '--', sys.executable, '-V', code=2)
        for path in ('../outside', str(self.project / 'src'), 'missing'):
            with self.subTest(path=path):
                self.cli('check', '--id', 'T1', '--for', 'F1', '--watch', path, '--', sys.executable, '-V', code=2)

    def test_lock_blocks_status_and_mutation(self):
        self.require()
        self.check()
        lock = self.store / '.lock'
        lock.write_text('active or interrupted check')
        self.cli('status', code=2)
        self.cli('require', '--id', 'F2', '--text', 'two', '--acceptance', 'two', '--source', 'README', code=2)
        self.assertTrue(lock.exists())

    def test_corrupt_state_is_preserved(self):
        self.require()
        state = self.store / 'state.json'
        state.write_text('{not valid json')
        self.cli('status', code=2)
        self.require_error()
        self.assertEqual(state.read_text(), '{not valid json')

    def test_earlier_schema_one_without_attempt_errors_remains_read_only(self):
        self.require()
        self.check()
        path = self.store / 'state.json'
        state = json.loads(path.read_text(encoding='utf-8'))
        del state['attempt_errors']
        path.write_text(json.dumps(state), encoding='utf-8')
        before = path.read_bytes()
        self.cli('status')
        self.assertEqual(before, path.read_bytes())

    def require_error(self):
        self.cli('require', '--id', 'F2', '--text', 'two', '--acceptance', 'two', '--source', 'README', code=2)

    def test_custom_store_escape_rejected(self):
        self.cli('--store', '../outside', 'status', code=2)
        self.assertFalse((Path(self.tmp.name) / 'outside').exists())

    def test_explicit_watched_file_in_excluded_directory_is_honored(self):
        self.require()
        (self.project / 'build').mkdir()
        output = self.project / 'build/result.txt'
        output.write_text('one')
        self.check(extra=('--watch', 'build/result.txt'))
        output.write_text('two')
        self.cli('status', code=2)

    def test_whole_project_watch_ignores_guard_and_caches(self):
        self.require()
        self.cli('check', '--id', 'T1', '--for', 'F1', '--watch', '.', '--', sys.executable, '-V')
        (self.project / '__pycache__').mkdir()
        (self.project / '__pycache__/x.pyc').write_bytes(b'cache')
        self.cli('status')

    def test_directory_link_is_rejected(self):
        external = Path(self.tmp.name) / 'external'
        external.mkdir()
        link = self.project / 'src/linked'
        try:
            link.symlink_to(external, target_is_directory=True)
        except OSError:
            if sys.platform != 'win32':
                self.skipTest('No symbolic-link capability')
            quote = lambda p: "'" + str(p).replace("'", "''") + "'"
            result = subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                                     'New-Item -ItemType Junction -Path ' + quote(link) + ' -Target ' + quote(external) + ' | Out-Null'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.require()
        self.check(code=2)
        self.assertEqual(list(external.iterdir()), [])

    def test_concurrent_finished_mutation_during_status_is_not_old_success(self):
        self.require()
        self.check()
        spec = importlib.util.spec_from_file_location('evidence_guard', SCRIPT)
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        original = guard.snapshot
        def concurrent(*args):
            value = original(*args)
            state = guard.load_state(self.store)
            state['requirements']['F1']['text'] = 'Concurrent changed requirement'
            guard.save_state(self.store, state)
            return value
        with patch.object(guard, 'snapshot', side_effect=concurrent):
            result, code = guard.status(self.project, self.store)
        self.assertEqual(code, 2)
        self.assertIn('state_changed_during_status', result['blockers'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
