# Muse Microstates

## Muse 2 to Python to Max/MSP

This repository contains the working real-time EEG interaction script used in Penelope Bekiari's artistic research. It receives a Muse 2 EEG stream through Lab Streaming Layer, calculates band power, derives baseline-relative z-scores, selects one of five operational states, and sends the result to Max/MSP through OSC.

The states are musical interaction categories. They are not conventional EEG topographic microstates and do not identify emotions, diagnoses, or validated psychological states.

## Signal flow

```text
Muse 2 EEG
↓
muselsl / Lab Streaming Layer
↓
AF7, channel index 1
↓
2 second windows at 256 Hz
↓
Welch power spectral density
↓
theta, alpha, beta, gamma band power
↓
60 second rolling history
↓
bandwise z-scores and high flags
↓
rule-based states 0 to 5
↓
OSC to Max/MSP
```

The frequency bands are:

- theta: 4–8 Hz
- alpha: 8–12 Hz
- beta: 13–30 Hz
- gamma: 30–45 Hz

## Installation

Create and activate a Python environment:

```bash
cd ~
python3 -m venv muse2-env
source ~/muse2-env/bin/activate
pip install --upgrade pip
```

Clone the repository and install its dependencies:

```bash
git clone https://github.com/penbek7-maker/muse-microstates.git
cd muse-microstates
pip install -r requirements.txt
```

## Running the system

Use two Terminal windows.

In Terminal 1, start the Muse stream:

```bash
source ~/muse2-env/bin/activate
python -m muselsl stream
```

In Terminal 2, run the analysis:

```bash
cd muse-microstates
source ~/muse2-env/bin/activate
python muse_microstates.py
```

The script uses:

```text
Sampling rate:       256 Hz
Window length:       2 seconds
Rolling history:     60 seconds, 30 windows
High-band threshold: z > 0.5
OSC destination:     127.0.0.1:5001
EEG channel:         AF7, channel index 1
```

The first five windows initialise the rolling history. During this period, the script sends state `0` with the name `initializing`.

## Normalisation

For every two-second window, the script calculates absolute band power with Welch's method. It appends the current value to the corresponding rolling history and calculates:

```text
z_band = (current_band_power - history_mean) / history_standard_deviation
```

Each band has its own history. A band becomes high when its z-score exceeds `0.5`.

## Operational states

The script checks `theta_dominant` first. It then checks the four pair rules in numerical order. If no rule passes, it returns `neutral`.

| State | Name | Exact rule |
|---:|---|---|
| 0 | `neutral` | No state rule passes |
| 1 | `alpha_theta` | Alpha and theta are high, while beta and gamma are not high |
| 2 | `beta_gamma` | Beta and gamma are high, while alpha and theta are not high |
| 3 | `beta_alpha` | Beta and alpha are high, while theta and gamma are not high |
| 4 | `alpha_gamma` | Alpha and gamma are high, while beta and theta are not high |
| 5 | `theta_dominant` | Theta exceeds the threshold and has a higher z-score than alpha, beta, and gamma |

The relevant Python conditions are:

```python
if alpha and theta and not (beta or gamma):
    return 1, "alpha_theta"

if beta and gamma and not (alpha or theta):
    return 2, "beta_gamma"

if beta and alpha and not (theta or gamma):
    return 3, "beta_alpha"

if alpha and gamma and not (beta or theta):
    return 4, "alpha_gamma"
```

## OSC output

The script sends:

```text
/bands      [alpha, beta, theta, gamma]
/bands_z    [z_alpha, z_beta, z_theta, z_gamma]
/state      integer from 0 to 5
/state_name string
```

Example Max/MSP routing:

```text
udpreceive 5001
↓
oscparse
↓
route bands bands_z state state_name
```

## Max/MSP mapping

| State | State name | Process | Sonic behaviour |
|---:|---|---|---|
| 0 | Neutral | Baseline, no dominant rhythms | No FX |
| 1 | Alpha–Theta | Resonance with sustained note | Pitch-recognised synth accompaniment |
| 2 | Beta–Gamma | Live granulation | Live granulation |
| 3 | Beta–Alpha | Reverse delay | Reverse delay |
| 4 | Alpha–Gamma | Loop of the previous phrase | Loop of the previous phrase |
| 5 | Theta dominant | High time-stretched downward reverberation | High time-stretched downward reverberation |

## Interpretation limits

The rules describe relationships among baseline-relative band-power values. They do not measure connectivity, synchrony, phase-amplitude coupling, creativity, immersion, or emotion.

Gamma-range scalp EEG can contain activity from facial, jaw, and neck muscles. This limitation is especially relevant during vocal performance. Treat the states as operational controls for musical interaction rather than direct readings of mental content.

## Repository files

```text
muse_microstates.py    Working Python script
README.md              Installation and system documentation
requirements.txt       Python dependencies
CHANGELOG.md           Version history
LICENSE                MIT License
```

## Credits

Developed by Penelope Bekiari.

2026.
