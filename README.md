# Muse Microstates / Hyponoia EEG Engine

## Muse 2 → Python → Max/MSP  
### Real-Time EEG Band Analysis and Rule-Based Micro Mental States

This repository contains a lightweight EEG interaction system for Muse 2, Python, Lab Streaming Layer, OSC, and Max/MSP.

It also includes a device-independent Hyponoia engine. Muse 2 remains supported,
while any EEG system that publishes an LSL stream with `type="EEG"` can use the
same analysis, states, and OSC interface. This includes LiveAmp through the
official BrainVision LSL Connector.

It was developed for artistic research, electroacoustic composition, live performance, sound art, and neuro-responsive interaction.

It is **not** intended for medical, diagnostic, therapeutic, or clinical use.

---

## What the System Does

The system reads EEG from a Muse 2 headset and translates changing EEG band relationships into rule-based interaction states.

The pipeline is:

```text
Muse 2 EEG
↓
muselsl / Lab Streaming Layer
↓
Python
↓
Welch bandpower analysis
↓
Rolling baseline and z-scores
↓
Rule-based micro mental states
↓
OSC messages
↓
Max/MSP
↓
Sound processing / performance mapping
```

The system analyses:

- theta: 4–8 Hz
- alpha: 8–12 Hz
- beta: 13–30 Hz
- gamma: 30–45 Hz

---

## Repository Files

```text
README.md              Project documentation
muse_microstates.py    Main Python script
hyponoia_microstates.py Device-independent EEG engine for Hyponoia
simulate_liveamp.py    Synthetic 32-channel EEG source for hardware-free testing
tests/                  Automated signal and compatibility tests
requirements.txt       Python dependencies
CHANGELOG.md           Version history
LICENSE                MIT License
```

---

## Hyponoia: Any EEG via LSL

The new pipeline is:

```text
Muse / LiveAmp / another EEG / simulator
↓
Lab Streaming Layer (stream type: EEG)
↓
hyponoia_microstates.py
↓
Welch bandpower + rolling baseline + rule-based states
↓
stable OSC messages
↓
Hyponoia / Max/MSP
```

The sampling rate, channel metadata, and amplitude units are read from the LSL
stream. Recognised volts, millivolts, microvolts, and nanovolts are normalised to
microvolts. In automatic mode, Muse keeps the historical AF7 behaviour.
Multi-channel devices use the median bandpower across EEG channels, unless
channels are selected explicitly.

Run with any available EEG stream:

```bash
python hyponoia_microstates.py
```

Choose a specific stream or channels:

```bash
python hyponoia_microstates.py --stream-name LiveAmp --channels Fz,Cz,Pz
```

The existing Hyponoia messages remain unchanged:

```text
/bands
/bands_z
/state
/state_name
```

Additional source metadata is sent once at connection:

```text
/eeg/source
/eeg/profile
/eeg/fs
/eeg/channels
/eeg/channel_names
/eeg/unit
```

### Test without EEG hardware

Start the synthetic 32-channel LiveAmp-like stream:

```bash
python simulate_liveamp.py
```

In another terminal, connect the Hyponoia engine:

```bash
python hyponoia_microstates.py \
  --stream-name Hyponoia-Simulated-LiveAmp-32 \
  --baseline-sec 10
```

When the physical LiveAmp is available, replace the simulator with the official
BrainVision LSL Connector and keep the Hyponoia engine and OSC mapping unchanged.

---

## Installation

### 1. Install Homebrew

Open Terminal and run:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

