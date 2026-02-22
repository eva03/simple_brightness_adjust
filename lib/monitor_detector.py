#!/usr/bin/env python3
"""
Monitor detection and identification module.

Detects monitors via ddcutil and creates stable monitor IDs
that persist across reboots and I2C bus number changes.
"""

import re
import subprocess
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Monitor:
    """Represents a detected monitor with stable identification."""
    manufacturer: str
    model: str
    serial: str
    i2c_bus: str
    stable_id: str

    def __post_init__(self):
        """Generate stable ID if not provided."""
        if not self.stable_id:
            self.stable_id = f"{self.manufacturer}-{self.model}-{self.serial}"


def detect_monitors() -> List[Monitor]:
    """
    Run ddcutil detect and parse output into Monitor objects.

    Returns:
        List of detected monitors with stable IDs.

    Raises:
        RuntimeError: If ddcutil command fails.
    """
    try:
        result = subprocess.run(
            ['ddcutil', 'detect', "--sleep-multiplier", ".1"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"ddcutil detect failed: {result.stderr}")

        return parse_ddcutil_detect(result.stdout)

    except FileNotFoundError:
        raise RuntimeError("ddcutil not found. Install with: sudo apt install ddcutil")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ddcutil detect timed out after 30 seconds")


def parse_ddcutil_detect(output: str) -> List[Monitor]:
    """
    Parse ddcutil detect output to extract monitor information.

    Expected format:
        Display 1
           I2C bus:  /dev/i2c-4
           ...
           Mfg id:               DEL
           Model:                DELL U3419W
           Serial number:        9B6SWP2

    Args:
        output: Raw stdout from ddcutil detect.

    Returns:
        List of Monitor objects sorted by stable ID.
    """
    monitors = []
    current_monitor = {}

    # Pattern to match I2C bus: /dev/i2c-X
    bus_pattern = re.compile(r'I2C bus:\s+(/dev/i2c-\d+)')
    # Pattern to match manufacturer ID
    mfg_pattern = re.compile(r'Mfg id:\s+(\w+)', re.IGNORECASE)
    # Pattern to match model name
    model_pattern = re.compile(r'Model:\s+(.+)')
    # Pattern to match serial number
    serial_pattern = re.compile(r'Serial number:\s+(.+)')

    for line in output.split('\n'):
        line = line.strip()

        # Check for I2C bus (indicates start of new monitor)
        bus_match = bus_pattern.search(line)
        if bus_match:
            # Save previous monitor if complete
            if _is_monitor_complete(current_monitor):
                monitors.append(_create_monitor(current_monitor))
            # Start new monitor
            current_monitor = {'i2c_bus': bus_match.group(1)}
            continue

        # Extract manufacturer
        mfg_match = mfg_pattern.search(line)
        if mfg_match and current_monitor:
            current_monitor['manufacturer'] = mfg_match.group(1)
            continue

        # Extract model
        model_match = model_pattern.search(line)
        if model_match and current_monitor:
            current_monitor['model'] = model_match.group(1).strip()
            continue

        # Extract serial number
        serial_match = serial_pattern.search(line)
        if serial_match and current_monitor:
            current_monitor['serial'] = serial_match.group(1).strip()
            continue

    # Don't forget the last monitor
    if _is_monitor_complete(current_monitor):
        monitors.append(_create_monitor(current_monitor))

    # Sort by stable ID for consistent ordering
    monitors.sort(key=lambda m: m.stable_id)

    # Handle duplicate stable IDs by appending bus number
    seen_ids = {}
    for monitor in monitors:
        if monitor.stable_id in seen_ids:
            # Append bus number to make unique
            bus_num = monitor.i2c_bus.split('-')[-1]
            monitor.stable_id = f"{monitor.stable_id}-bus{bus_num}"
        seen_ids[monitor.stable_id] = True

    return monitors


def _is_monitor_complete(monitor_dict: Dict) -> bool:
    """Check if monitor dictionary has all required fields."""
    required = ['i2c_bus', 'manufacturer', 'model', 'serial']
    return all(key in monitor_dict for key in required)


def _create_monitor(monitor_dict: Dict) -> Monitor:
    """Create Monitor object from parsed dictionary."""
    return Monitor(
        manufacturer=monitor_dict['manufacturer'],
        model=monitor_dict['model'],
        serial=monitor_dict['serial'],
        i2c_bus=monitor_dict['i2c_bus'],
        stable_id=""  # Will be generated in __post_init__
    )


