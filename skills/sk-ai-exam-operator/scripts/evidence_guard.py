#!/usr/bin/env python3
"""Record actual checks and detect stale evidence; not a sandbox or a task grader.

Requires explicit project-relative --watch paths. Directory scans omit .git,
node_modules, .venv, venv, __pycache__, .pytest_cache, .mypy_cache, .ruff_cache,
.next, dist, build, coverage and this guard's store. Explicit files are honored.
Watch the relevant source, configuration, requirements and input data; omitted
inputs and the semantic adequacy of a command cannot be verified by this tool.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import uuid

OWNER = 'sk-ai-exam-evidence-guard'
SNAPSHOT_VERSION = 2
EXCLUDED = frozenset(('.git', 'node_modules', '.venv', 'venv', '__pycache__',
                      '.pytest_cache', '.mypy_cache', '.ruff_cache', '.next',
                      'dist', 'build', 'coverage'))
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}')
DIGEST = re.compile(r'[a-f0-9]{64}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def linked(path):
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), 'st_file_attributes', 0) &
                    getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))
    except FileNotFoundError:
        return False


def normal_ancestors(path):
    for item in (path, *path.parents):
        require(not linked(item), f'Linked/junction paths are not allowed: {item}')


def relative(value, *, dot=False):
    value = str(value).replace('\\', '/')
    if dot and value == '.':
        return '.'
    parts = value.split('/')
    require(bool(value) and ':' not in value and not value.startswith('/') and
            all(p not in ('', '.', '..') for p in parts), 'Expected a safe project-relative path')
    return PurePosixPath(value).as_posix()


def target(root, value, *, dot=False):
    value = relative(value, dot=dot)
    result = root if value == '.' else root.joinpath(*value.split('/'))
    normal_ancestors(result)
    require(result.resolve().is_relative_to(root.resolve()), 'Path escapes project')
    return result


def file_fingerprint(path):
    require(path.is_file() and not linked(path), f'Missing or linked file: {path}')
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino), 'File changed while hashing')
    return (digest.hexdigest(), after.st_size, after.st_mtime_ns, after.st_ino, after.st_mode)


def sha_file(path):
    return file_fingerprint(path)[0]


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


def scan_error(error):
    raise error


def snapshot(project, watches, store):
    entries = []
    for watch in sorted(set(watches)):
        path = target(project, watch, dot=True)
        require(path != store and not path.is_relative_to(store), 'Cannot watch evidence store')
        require(path.exists(), f'Missing watched path: {watch}')
        if path.is_file():
            entries.append(('file', watch, *file_fingerprint(path)))
            continue
        require(path.is_dir(), f'Unsupported watched path: {watch}')
        for current, directories, files in os.walk(path, topdown=True, followlinks=False, onerror=scan_error):
            current = Path(current)
            normal_ancestors(current)
            entries.append(('directory', current.relative_to(project).as_posix()))
            directories[:] = sorted(d for d in directories if d not in EXCLUDED and
                                     current / d != store and not (current / d).is_relative_to(store))
            for directory in directories:
                normal_ancestors(current / directory)
            for name in sorted(files):
                item = current / name
                if item == store or item.is_relative_to(store):
                    continue
                normal_ancestors(item)
                entries.append(('file', item.relative_to(project).as_posix(), *file_fingerprint(item)))
    return json_digest(entries)


def new_state():
    return {'owner': OWNER, 'schema_version': 1, 'requirements': {}, 'checks': {}, 'attempt_errors': {}}


def load_state(store):
    path = store / 'state.json'
    normal_ancestors(path)
    if not path.exists():
        return new_state()
    require(path.is_file(), 'State must be a normal file')
    state = json.loads(path.read_text(encoding='utf-8'))
    require(isinstance(state, dict) and state.get('owner') == OWNER and
            type(state.get('schema_version')) is int and state['schema_version'] == 1,
            'Unfamiliar state schema; original preserved')
    require(isinstance(state.get('requirements'), dict) and isinstance(state.get('checks'), dict),
            'Malformed state; original preserved')
    # Earlier schema-1 records predate rejection tracking; read them without rewriting.
    state.setdefault('attempt_errors', {})
    require(isinstance(state.get('attempt_errors'), dict), 'Malformed attempt error state; original preserved')
    for identifier, item in state['attempt_errors'].items():
        require(isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier) and isinstance(item, dict)
                and isinstance(item.get('error'), str) and bool(item['error'])
                and isinstance(item.get('recorded_at_utc'), str), 'Malformed attempt error')
    for identifier, item in state['requirements'].items():
        require(isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier) and isinstance(item, dict),
                'Malformed requirement')
        require(set(item) == {'text', 'acceptance', 'source'} and
                all(isinstance(v, str) and v.strip() for v in item.values()), 'Malformed requirement fields')
    for identifier, item in state['checks'].items():
        require(isinstance(identifier, str) and IDENTIFIER.fullmatch(identifier) and isinstance(item, dict),
                'Malformed check')
        require(item.get('outcome') in ('running', 'pass', 'fail', 'timeout', 'start_error',
                                       'interrupted', 'supervisor_error'), 'Malformed check outcome')
        require(isinstance(item.get('requirements'), list) and bool(item['requirements']) and
                all(isinstance(v, str) and v in state['requirements'] for v in item['requirements']),
                'Malformed check requirement links')
        require(isinstance(item.get('watch'), list) and bool(item['watch']) and
                all(isinstance(v, str) and relative(v, dot=True) == v for v in item['watch']),
                'Malformed watch list')
        for key in ('before', 'requirements_hash'):
            require(isinstance(item.get(key), str) and DIGEST.fullmatch(item[key]), 'Malformed evidence hash')
        for key in ('after', 'log_hash'):
            require(item.get(key) is None or (isinstance(item[key], str) and DIGEST.fullmatch(item[key])),
                    'Malformed evidence hash')
        require(item.get('exit_code') is None or type(item['exit_code']) is int, 'Malformed exit code')
        log = item.get('log')
        require(isinstance(log, str) and re.fullmatch(r'logs/[a-f0-9]{32}\.log', log), 'Malformed log path')
        require(isinstance(item.get('command'), list) and bool(item['command']) and
                all(isinstance(v, str) for v in item['command']), 'Malformed command')
    return state


def save_state(store, state):
    destination = store / 'state.json'
    normal_ancestors(destination)
    temporary = store / ('.state-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(state, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def mutation(store):
    normal_ancestors(store)
    store.mkdir(parents=True, exist_ok=True)
    lock = store / '.lock'
    normal_ancestors(lock)
    try:
        with lock.open('x', encoding='utf-8') as stream:
            stream.write(f'pid={os.getpid()}\n')
    except FileExistsError as exc:
        raise ValueError('Guard is locked; inspect the active/interrupted operation, never auto-clear its lock') from exc
    try:
        yield
    finally:
        lock.unlink()


def kill_owned(process):
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def check(project, store, state, args):
    identifiers = sorted(set(args.for_requirements))
    require(all(v in state['requirements'] for v in identifiers), 'Unknown requirement ID')
    watches = sorted(set(relative(v, dot=True) for v in args.watch))
    before = snapshot(project, watches, store)
    command = args.command[1:] if args.command and args.command[0] == '--' else args.command
    require(bool(command), 'An actual command is required after --')
    require(math.isfinite(args.timeout) and args.timeout > 0, 'Timeout must be positive and finite')
    logs = store / 'logs'
    normal_ancestors(logs)
    logs.mkdir(exist_ok=True)
    log_relative = 'logs/' + uuid.uuid4().hex + '.log'
    log = store / log_relative
    item = {'requirements': identifiers, 'watch': watches, 'before': before, 'after': None,
            'snapshot_version': SNAPSHOT_VERSION,
            'requirements_hash': json_digest(state['requirements']), 'command': command,
            'outcome': 'running', 'exit_code': None, 'log': log_relative, 'log_hash': None,
            'started_at_utc': datetime.now(timezone.utc).isoformat()}
    state['checks'][args.id] = item
    # Persist an incomplete attempt before execution so interruption cannot expose old success.
    save_state(store, state)
    process = None
    with log.open('xb') as output:
        try:
            options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen(command, cwd=project, shell=False, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, **options)
            try:
                item['exit_code'] = process.wait(timeout=args.timeout)
                item['outcome'] = 'pass' if item['exit_code'] == 0 else 'fail'
            except subprocess.TimeoutExpired:
                kill_owned(process)
                item.update(outcome='timeout', exit_code=124)
        except OSError as error:
            if process is not None:
                kill_owned(process)
            item.update(outcome='start_error', exit_code=127, error=str(error))
            output.write((str(error) + '\n').encode('utf-8', errors='replace'))
        except BaseException as error:
            if process is not None:
                kill_owned(process)
            item.update(outcome='interrupted' if isinstance(error, KeyboardInterrupt) else 'supervisor_error',
                        exit_code=130 if isinstance(error, KeyboardInterrupt) else 125, error=repr(error))
    try:
        item['after'] = snapshot(project, watches, store)
    except (OSError, ValueError) as error:
        item['snapshot_error'] = str(error)
    item['log_hash'] = sha_file(log)
    item['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    if item['outcome'] == 'pass' and item['before'] == item['after']:
        state['attempt_errors'].pop(args.id, None)
    save_state(store, state)
    fresh = item['before'] == item['after']
    result = dict(item, id=args.id, fresh=fresh)
    code = item['exit_code']
    return result, (0 if fresh else 2) if code == 0 else (code if 0 < code < 256 else 1)


def status(project, store):
    normal_ancestors(store / '.lock')
    if (store / '.lock').exists():
        return {'recorded_checks_current': False, 'blockers': ['active_or_interrupted_operation']}, 2
    state_path = store / 'state.json'
    original_hash = sha_file(state_path) if state_path.exists() else None
    state = load_state(store)
    blockers, covered, details = [], set(), {}
    blockers.extend('rejected_attempt:' + identifier for identifier in sorted(state['attempt_errors']))
    if not state['requirements']:
        blockers.append('no_registered_requirements')
    if not state['checks']:
        blockers.append('no_recorded_checks')
    requirements_hash = json_digest(state['requirements'])
    for identifier, item in state['checks'].items():
        problems = []
        if item.get('snapshot_version') != SNAPSHOT_VERSION:
            problems.append('snapshot_algorithm_changed')
        if item['outcome'] != 'pass' or item['exit_code'] != 0:
            problems.append('latest_attempt_did_not_pass')
        if item['before'] != item['after'] or item['after'] is None:
            problems.append('inputs_changed_during_check')
        if item['requirements_hash'] != requirements_hash:
            problems.append('requirements_changed')
        try:
            if snapshot(project, item['watch'], store) != item['after']:
                problems.append('watched_inputs_changed')
            log = target(project, (store / item['log']).relative_to(project).as_posix())
            if sha_file(log) != item['log_hash']:
                problems.append('log_changed')
        except (OSError, ValueError) as error:
            problems.append('missing_or_unsafe_evidence: ' + str(error))
        details[identifier] = {'current': not problems, 'problems': problems}
        if problems:
            blockers.append(identifier)
        else:
            covered.update(item['requirements'])
    uncovered = sorted(set(state['requirements']) - covered)
    if uncovered:
        blockers.append('uncovered_requirements')
    # Concurrent mutation may have begun after the first lock check.
    if (store / '.lock').exists():
        blockers.append('active_or_interrupted_operation')
    elif (sha_file(state_path) if state_path.exists() else None) != original_hash:
        blockers.append('state_changed_during_status')
    result = {'recorded_checks_current': not blockers, 'blockers': blockers,
              'uncovered_requirements': uncovered, 'checks': details,
              'notice': 'Only registered requirements and declared watched inputs are covered; command success does not prove semantic correctness.'}
    return result, 2 if blockers else 0


def parser():
    cli = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    cli.add_argument('--project', required=True, type=Path)
    cli.add_argument('--store', default='exam-notes/.evidence-guard', help='Project-relative private evidence directory')
    commands = cli.add_subparsers(dest='action', required=True)
    register = commands.add_parser('require')
    for name in ('id', 'text', 'acceptance', 'source'):
        register.add_argument('--' + name, required=True)
    run = commands.add_parser('check')
    run.add_argument('--id', required=True)
    run.add_argument('--for', dest='for_requirements', action='append', required=True)
    run.add_argument('--watch', action='append', required=True)
    run.add_argument('--timeout', type=float, default=120)
    run.add_argument('command', nargs=argparse.REMAINDER)
    commands.add_parser('status')
    return cli


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    try:
        project = args.project.absolute()
        normal_ancestors(project)
        require(project.is_dir(), 'Project must be an existing normal directory')
        store = target(project, args.store)
        if args.action == 'status':
            result, code = status(project, store)
        else:
            require(IDENTIFIER.fullmatch(args.id) is not None, 'Invalid ID')
            with mutation(store):
                state = load_state(store)
                if args.action == 'require':
                    item = {key: getattr(args, key).strip() for key in ('text', 'acceptance', 'source')}
                    require(all(item.values()), 'Requirement fields must not be empty')
                    changed = state['requirements'].get(args.id) != item
                    if changed:
                        state['requirements'][args.id] = item
                        save_state(store, state)
                    result, code = {'id': args.id, 'registered': True, 'changed': changed}, 0
                else:
                    try:
                        result, code = check(project, store, state, args)
                    except (OSError, ValueError, TypeError, KeyError) as error:
                        state['attempt_errors'][args.id] = {
                            'error': str(error), 'recorded_at_utc': datetime.now(timezone.utc).isoformat()}
                        save_state(store, state)
                        result, code = {'recorded_checks_current': False, 'id': args.id, 'error': str(error)}, 2
    except (OSError, ValueError, TypeError, KeyError) as error:
        result, code = {'recorded_checks_current': False, 'error': str(error)}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
