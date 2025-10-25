"""Continuous EC monitoring script for the Raspberry Pi Pico W.

This script reads the calibration settings produced by :mod:`ec_calibration` and publishes
conductivity measurements once an hour.  It is designed to coexist with the programs from
``pH-Calibration`` by keeping its configuration and state within ``ec_config.json`` and by
only touching the ADC pin defined in that file.
"""
from __future__ import annotations

import sys
import time

try:
    import machine
    import ujson as json
except ImportError as exc:  # pragma: no cover - MicroPython specific
    raise SystemExit("This script must run on MicroPython with machine and ujson modules") from exc

CONFIG_PATH = "ec_config.json"
DEFAULT_ADC_PIN = 26
DEFAULT_SAMPLES = 50
DEFAULT_SAMPLE_DELAY_MS = 20
TEMP_COEFFICIENT = 0.019  # Typical temperature compensation per °C for conductivity probes.
REFERENCE_TEMP_C = 25.0


class ECMonitor:
    def __init__(self, config: dict) -> None:
        self.slope = config.get("slope")
        self.intercept = config.get("intercept")
        if self.slope is None or self.intercept is None:
            raise ValueError("Calibration data missing. Run ec_calibration.py first.")

        adc_pin = config.get("adc_pin", DEFAULT_ADC_PIN)
        self.adc = machine.ADC(adc_pin)

        self.samples = int(config.get("samples", DEFAULT_SAMPLES))
        self.sample_delay_ms = int(config.get("sample_delay_ms", DEFAULT_SAMPLE_DELAY_MS))

    def read_raw(self) -> float:
        total = 0
        for _ in range(self.samples):
            total += self.adc.read_u16()
            time.sleep_ms(self.sample_delay_ms)
        return total / float(self.samples)

    def raw_to_us_cm(self, raw_value: float, temperature_c: float | None = None) -> float:
        ec = self.slope * raw_value + self.intercept
        if temperature_c is None:
            return ec

        # Apply linear temperature compensation.
        return ec / (1 + TEMP_COEFFICIENT * (temperature_c - REFERENCE_TEMP_C))


def _load_config(path: str) -> dict:
    try:
        with open(path) as fh:
            return json.load(fh)
    except OSError as exc:
        raise SystemExit(
            "Calibration file not found. Run ec_calibration.py on the Pico before starting "
            "ec_monitor.py"
        ) from exc


def _read_temperature() -> float | None:
    """Read the Pico's internal temperature sensor if available.

    The internal sensor is not very accurate for absolute measurements but is adequate for
    conductivity temperature compensation.  If the board does not expose the sensor this
    function returns ``None`` and the readings are left uncorrected.
    """
    try:
        sensor = machine.ADC(4)
        conversion_factor = 3.3 / 65535
        reading = sensor.read_u16() * conversion_factor
        return 27 - (reading - 0.706) / 0.001721
    except Exception:  # pylint: disable=broad-except
        return None


def main() -> int:
    config = _load_config(CONFIG_PATH)
    monitor = ECMonitor(config)

    print("EC monitor started")
    print("===================")
    print("Press Ctrl+C to stop. A reading will be logged every hour.")

    while True:
        raw = monitor.read_raw()
        temp_c = _read_temperature()
        ec = monitor.raw_to_us_cm(raw, temp_c)

        if temp_c is None:
            print(
                "Raw ADC: {:.2f}, Conductivity: {:.2f} µS/cm (no temperature compensation)".format(
                    raw, ec
                )
            )
        else:
            print(
                "Raw ADC: {:.2f}, Conductivity: {:.2f} µS/cm @ {:.1f} °C".format(
                    raw, ec, temp_c
                )
            )

        # Sleep for one hour (3600 seconds).
        for _ in range(3600):
            time.sleep(1)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
