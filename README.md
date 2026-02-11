# Muse 2 → Python → Max/MSP  
## Real-Time EEG Band Analysis & Rule-Based Micro Mental States

This repository provides a **beginner-friendly, transparent, and performance-oriented EEG system**
using the **Muse 2** headset, **Python**, and **Max/MSP**.

The system is designed for:
- live performance
- sound art
- interactive installations
- artistic and academic research

It is **not intended for medical, diagnostic, or clinical use**.

---

## What This System Does (Plain Language)

1. Reads EEG signals from a Muse 2 headset  
2. Streams them via Lab Streaming Layer (LSL)  
3. Processes them in Python  
4. Extracts brainwave activity (Theta, Alpha, Beta, Gamma)  
5. Detects *micro mental states* using rule-based logic  
6. Sends the results to Max/MSP via OSC  
7. Optionally records data for safe concert playback  

---

## System Architecture

```text
Muse 2 EEG
   ↓
muselsl (LSL stream)
   ↓
Python (band analysis + microstates)
   ↓
OSC messages
   ↓
Max/MSP (sound, mapping, interaction)


1. Install Homebrew (macOS)

Open Terminal and run:

/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"


For Apple Silicon Macs, then run:

echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
source ~/.zprofile


Check installation:

brew --version

2. Install Lab Streaming Layer (LSL)
brew install labstreaminglayer/tap/lsl


Verify:

ls /opt/homebrew/lib | grep lsl

3. Create a Python Virtual Environment
cd ~
python3 -m venv muse2-env
source muse2-env/bin/activate


You should now see:

(muse2-env) yourname ~ %


Upgrade pip:

pip install --upgrade pip

4. Install Python Libraries
pip install muselsl pylsl numpy scipy python-osc

PART 2 — Download the Project Files (Beginner Friendly)

!) The Python script is not installed automatically.
It is simply downloaded and run.

Download

Open this GitHub repository in your browser

Click Code → Download ZIP

Unzip the folder on your computer

You will obtain a folder containing:

README.md (this guide)

muse_microstates.py (the main Python script)

The Main Script

The core of the system is:

muse_microstates.py


This script:

connects to the Muse EEG stream via LSL

computes EEG band power

detects rule-based micro mental states

sends OSC messages to Max/MSP

optionally records data to CSV

PART 3 — Running the System (Every Time)
What You Need

Muse 2 headset (charged and worn correctly)

Max/MSP open

Two Terminal windows

Step 1 — Start EEG Streaming (Terminal 1)
cd ~
source muse2-env/bin/activate
python -m muselsl stream


Wait until you see:

Connected.
Streaming EEG...


Leave this terminal running.

Step 2 — Run Processing Script (Terminal 2)

Navigate to the folder you downloaded (example assumes Downloads):

cd ~/Downloads/muse-microstates
source ~/muse2-env/bin/activate
python muse_microstates.py --print


You should see:

band values

z-scores

detected states

OSC Messages Sent to Max/MSP
/bands      → [alpha, beta, theta, gamma]
/bands_z    → z-scored band values
/state      → integer (0–5)
/state_name → string

Recording Mode (Concert Safety)

To record 10 minutes of data:

python muse_microstates.py --record take01.csv --duration 600


This allows:

rehearsal capture

playback instead of live EEG

safe performance fallback

Notes on Use

This system is artistic and exploratory

It is not a neuroscientific diagnostic tool

Mental states are interaction metaphors, not labels

Credits

Developed by Penelope Bekiari
Year: 2025
