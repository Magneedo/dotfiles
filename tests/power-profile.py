#!/usr/bin/env python3
"""Exercise real scripts in a user namespace with simulated CPU controls."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
HELPER = '/usr/local/sbin/power-profile'
MENU = REPO / 'home/.local/bin/tofi-power-profile'
MODES = {
    'battery-saver': ('power', '1'),
    'normal': ('balance_performance', '0'),
    'performance': ('performance', '0'),
}


class Profiles(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='power-profile-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.cpu = self.root / 'sys/devices/system/cpu'
        self.runtime = self.root / 'run'
        self.runtime.mkdir()
        self.state = self.runtime / 'power-profile/profile'
        (self.root / 'sys/power').mkdir(parents=True)
        (self.root / 'sys/power/state').write_text('')
        (self.cpu / 'intel_pstate').mkdir(parents=True)
        (self.cpu / 'intel_pstate/status').write_text('active\n')
        (self.cpu / 'intel_pstate/no_turbo').write_text('0\n')
        (self.cpu / 'intel_pstate/min_perf_pct').write_text('10\n')
        (self.cpu / 'intel_pstate/max_perf_pct').write_text('100\n')
        self.policies = [self.cpu / 'cpufreq' / name
                         for name in ('policy0', 'policy1', 'policy10')]
        for policy in self.policies:
            policy.mkdir(parents=True)
            for name, value in {
                'scaling_driver': 'intel_pstate',
                'scaling_governor': 'powersave',
                'energy_performance_preference': 'balance_performance',
                'energy_performance_available_preferences':
                    'default performance balance_performance balance_power power ',
            }.items():
                (policy / name).write_text(value + '\n')
        shutil.copytree(REPO / 'usr/local', self.root / 'usr/local')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.stub('tofi', 'cat > /run/menu-input\nprintf "%s\\n" "$*" > /run/menu-args\n'
                  'printf "menu\\n" >> /run/menu-opens\nsleep "${TEST_DELAY:-0}"\n'
                  'printf "%s\\n" "${TEST_SELECTION:-}"\nexit "${TEST_EXIT:-0}"\n')
        self.stub('doas', '[ "$1" = -n ]\nshift\nprintf "%s\\n" "$*" >> /run/actions\nexec "$@"\n')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/sh\nset -eu\n' + body)
        path.chmod(0o755)

    def command(self, *args, uid=0, mounts=()):
        return ['bwrap', '--unshare-user', '--uid', str(uid), '--gid', str(uid),
                '--unshare-pid', '--die-with-parent', '--new-session',
                '--ro-bind', '/', '/', '--dev', '/dev', '--proc', '/proc',
                '--bind', str(self.root / 'sys'), '/sys',
                '--bind', str(self.runtime), '/run',
                '--ro-bind', str(self.root / 'usr/local'), '/usr/local',
                *mounts, '--', *map(str, args)]

    def run_script(self, *args, success=True, uid=0, mounts=(), **environment):
        env = dict(os.environ, XDG_RUNTIME_DIR='/run',
                   PATH=str(self.bin) + ':/usr/bin:/bin', **environment)
        result = subprocess.run(self.command(*args, uid=uid, mounts=mounts),
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(path.relative_to(self.cpu)): path.read_text()
                for path in self.cpu.rglob('*') if path.is_file()}

    def assert_profile(self, profile):
        preference, turbo = MODES[profile]
        self.assertEqual((self.cpu / 'intel_pstate/no_turbo').read_text(), turbo + '\n')
        for policy in self.policies:
            self.assertEqual((policy / 'scaling_governor').read_text(), 'powersave\n')
            self.assertEqual((policy / 'energy_performance_preference').read_text(), preference + '\n')
        self.assertEqual(self.state.read_text(), profile + '\n')
        self.assertEqual(self.run_script(HELPER, 'status', uid=1000).stdout.strip(), profile)

    def test_every_transition_and_limits(self):
        for before in MODES:
            for after in MODES:
                with self.subTest(before=before, after=after):
                    self.run_script(HELPER, before)
                    self.run_script(HELPER, after)
                    self.assert_profile(after)
        self.assertEqual((self.cpu / 'intel_pstate/min_perf_pct').read_text(), '10\n')
        self.assertEqual((self.cpu / 'intel_pstate/max_perf_pct').read_text(), '100\n')

    def test_status_is_read_only_and_detects_mixed_settings(self):
        before = self.snapshot()
        self.assertEqual(self.run_script(HELPER, 'status', uid=1000).stdout, 'normal\n')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.state.parent.exists())
        (self.policies[1] / 'energy_performance_preference').write_text('power\n')
        self.assertEqual(self.run_script(HELPER, 'status').stdout, 'custom\n')

    def test_bad_arguments_and_unprivileged_writes_are_rejected(self):
        before = self.snapshot()
        for args in ((), ('invalid',), ('normal', 'extra')):
            self.run_script(HELPER, *args, success=False)
        self.run_script(HELPER, 'performance', uid=1000, success=False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.state.exists())

    def test_preflight_failure_preserves_cpu_and_saved_profile(self):
        self.run_script(HELPER, 'normal')
        path = self.policies[1] / 'energy_performance_available_preferences'
        path.write_text('balance_performance\n')
        before = self.snapshot()
        self.run_script(HELPER, 'battery-saver', success=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.state.read_text(), 'normal\n')
        (self.cpu / 'intel_pstate/status').write_text('passive\n')
        self.run_script(HELPER, 'normal', success=False)

    def test_read_only_policy_is_rejected_before_any_cpu_changes(self):
        before = self.snapshot()
        path = self.policies[1] / 'energy_performance_preference'
        mounts = ('--ro-bind', str(path), '/sys/' + str(path.relative_to(self.root / 'sys')))
        self.run_script(HELPER, 'battery-saver', mounts=mounts, success=False)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.state.exists())

    def test_boot_and_elogind_resume(self):
        self.run_script(HELPER, 'resume')
        self.assert_profile('normal')
        self.run_script(HELPER, 'performance')
        for policy in self.policies:
            (policy / 'energy_performance_preference').write_text('balance_performance\n')
        before = self.snapshot()
        hook = REPO / 'etc/elogind/system-sleep/power-profile'
        self.run_script(hook, 'pre', 'suspend')
        self.assertEqual(self.snapshot(), before)
        self.run_script(hook, 'post', 'suspend')
        self.assert_profile('performance')
        self.run_script(REPO / 'etc/local.d/power-profile.start')
        self.assert_profile('normal')
        self.state.write_text('invalid\n')
        before = self.snapshot()
        self.run_script(HELPER, 'resume', success=False)
        self.assertEqual(self.snapshot(), before)

    def test_concurrent_switches_save_the_applied_profile(self):
        processes = [subprocess.Popen(self.command(HELPER, mode),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for mode in list(MODES) * 3]
        for process in processes:
            out, err = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, out + err)
        self.assert_profile(self.state.read_text().strip())
        self.assertFalse((self.state.parent / 'profile.tmp').exists())

    def test_menu_selection_and_cancellation(self):
        for label, profile in (('battery-saver', 'battery-saver'),
                               ('normal', 'normal'), ('performance', 'performance')):
            self.run_script(MENU, TEST_SELECTION=label)
            self.assert_profile(profile)
        before = self.snapshot()
        actions = (self.runtime / 'actions').read_text()
        self.run_script(MENU)
        self.run_script(MENU, TEST_EXIT='1', success=False)
        self.run_script(MENU, TEST_SELECTION='arbitrary', success=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual((self.runtime / 'actions').read_text(), actions)
        self.assertIn('profile (performance):', (self.runtime / 'menu-args').read_text())
        self.assertEqual((self.runtime / 'menu-input').read_text(),
                         'battery-saver\nnormal\nperformance\n')

    def test_repeated_menu_press_opens_one_menu(self):
        env = dict(os.environ, XDG_RUNTIME_DIR='/run', TEST_DELAY='1',
                   PATH=str(self.bin) + ':/usr/bin:/bin')
        processes = [subprocess.Popen(self.command(MENU),
                                      env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for _ in range(6)]
        for process in processes:
            out, err = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, out + err)
        self.assertEqual((self.runtime / 'menu-opens').read_text(), 'menu\n')

    def test_direct_hibernate_restores_profile_after_lock_and_resume(self):
        self.run_script(HELPER, 'battery-saver')
        for policy in self.policies:
            (policy / 'energy_performance_preference').write_text('balance_performance\n')
        self.stub('id', 'printf "1000\\n"\n')
        self.stub('swaylock', '[ "$1" = -f ]\nprintf "locked\\n" >> /run/actions\n')
        self.run_script('/usr/local/bin/hibernate', WAYLAND_DISPLAY='test')
        self.assert_profile('battery-saver')
        self.assertEqual((self.root / 'sys/power/state').read_text(), 'disk\n')
        self.assertEqual((self.runtime / 'actions').read_text().splitlines(),
                         ['locked', '/usr/bin/tee /sys/power/state', HELPER + ' resume'])


class Installation(unittest.TestCase):
    def test_install_preserves_policy_and_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='profile-install-test-') as directory:
            root = Path(directory)
            (root / 'etc').mkdir()
            policy = root / 'etc/doas.conf'
            original = 'permit persist :wheel\n# Keep my local rules.\n'
            policy.write_text(original)
            for _ in range(2):
                subprocess.run([str(REPO / 'scripts/install-power-profile'), directory],
                               cwd=REPO, check=True, capture_output=True, text=True)
            self.assertTrue(policy.read_text().startswith(original))
            self.assertEqual(policy.read_text().count('cmd ' + HELPER), 4)
            self.assertEqual(policy.stat().st_mode & 0o777, 0o600)
            self.assertEqual((root / 'etc/doas.conf.before-power-profile').read_text(), original)
            for relative in ('usr/local/sbin/power-profile', 'usr/local/bin/hibernate',
                             'etc/local.d/power-profile.start',
                             'etc/elogind/system-sleep/power-profile'):
                installed = root / relative
                self.assertEqual(installed.read_bytes(), (REPO / relative).read_bytes())
                self.assertEqual(installed.stat().st_mode & 0o777, 0o755)
            self.assertFalse((root / 'run').exists())
            self.assertFalse((root / 'usr/local/bin/tofi-power-profile').exists())
            self.assertEqual(list((root / 'etc').glob('.doas-power-profile.*')), [])

    def test_invalid_policy_stops_installation(self):
        with tempfile.TemporaryDirectory(prefix='profile-install-test-') as directory:
            root = Path(directory)
            (root / 'etc').mkdir()
            policy = root / 'etc/doas.conf'
            policy.write_text('not a valid policy\n')
            result = subprocess.run([str(REPO / 'scripts/install-power-profile'), directory],
                                    cwd=REPO, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'usr').exists())
            self.assertEqual(policy.read_text(), 'not a valid policy\n')


if __name__ == '__main__':
    unittest.main()
