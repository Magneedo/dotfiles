# dotfiles

bren's configuration for an Artix Linux (runit) laptop running
[dwl](https://github.com/Magneedo/brendwl) on Wayland. The files are plain
copies of the live ones, laid out the way they sit on disk: no symlinks and no
dotfile manager.

## Install

[brenOS](https://github.com/Magneedo/brenOS) installs everything on a fresh
Artix system. To take single files, copy them:

```sh
git clone https://github.com/Magneedo/dotfiles ~/Projects/dotfiles
cp ~/Projects/dotfiles/home/.config/foot/foot.ini ~/.config/foot/
```

Many files assume the user `bren` and the path `~/Projects/dotfiles`; brenOS
renames them for another user.

## Layout

| Path | What it holds |
| --- | --- |
| `home/` | Mirrors `~`: shell profile, `.config/` (foot, tofi, mako, lf, mpv, swaylock, btop, OBS) and the scripts in `.local/bin` |
| `etc/` | Mirrors `/etc`: doas, nftables, sysctl, cron, runit services |
| `usr/` | Mirrors `/usr/local`: backup, snapshot, network and power helpers that run as root |
| `scripts/` | Installers for the parts that need root or a one-time setup |
| `tests/` | Tests for the power-profile and weekly-snapshot helpers |
| `docs/` | Notes on this machine: [overview](docs/machine-notes.md), [runit](docs/runit.md), [power profiles](docs/power-profiles.md), [storage and backups](docs/storage-maintenance.md) |

## Scripts in `home/.local/bin`

| Script | What it does |
| --- | --- |
| `dwl-session`, `dwl-autostart` | Start dwl at login, then the bar, notifications, wallpaper and status |
| `statusd` | Status text for the bar, with click and scroll actions |
| `bar-panel` | Calendar and notification history cards for the bar's clock |
| `tofi-power`, `tofi-power-profile`, `tofi-net`, `tofi-audio`, `tofi-emoji` | Menus: power, power profile, network, audio output, emoji and symbols |
| `screenshots`, `bluefilter`, `wallpaper`, `fetch` | Region screenshot to file and clipboard, blue light filter, wallpaper, system summary |
| `tv` | Pick a channel, movie or episode in fzf and play it in mpv |
| `dotfiles-drift` | List live files that differ from their copy here |
| `brenbots`, `agentdesk`, `agent-notify`, `mcp-lazy`, `mailbox`, `no-ai-attribution` | Tools for the coding agents: their tmux popup, a headless desktop for them, notifications, on-demand MCP servers, mail over SSH, and a commit hook |

## Keeping it current

Change a live file that has a copy here and update the copy too.
`dotfiles-drift` lists the files that differ or are missing and exits 1 if
there are any.

## Look

Colors and font follow stock dwl: `#222222` background, `#444444` lines,
`#005577` accent, `#eeeeee` text, `#bbbbbb` muted text, Noto Sans Mono 14.

## Related

- [brendwl](https://github.com/Magneedo/brendwl): the compositor.
- [brendwlb](https://github.com/Magneedo/brendwlb): the bar.
- [brenOS](https://github.com/Magneedo/brenOS): the installer.

## License

MIT: see [LICENSE](LICENSE). The character list for the emoji picker is built
from Unicode data under
[its own license](home/.local/share/tofi/LICENSE.unicode).
