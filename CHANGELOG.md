# Changelog

## 0.3.1 — Restore the working five-state model

- Restored the tested `muse_microstates.py` used in performance.
- Restored states 1–4 as the original exclusive Boolean band-pair rules.
- Restored state 5 as `theta_dominant`.
- Restored AF7 as the single analysis channel.
- Restored the original rolling-bandpower z-score implementation and OSC output.
- Pinned NumPy below version 2 because the restored script uses `np.trapz`.
- Updated the README and academic rationale to match the working script.
- Removed the six-pair model from the active implementation. Version 0.3.0 remains documented below as historical development.

## 0.3.0 — All-pair dominant interaction states

- Replaced four selected Boolean pair rules and `theta_dominant` with a
  comparison of all six possible theta/alpha/beta/gamma pairs.
- Defined each pair score as the mean of its two baseline-relative z-scores.
- A pair state is active only when it ranks first and both bands exceed the
  configured z-score threshold.
- Added an optional minimum winner margin with `--pair-margin`.
- Added pair scores, rankings, high-band flags, and one-hot active-pair OSC
  messages and CSV fields.
- Changed the default analysis from one AF7 channel to the median of AF7 and
  AF8, while retaining configurable channel selection.
- Added dB conversion before rolling-baseline standardization.
- Added academic rationale and terminology limitations.

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
