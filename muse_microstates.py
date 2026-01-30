import numpy as np
from collections import deque
from scipy.signal import welch
from pylsl import StreamInlet, resolve_byprop
from pythonosc import udp_client

# --------- PARAMS ---------
FS = 256            # Muse 2 sampling rate (τυπικό)
WIN_SEC = 2         # window length in seconds
WIN_SAMPLES = FS * WIN_SEC

BASELINE_SEC = 60   # πόσα δευτερόλεπτα χρησιμοποιούμε για baseline
BASELINE_WINDOWS = BASELINE_SEC // WIN_SEC

Z_THRESHOLD = 0.5   # πόσο πάνω από baseline θεωρούμε "high"

OSC_IP = "127.0.0.1"
OSC_PORT = 5001

# Muse bands
BANDS = {
    "theta": (4, 8),
    "alpha": (8, 12),
    "beta":  (13, 30),
    "gamma": (30, 45),
}


# --------- STATE LOGIC ---------
def detect_state(high_flags, z_vals, z_threshold):
    alpha = high_flags["alpha"]
    beta  = high_flags["beta"]
    theta = high_flags["theta"]
    gamma = high_flags["gamma"]

    z_alpha = z_vals["alpha"]
    z_beta  = z_vals["beta"]
    z_theta = z_vals["theta"]
    z_gamma = z_vals["gamma"]

    # ---- State 5: Theta higher than all ----
    theta_dominant = (
        z_theta > z_threshold and
        z_theta > z_alpha and
        z_theta > z_beta and
        z_theta > z_gamma
    )
    if theta_dominant:
        return 5, "theta_dominant"

    # ---- State 1: Alpha & Theta high ----
    if alpha and theta and not (beta or gamma):
        return 1, "alpha_theta"

    # ---- State 2: Beta & Gamma high ----
    if beta and gamma and not (alpha or theta):
        return 2, "beta_gamma"

    # ---- State 3: Beta & Alpha high ----
    if beta and alpha and not (theta or gamma):
        return 3, "beta_alpha"

    # ---- State 4: Alpha & Gamma high ----
    if alpha and gamma and not (beta or theta):
        return 4, "alpha_gamma"

    # Neutral
    return 0, "neutral"


def bandpower(signal, fs, band):
    """Absolute bandpower μέσω Welch."""
    fmin, fmax = band
    freqs, psd = welch(signal, fs=fs, nperseg=min(len(signal), fs*2))
    idx = np.logical_and(freqs >= fmin, freqs <= fmax)
    return np.trapz(psd[idx], freqs[idx])


def main():
    print("Resolving Muse EEG stream (type='EEG')...")
    streams = resolve_byprop("type", "EEG", timeout=10)

    if len(streams) == 0:
        print("No EEG stream found. Is muselsl stream running?")
        return

    inlet = StreamInlet(streams[0])
    info = inlet.info()
    name = info.name()
    n_channels = info.channel_count()
    print(f"Connected to stream: {name} with {n_channels} channels")

    # OSC client
    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    print(f"Sending OSC to {OSC_IP}:{OSC_PORT}")

    buffer = []

    # ιστορικό bandpowers για baseline
    history_alpha = deque(maxlen=BASELINE_WINDOWS)
    history_beta  = deque(maxlen=BASELINE_WINDOWS)
    history_theta = deque(maxlen=BASELINE_WINDOWS)
    history_gamma = deque(maxlen=BASELINE_WINDOWS)

    while True:
        sample, ts = inlet.pull_sample()
        if sample is None:
            continue

        buffer.append(sample)

        if len(buffer) >= WIN_SAMPLES:
            data = np.array(buffer)
            buffer = []

            # Χρησιμοποιούμε π.χ. κανάλι AF7 (index 1)
            if n_channels < 2:
                print("Not enough channels in EEG stream.")
                continue

            ch = data[:, 1]  # AF7

            # --- Absolute bandpowers ---
            bp = {}
            for band_name, (fmin, fmax) in BANDS.items():
                bp[band_name] = bandpower(ch, FS, (fmin, fmax))

            # --- Ιστορικό για baseline ---
            history_theta.append(bp["theta"])
            history_alpha.append(bp["alpha"])
            history_beta.append(bp["beta"])
            history_gamma.append(bp["gamma"])

            if len(history_alpha) < 5:
                client.send_message("/bands", [
                    float(bp["alpha"]),
                    float(bp["beta"]),
                    float(bp["theta"]),
                    float(bp["gamma"]),
                ])
                client.send_message("/state", 0)
                client.send_message("/state_name", "initializing")
                print("Collecting baseline...")
                continue

            # --- Z-scores ---
            def z_score(val, hist):
                mean = np.mean(hist)
                std = np.std(hist) if np.std(hist) > 1e-9 else 1.0
                return (val - mean) / std

            z_alpha = z_score(bp["alpha"], history_alpha)
            z_beta  = z_score(bp["beta"],  history_beta)
            z_theta = z_score(bp["theta"], history_theta)
            z_gamma = z_score(bp["gamma"], history_gamma)

            z_vals = {
                "alpha": z_alpha,
                "beta":  z_beta,
                "theta": z_theta,
                "gamma": z_gamma,
            }

            # --- Ποια bands είναι "high"; ---
            high_flags = {
                "alpha": z_alpha > Z_THRESHOLD,
                "beta":  z_beta  > Z_THRESHOLD,
                "theta": z_theta > Z_THRESHOLD,
                "gamma": z_gamma > Z_THRESHOLD,
            }

            state_idx, state_name = detect_state(high_flags, z_vals, Z_THRESHOLD)

            # --- OSC προς Max ---
            client.send_message("/bands", [
                float(bp["alpha"]),
                float(bp["beta"]),
                float(bp["theta"]),
                float(bp["gamma"]),
            ])

            client.send_message("/bands_z", [
                float(z_alpha),
                float(z_beta),
                float(z_theta),
                float(z_gamma),
            ])

            client.send_message("/state", state_idx)
            client.send_message("/state_name", state_name)

            print(
                f"BP: { {k: round(v,3) for k,v in bp.items()} } | "
                f"Z: A={z_alpha:.2f}, B={z_beta:.2f}, T={z_theta:.2f}, G={z_gamma:.2f} "
                f"| state={state_idx} ({state_name})"
            )


if __name__ == "__main__":
    main()

