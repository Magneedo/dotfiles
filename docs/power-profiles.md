# Framework power profiles

`Mod+Shift+Escape` opens `tofi-power-profile`. The prompt shows the current
profile. Choose `battery-saver`, `normal` or `performance`; Escape cancels. Repeated
presses open only one menu. The existing `Mod+Escape` power menu remains available.

| Profile | Intel energy preference | Turbo |
| --- | --- | --- |
| battery-saver | `power` | Disabled |
| normal | `balance_performance` | Enabled |
| performance | `performance` | Enabled |

All three use the adaptive `powersave` governor with active `intel_pstate`.
The helper checks every CPU policy before writing, reads back the applied
settings, and only then records a successfully selected profile. `status`
reads the actual CPU settings and reports `custom` if they do not match a profile.
No background service or additional runtime package is required; this uses
the existing shell, util-linux `flock`, coreutils, doas and tofi.

Normal preserves the reference machine's CPU policy. Battery Saver trades peak
performance for lower burst power. Performance favors speed and can increase
heat and fan activity. Actual energy savings depend on the workload; no battery
runtime or benchmark improvement is assumed. Existing frequency limits,
brightness, device power settings and firmware thermal limits are retained.

## Installation

Run the installer script after reviewing the source:

```sh
cd ~/Projects/dotfiles
python3 tests/power-profile.py
install -Dm0755 home/.local/bin/tofi-power-profile ~/.local/bin/tofi-power-profile
doas ./scripts/install-power-profile

cd ~/Projects/dwl
make
doas make install
```

Restart dwl to activate the new shortcut. After installing the scripts, the menu
can also be opened immediately by running `tofi-power-profile`.
Installation does not change the running CPU profile.

The selector lives in `~/.local/bin/tofi-power-profile`, alongside the other tofi
scripts, and is installed as your user. When moving from the earlier system-wide
location, remove the old copy with `doas rm /usr/local/bin/tofi-power-profile`.

The dotfiles install places these root-owned executable files:

- `/usr/local/sbin/power-profile`: profile controller and read-only status.
- `/usr/local/bin/hibernate`: existing lock/hibernate helper with profile
  restoration after the kernel returns from hibernation.
- `/etc/local.d/power-profile.start`: select Normal at boot through the existing
  Artix runit stage-2 startup hook.
- `/etc/elogind/system-sleep/power-profile`: restore the selection after
  elogind-managed suspend or hibernation.

The installer preserves the existing `/etc/doas.conf`, adding only these rules:

```text
permit nopass bren as root cmd /usr/local/sbin/power-profile args battery-saver
permit nopass bren as root cmd /usr/local/sbin/power-profile args normal
permit nopass bren as root cmd /usr/local/sbin/power-profile args performance
permit nopass bren as root cmd /usr/local/sbin/power-profile args resume
```

It validates the combined policy before installing any scripts, saves the
original policy as `/etc/doas.conf.before-power-profile` on the first policy
change, and installs the updated policy with mode `0600`. Repeated installs
do not duplicate the rules or replace that backup. The helper accepts only
the documented commands and uses fixed system paths.

## Selection and persistence

```sh
/usr/local/sbin/power-profile status
doas -n /usr/local/sbin/power-profile battery-saver
doas -n /usr/local/sbin/power-profile normal
doas -n /usr/local/sbin/power-profile performance
```

Changes are serialized with `flock`. The last successfully applied profile is
stored under root-owned `/run/power-profile`, surviving suspend and hibernation
but resetting on a fresh boot. Resume defaults to Normal if no profile has yet
been selected. Invalid saved state fails visibly. Connecting or disconnecting
the charger does not change profiles.

The existing hibernate command writes directly to `/sys/power/state`, so it
restores the profile itself after return; this path does not invoke elogind.
Screen locking and the hibernation request are otherwise unchanged.

## Validation

`python3 tests/power-profile.py` needs the already-installed Python 3 and
bubblewrap for tests only.
It runs the real scripts in an unprivileged user namespace with simulated CPU
files and a private `/run`. Tests cover all profile transitions, permissions,
unsupported controls, read-only controls, concurrent changes, menu cancellation
and locking, boot/resume hooks, the direct hibernate sequence, and staged installs.
They do not alter the host's CPU controls, policy or sleep state.

The dwl `make check` suite verifies the configured `Mod+Shift+Escape` binding
with a harmless replacement selector in its isolated compositor.

After installation, check actual CPU settings across profile changes and resume.
Compare battery discharge, responsiveness, temperature and compilation time at
fixed brightness and workload before judging the profile tradeoffs.

## Removal

Select Normal first. Remove the two profile programs and the two startup/resume
hooks listed above, remove the four profile rules from `/etc/doas.conf`, and
remove the final profile-restoration line from the hibernate helper. Preserve
later unrelated doas edits instead of blindly restoring the backup. Remove the
profile binding from dwl and rebuild it. `/run/power-profile` is cleared at boot.
