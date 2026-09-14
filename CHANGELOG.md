# Changelog

## 0.3.1 - Simulator montage clarification

### Changed

- Replaced the provisional simulator labels with a representative published
  LiveAmp-32 montage.
- Made simulator channel labels configurable and explicitly non-authoritative.
- Confirmed that the real engine always reads channel labels from LSL metadata.

## 0.3.0 - Device-independent Hyponoia EEG engine

### Added

- Added `hyponoia_microstates.py` for any regular LSL EEG stream.
- Added automatic sampling-rate and channel-metadata discovery.
- Added automatic amplitude-unit normalisation to microvolts.
- Added explicit stream and channel selection.
- Added Muse, LiveAmp, and generic automatic profiles.
- Preserved the existing OSC contract used by Hyponoia/Max/MSP.
- Added OSC source metadata under `/eeg/*`.
- Added a synthetic 32-channel LiveAmp-like LSL source for hardware-free testing.
- Added automated tests for state rules, channel selection, and bandpower.

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