For Apple Silicon Macs, also run:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
source ~/.zprofile
```

Check that Homebrew is installed:

```bash
brew --version
```

---

### 2. Optional: Install Lab Streaming Layer

Recent versions of `pylsl` usually bundle `liblsl`, so this step is often not required.

If you have LSL issues, install it with Homebrew:

```bash
brew install labstreaminglayer/tap/lsl
```

---

### 3. Create a Python virtual environment

```bash
cd ~
python3 -m venv muse2-env
source muse2-env/bin/activate
pip install --upgrade pip
```

---

### 4. Download or clone the repository

#### Option A: Download ZIP

If you use GitHub's **Code → Download ZIP**, the folder will usually be called:

```text
muse-microstates-main
```

Then run:

```bash
cd ~/Downloads/muse-microstates-main
```

#### Option B: Clone with Git

```bash
git clone https://github.com/penbek7-maker/muse-microstates.git
cd muse-microstates
```

---

### 5. Install Python dependencies

From inside the project folder:

```bash
pip install -r requirements.txt
```

If you prefer to install manually:

```bash
pip install muselsl pylsl numpy scipy python-osc
```

---

## Running the System

You need two Terminal windows.

---

### Terminal 1 — Start the Muse 2 EEG stream

```bash
source ~/muse2-env/bin/activate
python -m muselsl stream
```

Wait until the terminal shows that Muse is connected and streaming EEG.

Leave this terminal open.

---

### Terminal 2 — Run the analysis script

Go to the repository folder:

```bash
cd ~/Downloads/muse-microstates-main
source ~/muse2-env/bin/activate
python muse_microstates.py
```

Or, if you cloned the repo:

```bash
cd muse-microstates
source ~/muse2-env/bin/activate
python muse_microstates.py
```

You should see live band values, z-scores, and detected states.

---

## OSC Output

By default, the script sends OSC to:

```text
IP:   127.0.0.1
Port: 5001
```

The following OSC messages are sent:

```text
/bands      [alpha, beta, theta, gamma]
/bands_z    [z_alpha, z_beta, z_theta, z_gamma]
/state      integer from 0 to 5
/state_name string
```

Example Max/MSP route:

```text
udpreceive 5001
↓
oscparse
↓
route bands bands_z state state_name
```

You can change the OSC destination:

```bash
python muse_microstates.py --osc-ip 127.0.0.1 --osc-port 5001
```

---

## Micro Mental States

These states are **artistic interaction categories**. They should not be understood as clinical EEG states or emotion recognition.

| State | Name | Rule |
|---:|---|---|
| 0 | `neutral` | No specific rule is triggered |
| 1 | `alpha_theta` | Alpha and theta are high; beta and gamma are not high |
| 2 | `beta_gamma` | Beta and gamma are high; alpha and theta are not high |
| 3 | `beta_alpha` | Beta and alpha are high; theta and gamma are not high |
| 4 | `alpha_gamma` | Alpha and gamma are high; beta and theta are not high |
| 5 | `theta_dominant` | Theta is above threshold and higher than alpha, beta, and gamma |

The default high-band threshold is:

```text
z-score > 0.5
```

You can change it:

```bash
python muse_microstates.py --z-threshold 0.7
```

---

## Recording Mode

The script can record processed analysis values to CSV.

Example: record 10 minutes of processed data.

```bash
python muse_microstates.py --record take01.csv --duration 600
```

The CSV contains:

```text
timestamp
alpha, beta, theta, gamma
z_alpha, z_beta, z_theta, z_gamma
state, state_name
```

Important: this records processed bandpower, z-score, and state values. It does **not** record raw EEG.

Recording mode can be useful for:

- rehearsal documentation
- performance testing
- later inspection of state changes
- fallback analysis
- comparison between takes or performers

---

## Command-Line Options

See all options:

```bash
python muse_microstates.py --help
```

Common options:

```bash
--record take01.csv       Record processed values to CSV
--duration 600            Stop after 600 seconds
--osc-ip 127.0.0.1        Set OSC target IP
--osc-port 5001           Set OSC target port
--z-threshold 0.5         Set z-score threshold
--channel 1               Select EEG channel index
--print                   Print values to console; kept for old README compatibility
--no-print                Disable console output
```

---

## Compatibility Notes

### NumPy

This version supports both NumPy 1.x and NumPy 2.x.

Older versions used:

```python
np.trapz(...)
```

This caused crashes on current NumPy 2.x installations. The current version uses a compatibility shim:

```python
_TRAPEZOID = getattr(np, "trapezoid", None) or np.trapz
```

This allows the script to work with both older and newer NumPy versions.

### Lab Streaming Layer

Recent `pylsl` versions bundle `liblsl`. Therefore, Homebrew LSL installation is optional unless your system specifically needs it.

---

## Artistic and Research Framing

This project should be understood as a neuro-responsive performance framework.

It does not claim to read emotions or diagnose mental states. Instead, it translates changing EEG band relationships into higher-level musical interaction states that can be mapped to compositional processes in Max/MSP.

In performance, these states may be used to trigger or influence:

- spectral processing
- density changes
- spatialisation
- looping
- freezing
- delay structures
- soundscape behaviour
- process selection

The purpose is not direct biological control, but a performative dialogue between brain activity, computational interpretation, and electroacoustic sound.

---

## Credits

Developed by **Penelope Bekiari**.

External testing and compatibility feedback: **Matthew Rogerson**.

2026.
