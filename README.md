# Muse Band-Pair Interaction States

## Muse 2 → Python → Max/MSP  
### Real-Time EEG Band Analysis and Dominant Band-Pair Interaction States

This repository contains a lightweight EEG interaction system for Muse 2, Python, Lab Streaming Layer, OSC, and Max/MSP.

It was developed for artistic research, electroacoustic composition, live performance, sound art, and neuro-responsive interaction.

It is **not** intended for medical, diagnostic, therapeutic, or clinical use.

---

## What the System Does

The system reads EEG from a Muse 2 headset and translates baseline-relative
EEG spectral deviations into rule-based interaction states.

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
All-pair comparison and dominant interaction state
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
ACADEMIC_RATIONALE.md  Academic rationale, limitations, and presentation wording
requirements.txt       Python dependencies
CHANGELOG.md           Version history
LICENSE                MIT License
```

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

You should see live band values, z-scores, all six pair scores, and the
detected dominant pair state.

### How the pair comparison works

The script compares all six unordered pairs formed by theta, alpha, beta, and
gamma. Each band is first converted to dB and standardized against its own
rolling baseline. For each pair:

```text
pair_score(A, B) = (z_A + z_B) / 2
```

The pair with the highest score is the candidate state. It becomes active only
when both constituent bands exceed `--z-threshold` and its score is greater
than the score of every other pair. `--pair-margin` can require an additional
lead over the runner-up. This is a descriptive comparison of band-power
deviations, not a connectivity, synchrony, or coupling measure.

The fixed pair order is:

```text
0 alpha_theta
1 beta_gamma
2 beta_alpha
3 alpha_gamma
4 theta_beta
5 theta_gamma
```

Additional OSC messages are:

```text
/analysis_status  initializing | running
/baseline_progress  value from 0.0 to 1.0
/bands_db         alpha, beta, theta, gamma power in decibels
/bands_high       four 0/1 flags in alpha, beta, theta, gamma order
/pair_names       six names in the fixed order above
/pair_scores      six joint-elevation scores
/pair_active      one-hot winning-pair flags, or all zero
/top_pair_index   integer from 0 to 5
/top_pair_name    string
/top_pair_score   float
/top_pair_margin  winning score minus runner-up score
/state            0 for neutral, otherwise 1 to 6
/state_name       neutral or pair_name_high
```

The script uses the median band power of the frontal Muse channels
AF7 and AF8 (indices 1 and 2). Select different channels with, for example,
`--channels 0,1,2,3`. Z-scores are calculated from log-transformed (dB) power.
Recording example:

```bash
python muse_microstates.py --record pair_take01.csv --duration 600
```

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
/state      integer from 0 to 6
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

## Band-Pair Interaction States

These states are **artistic interaction categories**. They should not be understood as clinical EEG states or emotion recognition.

| State | Name | Rule |
|---:|---|---|
| 0 | `neutral` | No specific rule is triggered |
| 1 | `alpha_theta_high` | Alpha–theta has the highest pair score and both bands are high |
| 2 | `beta_gamma_high` | Beta–gamma has the highest pair score and both bands are high |
| 3 | `beta_alpha_high` | Beta–alpha has the highest pair score and both bands are high |
| 4 | `alpha_gamma_high` | Alpha–gamma has the highest pair score and both bands are high |
| 5 | `theta_beta_high` | Theta–beta has the highest pair score and both bands are high |
| 6 | `theta_gamma_high` | Theta–gamma has the highest pair score and both bands are high |

The default high-band threshold is:

```text
z-score > 0.5
```

You can change it:

```bash
python muse_microstates.py --z-threshold 0.7
```

You can also require the winner to lead the second pair by a minimum score:

```bash
python muse_microstates.py --pair-margin 0.1
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
theta, alpha, beta, gamma
db_theta, db_alpha, db_beta, db_gamma
z_theta, z_alpha, z_beta, z_gamma
all six pair scores and one-hot active flags
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
--pair-margin 0.0         Minimum lead over the second-ranked pair
--channels 1,2            Select comma-separated EEG channel indices
--print                   Print values to console
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

It does not claim to read emotions or diagnose mental states. Instead, it
translates changing EEG band-power deviations into higher-level musical
interaction states that can be mapped to compositional processes in Max/MSP.

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
