# Storage maintenance

Use a manual monthly scrub on AC power. No smartd daemon, balance or
defragmentation job is enabled. Btrfs scrub verifies allocated checksummed
data and metadata; it is not a backup. The filesystem has SINGLE data and
DUP metadata, so detection does not imply that every damaged data extent
could be repaired. [Btrfs scrub documentation](https://btrfs.readthedocs.io/en/latest/btrfs-scrub.html)

Run in a terminal that remains open until completion:

```sh
doas btrfs scrub start -B --limit 256M /
```

The foreground form makes completion and errors visible. Closing the terminal
can interrupt the scrub. For a deliberately detached one-shot run, a separate
session plus redirected input/output is necessary; there is no need to install
a scheduler merely for this operation. Status persists under `/var/lib/btrfs`:

```sh
doas btrfs scrub status /
doas btrfs device stats /
```

If interrupted, resume the existing pass rather than repeatedly starting over:

```sh
doas btrfs scrub resume -B --limit 256M /
```

Do not suspend, hibernate or reboot during a planned maintenance pass. If the
machine must be put away, cancel the scrub cleanly and resume later. Investigate
checksum, media or uncorrectable errors and protect important files before
attempting further repair.

`smartmontools` is installed solely for occasional read-only NVMe health checks:

```sh
doas smartctl -a /dev/nvme0n1
```

No destructive test or drive firmware update is part of this procedure. The
2026-09-05 baseline was Samsung 980 PRO 1TB, firmware 5B2QGXA7, zero media/error
log entries, 100% spare, 1% used and 350 historical unsafe shutdowns. Compare
new counts with that baseline; the historical count alone does not identify
the cause of an unsafe power loss.

Root and `/.snapshots` use `commit=30`, the default Btrfs transaction interval.
It replaces the old 120-second interval because reliability takes priority
and there was no measured benefit supporting the longer interval. This
shortens the periodic commit window by 90 seconds; it does not guarantee an
exact bound on application data loss. Applications still need correct
`fsync` behavior. [Btrfs mount options](https://btrfs.readthedocs.io/en/latest/btrfs-man5.html)

## Weekly snapshots

`weekly-snapshot` retains the four newest weekly snapshots under
`/.snapshots/weekly/YYYY-MM-DDTHH:MM:SSZ`. Each contains the root filesystem,
including `/home/bren`, and a copy of the separate FAT `/boot` partition.
The completed snapshot is read-only. Existing manually named snapshots outside
this directory are preserved.

BusyBox is already installed. Its `crond` runs in the foreground under runit,
using `/etc/cron/crontabs/root`. The job checks at service startup and at minute
15 of every hour, creating a snapshot only when the newest is at least seven
days old. A missed week is caught up at the next check; missed weeks are not
filled with redundant copies. Logs, including failures, go through `svlogd`
to `/var/log/cron` with its normal size-based rotation. No email is sent.

Snapshots share unchanged file data; they do not make four full copies of home.
Changes and deletions retain old blocks, so four snapshots are a retention limit,
not a fixed space budget. VM images, games and caches remain included. Creation
is deferred with an error below 20 GiB free; existing snapshots can still grow
in exclusive usage as live files change. Check `btrfs filesystem usage /` and
the cron log periodically. Snapshots on this SSD do not replace another-device
backups and do not include unsaved application data or nested subvolumes.

The job validates the current mount layout and home subvolume, serializes its
own runs with `flock`, and briefly takes pacman's native database lock while
capturing root and `/boot`. If pacman is busy, it retries at a later check.
The job's temporary database lock is removed from the saved snapshot.
Failed creation is cleaned up without pruning the four existing restore points;
new snapshots are completed and flushed before old ones are pruned. A partial
`.pending` snapshot from a crash is removed at the next run. An uncatchable crash
while holding `/var/lib/pacman/db.lck` can leave that lock behind, just as a crashed
pacman transaction can; inspect its recorded PID and confirm no package manager
is running before removing a stale lock manually.

Install from this repository after reviewing the files:

```sh
python3 -B tests/weekly-snapshot.py
doas ./scripts/install-weekly-snapshot
doas sv status /run/runit/service/cron /run/runit/service/cron/log
doas tail /var/log/cron/current
```

The installer first checks the real cron daemon with harmless jobs in an isolated
filesystem; this takes up to a minute and requires root for cron's credential
changes. It then copies the helper, root crontab and runit service, runs the first
due snapshot, then enables `/etc/runit/runsvdir/default/cron`. Runit starts it
automatically. No package installation or reboot is needed. Reinstallation
refuses to overwrite a different existing cron configuration. The test suite
uses the existing Python and bubblewrap with simulated Btrfs commands; it does
not snapshot, delete or mount the host filesystem. The cron integration test is
skipped in an unprivileged test run and is required by the root installer.

To check or run a due snapshot manually:

```sh
doas /usr/local/sbin/weekly-snapshot
doas ls -l /.snapshots/weekly
```

Recover an individual file by copying it out of the chosen snapshot's
`home/bren/` directory. Whole-system recovery is an offline operation from a
live environment: preserve the current root as a recovery path, create a
writable snapshot of the selected restore point as `@`, and restore that same
snapshot's `boot/` contents to the EFI partition. Keep the existing `@snapshots`
and swap partition. Because home belongs to `@`, whole-root rollback also rolls
back home; protect newer personal files first. Do not switch the active root
from the running desktop or assume a root-only rollback restores `/boot`.
