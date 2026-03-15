# Machine notes

## Base system
- Artix Linux
- runit
- seatd
- Framework 13 1240P
- Wayland, dwl

## Boot / filesystem
- EFISTUB
- Btrfs root with subvolumes
- Swap partition present
- Hibernate via `/sys/power/state`

## Core services enabled
- See `docs/runit-enabled-services.txt` (canonical list).
