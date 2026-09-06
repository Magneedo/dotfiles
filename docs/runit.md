# Runit services

The system uses the normal/default runlevel. Canonical service definitions
are under `/etc/runit/sv`, enabled service links are under
`/etc/runit/runsvdir/default`, and `/etc/runit/runsvdir/current -> default`.
`runit-enabled-services.txt` lists the eleven enabled services.

Intentional customizations are stored directly under `etc/runit/sv` in this
repository. They preserve tty1 autologin for `bren`, foreground dhcpcd with
`-B -q -w`, the existing wlan0/profile selection and wpa_supplicant runtime
directory setup, and seatd startup with group `seat` and readiness checked
through `/run/seatd.sock`. tty2 remains a normal getty console.

Package upgrades may replace locally modified package-owned service files.
This is accepted; there is no automatic upgrade protection or repair mechanism.
