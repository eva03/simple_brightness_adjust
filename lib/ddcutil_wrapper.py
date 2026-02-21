#!/usr/bin/env python3
"""
ddcutil command wrapper with caching for performance.

Caches the full sorted list of detected monitors to avoid running
ddcutil detect on every keypress.
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path


# VCP code for brightness control
VCP_BRIGHTNESS = 0x10

# Cache file location
CACHE_FILE = Path(f"/tmp/brightness-control-{os.getenv('USER', 'unknown')}-bus-cache.json")


class MonitorCache:
    """Caches the sorted list of detected monitors with a TTL."""

    def __init__(self, cache_duration: int = 60):
        self.cache_duration = cache_duration

    def get(self):
        """
        Return cached monitor list, or None if stale or missing.

        Returns:
            List of Monitor objects in sorted order, or None.
        """
        try:
            if not CACHE_FILE.exists():
                return None

            with open(CACHE_FILE) as f:
                data = json.load(f)

            if time.time() - data.get('timestamp', 0) > self.cache_duration:
                return None

            # Import here to avoid circular dependency
            from monitor_detector import Monitor
            return [
                Monitor(
                    manufacturer=m['manufacturer'],
                    model=m['model'],
                    serial=m['serial'],
                    i2c_bus=m['i2c_bus'],
                    stable_id=m['stable_id'],
                )
                for m in data['monitors']
            ]

        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def set(self, monitors) -> None:
        """Cache the sorted monitor list."""
        try:
            data = {
                'timestamp': time.time(),
                'monitors': [
                    {
                        'stable_id': m.stable_id,
                        'manufacturer': m.manufacturer,
                        'model': m.model,
                        'serial': m.serial,
                        'i2c_bus': m.i2c_bus,
                    }
                    for m in monitors
                ],
            }
            with open(CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)

        except OSError as e:
            print(f"Warning: Failed to write cache: {e}")

    def invalidate(self) -> None:
        """Delete the cache file."""
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
        except OSError:
            pass


def get_brightness(i2c_bus: str, max_retries: int = 3) -> int:
    """
    Get current brightness level for a monitor.

    Args:
        i2c_bus: I2C bus path (e.g., "/dev/i2c-4").
        max_retries: Number of retry attempts for transient failures.

    Returns:
        Current brightness value (0-100).

    Raises:
        RuntimeError: If ddcutil command fails after retries.
        PermissionError: If user lacks I2C device permissions.
    """
    bus_num = _extract_bus_number(i2c_bus)

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['ddcutil', '--bus', bus_num, 'getvcp', hex(VCP_BRIGHTNESS)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()

                if 'permission denied' in stderr or 'errno 13' in stderr:
                    raise PermissionError(
                        f"Permission denied accessing {i2c_bus}. "
                        f"Add user to i2c group: sudo usermod -aG i2c {os.getenv('USER')}\n"
                        f"Then log out and log back in."
                    )

                if 'invalid' in stderr or 'unsupported' in stderr:
                    raise RuntimeError(
                        f"Monitor on {i2c_bus} does not support DDC/CI brightness control "
                        f"(VCP {hex(VCP_BRIGHTNESS)})"
                    )

                if attempt < max_retries - 1:
                    time.sleep(0.1)
                    continue

                raise RuntimeError(f"ddcutil getvcp failed: {result.stderr.strip()}")

            match = re.search(r'current value\s*=\s*(\d+)', result.stdout)
            if match:
                return int(match.group(1))

            raise RuntimeError(f"Failed to parse brightness from: {result.stdout.strip()}")

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                continue
            raise RuntimeError(f"ddcutil getvcp timed out on {i2c_bus}")

        except FileNotFoundError:
            raise RuntimeError("ddcutil not found. Install with: sudo apt install ddcutil")

    raise RuntimeError("Failed to get brightness after retries")


def set_brightness(i2c_bus: str, value: int, max_retries: int = 3) -> None:
    """
    Set brightness level for a monitor.

    Args:
        i2c_bus: I2C bus path (e.g., "/dev/i2c-4").
        value: Target brightness value (0-100).
        max_retries: Number of retry attempts for transient failures.

    Raises:
        ValueError: If value is out of range.
        RuntimeError: If ddcutil command fails after retries.
        PermissionError: If user lacks I2C device permissions.
    """
    if not 0 <= value <= 100:
        raise ValueError(f"Brightness value must be 0-100, got {value}")

    bus_num = _extract_bus_number(i2c_bus)

    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['ddcutil', '--bus', bus_num, 'setvcp', hex(VCP_BRIGHTNESS), str(value)],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                stderr = result.stderr.lower()

                if 'permission denied' in stderr or 'errno 13' in stderr:
                    raise PermissionError(
                        f"Permission denied accessing {i2c_bus}. "
                        f"Add user to i2c group: sudo usermod -aG i2c {os.getenv('USER')}\n"
                        f"Then log out and log back in."
                    )

                if attempt < max_retries - 1:
                    time.sleep(0.1)
                    continue

                raise RuntimeError(f"ddcutil setvcp failed: {result.stderr.strip()}")

            return

        except subprocess.TimeoutExpired:
            if attempt < max_retries - 1:
                continue
            raise RuntimeError(f"ddcutil setvcp timed out on {i2c_bus}")

        except FileNotFoundError:
            raise RuntimeError("ddcutil not found. Install with: sudo apt install ddcutil")

    raise RuntimeError("Failed to set brightness after retries")


def _extract_bus_number(i2c_bus: str) -> str:
    """Extract numeric bus number from an I2C bus path like '/dev/i2c-4'."""
    match = re.search(r'i2c-(\d+)', i2c_bus)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid I2C bus format: {i2c_bus}")
