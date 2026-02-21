# Brightness Control for External Monitors

Keyboard-driven brightness control for external monitors on Pop!_OS 22.04 / GNOME.

## How It Works

No configuration file. Monitor slots are assigned **alphabetically by stable ID** (`{manufacturer}-{model}-{serial}`) for whatever monitors are currently connected. Slot 1 = alphabetically first, slot 2 = second, etc.

This means:
- Monitor ordering is consistent as long as the same monitors are connected
- Adding/removing a monitor may shift slot numbers (acceptable trade-off for zero config)
- Run `brightness-control --detect` at any time to see the current slot assignments

Detection results are cached for 60 seconds, so repeated keypresses are fast (~40ms vs ~700ms for a cold detection).

## Requirements

- Pop!_OS 22.04 or any GNOME-based distro
- Monitors that support DDC/CI
- `ddcutil`: `sudo apt install ddcutil`
- Python 3.7+

## Installation

```bash
./install.sh
```

The installer:
1. Asks how many monitors to set up shortcuts for
2. Installs `brightness-control` to `~/.local/bin/`
3. Installs library modules to `~/.local/lib/brightness-control/`
4. Creates GNOME keyboard shortcuts
5. Adds you to the `i2c` group (requires logout)

**Log out and back in** after installation for i2c permissions to take effect.

## Default Shortcuts

| Shortcut | Action |
|---|---|
| `Super+Shift+F1` | Monitor 1 brightness down |
| `Super+Shift+F2` | Monitor 1 brightness up |
| `Super+Shift+F3` | Monitor 2 brightness down |
| `Super+Shift+F4` | Monitor 2 brightness up |

## Command Line

```bash
brightness-control -m 1 -a up      # Monitor 1 brightness up
brightness-control -m 2 -a down    # Monitor 2 brightness down
brightness-control --detect        # Show current slot assignments
```

## File Layout

```
~/.local/bin/
└── brightness-control              # Main executable

~/.local/lib/brightness-control/
├── monitor_detector.py             # Parses ddcutil output, creates stable IDs
└── ddcutil_wrapper.py              # ddcutil commands + monitor cache

/tmp/brightness-control-$USER-bus-cache.json   # Runtime cache (60s TTL)
```

## Troubleshooting

**No monitors detected**
```bash
ddcutil detect          # Test ddcutil directly
ls -l /dev/i2c-*        # Check I2C devices exist
```

**Permission denied**
```bash
sudo usermod -aG i2c $USER   # Add to i2c group
# Then log out and back in
```

**Wrong monitor responding**
```bash
brightness-control --detect   # Show current slot assignments (alphabetical by stable ID)
```

**Shortcut does nothing**
```bash
brightness-control -m 1 -a up   # Test manually first
which brightness-control         # Verify it's in PATH
```

## Uninstallation

```bash
./uninstall.sh
```
