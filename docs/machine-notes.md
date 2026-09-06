# Machine notes

## Base system
- Artix Linux
- runit
- seatd
- Framework 13 1240P
- Wayland, dwl

## Boot / filesystem
- Direct EFISTUB + Booster with the normal `linux` kernel.
- `Boot0000`, labeled `Artix`, is the only Artix EFI entry and the default boot.
  BootOrder: `0000,2001,2002,2003`.
- The EFI entry uses `\vmlinuz-linux`, `\intel-ucode.img` and
  `\booster-linux.img`; it selects the normal/default runit runlevel.
- Btrfs root with subvolumes
- Hibernation uses a dedicated swap partition and the existing `resume=UUID`
  argument with Booster. No swapfile resume offset is needed.
- `/usr/local/bin/hibernate` locks the Wayland session with `swaylock -f`
  before requesting hibernation through `/sys/power/state`. Physical testing
  confirmed locking, hibernation, resume and successful return to the dwl session.
- Btrfs uses the default 30-second commit interval; monthly scrub on AC is the
  maintenance cadence. See `storage-maintenance.md`.

## Core services enabled
- See `runit-enabled-services.txt` for the eleven enabled services.
- Service definitions live in `/etc/runit/sv`; the enabled links are under
  `/etc/runit/runsvdir/default`, and `/etc/runit/runsvdir/current` points to
  `default`. See `runit.md` for the intentional service customizations.
