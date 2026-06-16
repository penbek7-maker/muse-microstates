# Changelog

## 0.2.1 — All reported issues fixed

Fixes based on external testing and compatibility feedback.

### Fixed

- Fixed NumPy 2.x crash caused by removed `np.trapz`.
- Added compatibility with both NumPy 1.x and 2.x.
- Implemented real `--record` CSV recording mode.
- Implemented real `--duration` option.
- Added real command-line parsing with `argparse`.
- Added `--print` compatibility flag so old README commands still work.
- Added `--no-print` for quiet operation.
- Corrected README instructions for GitHub ZIP folder name: `muse-microstates-main`.
- Clarified that Homebrew LSL installation is optional with current `pylsl`.
- Added `requirements.txt`.
- Added clearer OSC documentation.
- Added explicit non-clinical disclaimer.

## 0.1.0 — Initial version

- Muse 2 EEG input via LSL.
- Welch bandpower analysis.
- Rolling baseline.
- Z-score calculation.
- Rule-based micro mental state detection.
- OSC output to Max/MSP.
