#!/usr/bin/env python3
"""Test snapshot retention and failures without touching host Btrfs state."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parent.parent
HELPER = REPO / 'usr/local/sbin/weekly-snapshot'
WEEK = 7 * 24 * 60 * 60
MOCK = '''#!/usr/bin/python3
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

name = Path(sys.argv[0]).name
args = sys.argv[1:]
settings = json.loads(Path('/run/settings').read_text())
with open('/run/calls', 'a') as output:
    output.write(json.dumps([name, *args]) + '\\n')
if name == 'date':
    if '-d' in args:
        print(int(datetime.fromisoformat(args[args.index('-d') + 1]).timestamp()))
    elif args[-1] == '+%s':
        print(settings['now'])
    else:
        print(datetime.fromtimestamp(settings['now'], timezone.utc).strftime(args[-1][1:]))
elif name == 'findmnt':
    field = args[1]
    if field == 'FSTYPE':
        print('btrfs')
    elif field == 'FSROOT':
        print('wrong' if settings.get('bad_mount') else '/@snapshots')
    else:
        print('same-filesystem')
elif name == 'mountpoint':
    sys.exit(1 if settings.get('missing_boot') else 0)
elif name == 'df':
    print('Filesystem 1024-blocks Used Available Capacity Mounted on')
    print('disk 900000000 500000000', settings.get('available', 400000000), '60% /')
elif name == 'sync':
    pass
elif name == 'cp':
    destination = Path(args[-1])
    for index, source in enumerate(Path('/boot').iterdir()):
        shutil.copy2(source, destination / source.name)
        if settings.get('copy_failure') and index == 0:
            sys.exit(1)
        if settings.get('interrupt_copy') and index == 0:
            os.kill(os.getppid(), signal.SIGTERM)
            sys.exit(1)
elif name == 'btrfs':
    if args[:2] == ['inspect-internal', 'rootid']:
        print(284 if settings.get('separate_home') and args[-1] != '/' else 283)
    elif args[:2] == ['subvolume', 'snapshot']:
        destination = Path(args[-1])
        assert args[2] == '/'
        assert Path('/var/lib/pacman/db.lck').is_file()
        shutil.copytree('/run/source', destination)
        (destination / 'var/lib/pacman').mkdir(parents=True)
        shutil.copy2('/var/lib/pacman/db.lck', destination / 'var/lib/pacman/db.lck')
        (destination / '.mock-ro').write_text('false')
        time.sleep(settings.get('snapshot_delay', 0))
    elif args[:2] == ['property', 'set']:
        Path(args[3], '.mock-ro').write_text(args[-1])
    elif args[:2] == ['property', 'get']:
        print('ro=' + Path(args[3], '.mock-ro').read_text())
    elif args[:2] == ['subvolume', 'delete']:
        target = Path(args[-1])
        assert not target.is_symlink()
        assert target.parent == Path('/.snapshots/weekly')
        assert (target / '.mock-ro').is_file()
        shutil.rmtree(target)
    else:
        raise AssertionError(args)
else:
    raise AssertionError(name)
'''


class Snapshots(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='weekly-snapshot-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ('run', 'snapshots', 'boot', 'database'):
            (self.root / directory).mkdir()
        self.destination = self.root / 'snapshots/weekly'
        source = self.root / 'run/source'
        (source / 'boot').mkdir(parents=True)
        (source / 'home/bren').mkdir(parents=True)
        (source / 'home/bren/important.txt').write_text('personal data\n')
        for name in ('vmlinuz-linux', 'intel-ucode.img', 'booster-linux.img'):
            (self.root / 'boot' / name).write_text('boot data: ' + name)
        self.mock = self.root / 'mock'
        self.mock.write_text(MOCK)
        self.mock.chmod(0o755)
        self.settings = {'now': 1789941600}
        self.save_settings()

    def save_settings(self, **settings):
        self.settings.update(settings)
        (self.root / 'run/settings').write_text(json.dumps(self.settings))

    def command(self):
        command = ['bwrap', '--unshare-user', '--uid', '0', '--gid', '0',
                   '--unshare-pid', '--die-with-parent', '--new-session',
                   '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc']
        for source, target in (('run', '/run'), ('snapshots', '/.snapshots'),
                               ('boot', '/boot'), ('database', '/var/lib/pacman')):
            command += ['--bind', str(self.root / source), target]
        for name in ('date', 'findmnt', 'mountpoint', 'df', 'sync', 'cp', 'btrfs'):
            command += ['--ro-bind', str(self.mock), '/usr/bin/' + name]
        return command + ['--', str(HELPER)]

    def run_helper(self, success=True):
        result = subprocess.run(self.command(), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def snapshots(self):
        return sorted(self.destination.glob('20*-*T*Z'))

    def advance(self, seconds=WEEK):
        self.save_settings(now=self.settings['now'] + seconds)

    def assert_clean(self):
        self.assertFalse((self.destination / '.pending').exists())
        self.assertFalse((self.root / 'database/db.lck').exists())

    def test_home_boot_readonly_and_not_due(self):
        self.run_helper()
        snapshot, = self.snapshots()
        self.assertEqual((snapshot / 'home/bren/important.txt').read_text(), 'personal data\n')
        for boot_file in (self.root / 'boot').iterdir():
            self.assertEqual((snapshot / 'boot' / boot_file.name).read_bytes(), boot_file.read_bytes())
        self.assertEqual((snapshot / '.mock-ro').read_text(), 'true')
        self.assertFalse((snapshot / 'var/lib/pacman/db.lck').exists())
        self.advance(WEEK - 1)
        self.run_helper()
        self.assertEqual(self.snapshots(), [snapshot])
        self.assert_clean()

    def test_four_weeks_and_manual_snapshots_survive(self):
        manual = self.root / 'snapshots/root-barebones'
        manual.mkdir()
        (manual / 'keep').write_text('historical')
        created = []
        for _ in range(6):
            self.run_helper()
            created.append(self.snapshots()[-1])
            self.advance()
        self.assertEqual(self.snapshots(), created[-4:])
        self.assertEqual((manual / 'keep').read_text(), 'historical')
        self.assert_clean()

    def test_missed_weeks_produce_one_catchup(self):
        self.run_helper()
        self.advance(8 * WEEK)
        self.run_helper()
        self.assertEqual(len(self.snapshots()), 2)

    def test_copy_failure_and_signal_preserve_restore_points(self):
        for _ in range(4):
            self.run_helper()
            self.advance()
        previous = self.snapshots()
        for setting in ('copy_failure', 'interrupt_copy'):
            self.save_settings(**{setting: True})
            self.run_helper(success=False)
            self.assertEqual(self.snapshots(), previous)
            self.assert_clean()
            self.save_settings(**{setting: False})

    def test_active_package_transaction_is_preserved(self):
        lock = self.root / 'database/db.lck'
        lock.write_text('another package manager\n')
        self.run_helper(success=False)
        self.assertEqual(lock.read_text(), 'another package manager\n')
        self.assertEqual(self.snapshots(), [])
        lock.unlink()
        self.run_helper()
        self.assertEqual(len(self.snapshots()), 1)

    def test_space_and_mount_preflight(self):
        for settings in ({'available': 100}, {'bad_mount': True},
                         {'missing_boot': True}, {'separate_home': True}):
            with self.subTest(settings=settings):
                original = self.settings.copy()
                self.save_settings(**settings)
                self.run_helper(success=False)
                self.assertEqual(self.snapshots(), [])
                self.assert_clean()
                self.settings = original
                self.save_settings()

    def test_stale_partial_is_removed(self):
        self.run_helper()
        pending = self.destination / '.pending'
        pending.mkdir()
        (pending / '.mock-ro').write_text('false')
        self.run_helper()
        self.assertEqual(len(self.snapshots()), 1)
        self.assert_clean()

    def test_unexpected_pending_symlink_is_preserved(self):
        self.run_helper()
        snapshot, = self.snapshots()
        pending = self.destination / '.pending'
        pending.symlink_to('/.snapshots/weekly/' + snapshot.name)
        self.run_helper(success=False)
        self.assertTrue(pending.is_symlink())
        self.assertTrue((snapshot / 'home/bren/important.txt').is_file())

    def test_concurrent_runs_create_once(self):
        self.save_settings(snapshot_delay=0.2)
        processes = [subprocess.Popen(self.command(), stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE) for _ in range(4)]
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(len(self.snapshots()), 1)
        self.assert_clean()


class Installation(unittest.TestCase):
    def test_staged_install_and_reinstall(self):
        with tempfile.TemporaryDirectory(prefix='snapshot-install-test-') as directory:
            root = Path(directory)
            for _ in range(2):
                subprocess.run([str(REPO / 'scripts/install-weekly-snapshot'), directory],
                               check=True, capture_output=True, text=True)
            for path in ('usr/local/sbin/weekly-snapshot', 'etc/runit/sv/cron/run',
                         'etc/runit/sv/cron/log/run', 'etc/cron/crontabs/root'):
                self.assertEqual((root / path).read_bytes(), (REPO / path).read_bytes())
            self.assertEqual((root / 'etc/cron/crontabs/root').stat().st_mode & 0o777, 0o600)
            self.assertEqual(os.readlink(root / 'etc/runit/runsvdir/default/cron'),
                             '/etc/runit/sv/cron')
            self.assertFalse((root / '.snapshots').exists())

    def test_existing_cron_configuration_is_not_replaced(self):
        with tempfile.TemporaryDirectory(prefix='snapshot-install-test-') as directory:
            root = Path(directory)
            crontab = root / 'etc/cron/crontabs/root'
            crontab.parent.mkdir(parents=True)
            crontab.write_text('existing jobs\n')
            result = subprocess.run([str(REPO / 'scripts/install-weekly-snapshot'), directory],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(crontab.read_text(), 'existing jobs\n')
            self.assertFalse((root / 'usr').exists())


class Cron(unittest.TestCase):
    @unittest.skipUnless(os.geteuid() == 0, 'cron credential changes require root; checked by installer')
    def test_real_cron_retries_startup_failure_and_logs_job_output(self):
        with tempfile.TemporaryDirectory(prefix='snapshot-cron-test-') as directory:
            root = Path(directory)
            for path in ('etc/cron/crontabs', 'usr/local/sbin', 'run', 'root'):
                (root / path).mkdir(parents=True)
            for name in ('passwd', 'group', 'nsswitch.conf'):
                shutil.copy2('/etc/' + name, root / 'etc' / name)
            source = (REPO / 'etc/cron/crontabs/root').read_text()
            (root / 'etc/cron/crontabs/root').write_text(
                source.replace('15 * * * *', '* * * * *'))
            helper = root / 'usr/local/sbin/weekly-snapshot'
            helper.write_text('#!/bin/sh\nset -eu\n'
                              'if [ ! -f /run/started ]; then\n'
                              '    touch /run/started\n'
                              '    exit 1\n'
                              'fi\n'
                              'printf "scheduled-job-output\\n"\n'
                              'touch /run/scheduled\n')
            helper.chmod(0o755)
            # A user namespace disables setgroups even when the caller is root.
            command = ['bwrap', '--unshare-pid', '--die-with-parent', '--new-session',
                       '--cap-add', 'CAP_SETUID', '--cap-add', 'CAP_SETGID',
                       '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc']
            for path in ('etc', 'usr/local', 'run', 'root'):
                command += ['--bind', str(root / path), '/' + path]
            command += ['--', str(REPO / 'etc/runit/sv/cron/run')]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 67
                while not (root / 'run/scheduled').exists() and time.monotonic() < deadline:
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
            finally:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate(timeout=5)
            self.assertTrue((root / 'run/scheduled').exists(), stdout + stderr)
            self.assertIn(b'startup snapshot failed', stdout)
            self.assertIn(b'scheduled-job-output', stdout)


if __name__ == '__main__':
    unittest.main()
