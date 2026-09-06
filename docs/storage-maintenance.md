# Storage maintenance

Use a monthly scrub on AC power. No timer service, smartd daemon, balance or
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

The existing snapshots are manually named historical/recovery states, with
ample free space and no automatic creation job found in the reviewed startup
configuration. No automated pruning policy is warranted yet. Retain them
until their purpose and replacement backups are established. If routine
snapshot creation is later introduced, agree a bounded retention rule with
that workflow rather than guessing which historical snapshots to delete.
