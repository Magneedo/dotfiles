# Machine notes

## Base system
- Artix Linux
- runit
- seatd
- Framework 13 1240P
- Wayland, dwl

## Power menu
- `home/.local/bin/tofi-power` provides lock, hibernate, reboot and poweroff
  through the existing `/usr/local/bin` helpers. Install it to `~/.local/bin`
  with mode `0755`; it uses the existing tofi configuration and util-linux's
  `flock` to prevent duplicate menus.
- Run `tofi-power`, or use `Mod+Escape` after rebuilding and installing dwl
  with the new binding. Type to filter, press Enter to run the selected action,
  or Escape to cancel. The menu lock is released before an action starts.
- `Mod+Shift+Escape` opens `~/.local/bin/tofi-power-profile` with `battery-saver`,
  `normal` and `performance`. Normal is selected at boot; manual choices survive
  suspend and hibernation. See [power profiles](power-profiles.md) for installation
  and tests.

## Emoji and character picker
- `Mod+period` opens `tofi-emoji` in a centered popup. Type a name such as
  `grinning`, `technologist`, `arrow`, `integral`, or `greek`, then use the arrow
  keys and Enter to insert the selection into the previously focused app.
  The character is also copied to the clipboard for reuse. Escape cancels
  without typing or changing the clipboard. Selection inserts only the character
  or complete emoji sequence, with no description or trailing newline.
- Install `home/.local/bin/tofi-emoji` to `~/.local/bin` with mode `0755`,
  `home/.config/tofi/emoji` to `~/.config/tofi/emoji`, and
  `home/.local/share/tofi/` to `~/.local/share/tofi/`. It uses the existing
  `tofi`, `wl-clipboard`, `wtype` and util-linux `flock` packages. `wtype` sends
  Unicode key events after the menu closes, so it also works in terminals
  without needing a different paste shortcut. Repeated presses cannot
  open duplicate menus. Run `tofi-emoji` directly before restarting dwl to use
  the new binding. Monitor focus moves to `Mod+Ctrl+comma/period`; the shifted
  bindings for moving windows between monitors remain available.
- The offline catalogue contains 15,309 supported emoji, punctuation, symbols,
  numbers, Latin, Greek and Cyrillic characters. It includes skin tones and
  joined emoji sequences. Names come from Unicode 17.0, and no network access
  is needed to open the picker. History is disabled.
- Both tofi configurations use font family names so Pango can find fallback
  fonts. Generic fontconfig aliases prefer Noto Sans, Serif and Sans Mono,
  with Noto Color Emoji before Noto symbol fallbacks. Keep `noto-fonts`,
  `noto-fonts-cjk`, `noto-fonts-emoji` and `noto-fonts-extra`; installed coverage
  is already broad. No font packages were added or removed.
- The catalogue generator checks each entry using Pango with `Noto Sans 16`
  and omits missing glyphs (281 entries on this machine). Regenerate if the
  installed font coverage changes. This prevents known missing glyphs in the
  catalogue; applications with their own fonts or rendering can still show
  missing characters after pasting.

To regenerate, download the pinned [emoji-test.txt](https://www.unicode.org/Public/17.0.0/emoji/emoji-test.txt)
and [UnicodeData.txt](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt)
into one directory, then run `python3 scripts/update-characters.py DIRECTORY`.
The script validates both SHA-256 checksums before writing the catalogue and
uses the existing Pango libraries. Review the resulting diff and copy the new
catalogue into `~/.local/share/tofi/characters.txt`. The associated Unicode
license is tracked as `home/.local/share/tofi/LICENSE.unicode`.

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
  maintenance cadence. BusyBox cron retains four weekly snapshots including
  home and matching boot files. See `storage-maintenance.md`.

## Core services enabled
- See `runit-enabled-services.txt` for the enabled services.
- Service definitions live in `/etc/runit/sv`; the enabled links are under
  `/etc/runit/runsvdir/default`, and `/etc/runit/runsvdir/current` points to
  `default`. See `runit.md` for the intentional service customizations.
