"""MicroPython script to calibrate the Gravity EC sensor on a Raspberry Pi Pico W.

Run this file from Thonny while the Pico W is connected.  The script will ask you to
place the probe into each calibration buffer and will compute the linear conversion
parameters required by :mod:`ec_monitor`.

The resulting parameters are written to ``ec_config.json`` in the Pico's filesystem so
that both this project and the separate ``pH-Calibration`` project can read them without
stepping on each other's files.
"""
from __future__ import annotations

import sys
import time

try:
    import machine
    import ujson as json
except ImportError as exc:  # pragma: no cover - MicroPython specific
    raise SystemExit("This script must run on MicroPython with machine and ujson modules") from exc

# ----- User adjustable settings -----------------------------------------------------------
ADC_PIN = 26  # GP26 on the Pico W.  Change if your EC sensor is wired to a different pin.
VREF = 3.3    # Pico ADC reference voltage in volts.
SAMPLES = 200
SAMPLE_DELAY_MS = 10
CONFIG_PATH = "ec_config.json"

# Conductivity values of the calibration buffers provided with the Gravity EC kit.
LOW_POINT_US_CM = 1413.0           # µS/cm
HIGH_POINT_US_CM = 12_880.0        # µS/cm (12.88 mS/cm)


class _ADCReader:
    """Helper that lazily instantiates the ADC only when running on-device."""

    def __init__(self, pin: int) -> None:
        self._pin = pin
        self._adc = None

    @property
    def adc(self) -> "machine.ADC":
        if self._adc is None:
            self._adc = machine.ADC(self._pin)
        return self._adc

    def read_average(self, samples: int, delay_ms: int) -> float:
        total = 0
        for _ in range(samples):
            total += self.adc.read_u16()
            time.sleep_ms(delay_ms)
        return total / float(samples)


def _prompt(message: str) -> None:
    print("\n" + message)
    try:
        input("Press ENTER when ready...")
    except EOFError:
        # When Thonny sends the script without an attached stdin the input() call raises.
        # Falling back to a short delay still gives time to position the probe.
        print("stdin not available; waiting 5 seconds instead of input().")
        time.sleep(5)


def _compute_calibration(raw_low: float, raw_high: float) -> tuple[float, float]:
    if raw_high == raw_low:
        raise ValueError("Calibration readings are identical; check the probe wiring.")

    slope = (HIGH_POINT_US_CM - LOW_POINT_US_CM) / (raw_high - raw_low)
    intercept = LOW_POINT_US_CM - slope * raw_low
    return slope, intercept


def main() -> int:
    print("Gravity EC sensor calibration")
    print("================================")
    print("This routine records ADC readings in two buffer solutions:")
    print("  • 1413 µS/cm standard")
    print("  • 12.88 mS/cm standard")
    print()
    print(
        "Make sure the probe is rinsed and gently dried between buffers.\n"
        "Temperature compensation is not applied during calibration; conduct the test\n"
        "close to 25 °C for best accuracy."
    )

    reader = _ADCReader(ADC_PIN)

    _prompt(
        "Place the probe in the 1413 µS/cm buffer solution. Ensure the sensor is still \"
        "and wait for the reading to stabilise."
    )
    raw_low = reader.read_average(SAMPLES, SAMPLE_DELAY_MS)
    print(f"Raw ADC average (low buffer): {raw_low:.2f}")

    _prompt(
        "Rinse the probe, dry it carefully, then place it in the 12.88 mS/cm buffer."
    )
    raw_high = reader.read_average(SAMPLES, SAMPLE_DELAY_MS)
    print(f"Raw ADC average (high buffer): {raw_high:.2f}")

    slope, intercept = _compute_calibration(raw_low, raw_high)

    config = {
        "version": 1,
        "adc_pin": ADC_PIN,
        "vref": VREF,
        "samples": SAMPLES,
        "sample_delay_ms": SAMPLE_DELAY_MS,
        "raw_low": raw_low,
        "raw_high": raw_high,
        "low_point_us_cm": LOW_POINT_US_CM,
        "high_point_us_cm": HIGH_POINT_US_CM,
        "slope": slope,
        "intercept": intercept,
    }

    with open(CONFIG_PATH, "w") as fh:
        json.dump(config, fh)

    print("\nCalibration complete!")
    print(f"Slope:     {slope:.8f} µS/cm per ADC count")
    print(f"Intercept: {intercept:.2f} µS/cm")
    print(f"Configuration saved to '{CONFIG_PATH}'.")
    print(
        "Use these parameters with ec_monitor.py to convert ADC readings into conductivity."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
