# EC-Calibration

MicroPython utilities for calibrating and monitoring the Gravity Analog Electrical
Conductivity Sensor (K=1) with a Raspberry Pi Pico W.  The scripts are designed to coexist
with the programs from the separate `pH-Calibration` repository without reusing filenames or
hardware resources.

## Files

- `ec_calibration.py` – interactive calibration helper.  Runs through the 1413 µS/cm and
  12.88 mS/cm buffer solutions and writes the resulting parameters to `ec_config.json`.
- `ec_monitor.py` – continuous conductivity monitor.  Reads `ec_config.json`, measures the
  probe once per hour, and prints the temperature-compensated EC value.

## Usage

1. **Copy the files to the Pico W** using Thonny's file browser (or `mpremote`).
2. **Run `ec_calibration.py`** in Thonny while the probe is in the 1413 µS/cm buffer.  Follow
   the prompts, moving the probe to the 12.88 mS/cm buffer when asked.  When complete, the
   computed slope and intercept are printed and stored in `ec_config.json` on the Pico.
3. **Optional:** review `ec_config.json` to confirm the ADC pin and sampling settings match
   your wiring.  Adjust `ADC_PIN`, `SAMPLES`, or `SAMPLE_DELAY_MS` in either script if your
   hardware setup differs.
4. **Run `ec_monitor.py`** to start hourly logging.  The script uses the Pico's internal
   temperature sensor for compensation when available and prints readings to Thonny's shell.
   Stop the monitor with `Ctrl+C` when required.

The monitor and calibration scripts only use the ADC channel defined in the configuration
and write to `ec_config.json`, ensuring they do not interfere with the pH calibration tools.
