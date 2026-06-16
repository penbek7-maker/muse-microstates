#!/usr/bin/env python3
"""
muse_microstates.py

Muse 2 -> Python -> Max/MSP
Real-time EEG band analysis and rule-based micro mental states.

This script is intended for artistic research, electroacoustic composition,
live performance, sound art, and neuro-responsive interaction.

It is NOT intended for medical, diagnostic, therapeutic, or clinical use.
"""

import argparse
import csv
import time
from collections import deque
from pathlib import Path

import numpy as np
from scipy.signal import welch
from pylsl import StreamInlet, resolve_byprop
from pythonosc import udp_client


# ---------------- DEFAULT PARAMETERS ----------------

DEFAULT_FS = 256
DEFAULT_WIN_SEC = 2
DEFAULT_BASELINE_SEC = 60
DEFAULT_Z_THRESHOLD = 0.5

DEFAULT_OSC_IP = "127.0.0.1"
DEFAULT_OSC_PORT = 5001

# Muse 2 via muselsl usually exposes:
# 0 = TP9, 1 = AF7, 2 = AF8, 3 = TP10, 4 = AUX
DEFAULT_CHANNEL_INDEX = 1

BANDS = {
    "theta": (4, 8),
    "alpha": (8, 12),
    "beta": (13, 30),
    "gamma": (30, 45),
}

# Compatibility with both NumPy 1.x and 2.x.
# NumPy 2.x uses np.trapezoid; NumPy 1.x used np.trapz.
_TRAPEZOID = getattr(np, "trapezoid", None) or np.trapz


# ---------------- STATE LOGIC ----------------

def detect_state(high_flags, z_vals, z_threshold):
    """
    Detect rule-based micro mental states from EEG band relationships.

    These are artistic interaction states, not clinical or psychological diagnoses.
    """
    alpha = high_flags["alpha"]
    beta = high_flags["beta"]
    theta = high_flags["theta"]
    gamma = high_flags["gamma"]

    z_alpha = z_vals["alpha"]
    z_beta = z_vals["beta"]
    z_theta = z_vals["theta"]
    z_gamma = z_vals["gamma"]

    # State 5: theta is above threshold and higher than all other bands.
    theta_dominant = (
        z_theta > z_threshold
        and z_theta > z_alpha
        and z_theta > z_beta
        and z_theta > z_gamma
    )
    if theta_dominant:
        return 5, "theta_dominant"

    # State 1: Alpha + Theta high.
    if alpha and theta and not (beta or gamma):
        return 1, "alpha_theta"

    # State 2: Beta + Gamma high.
    if beta and gamma and not (alpha or theta):
        return 2, "beta_gamma"

    # State 3: Beta + Alpha high.
    if beta and alpha and not (theta or gamma):
        return 3, "beta_alpha"

    # State 4: Alpha + Gamma high.
    if alpha and gamma and not (beta or theta):
        return 4, "alpha_gamma"

    return 0, "neutral"


def bandpower(signal, fs, band):
    """Calculate absolute bandpower using Welch's method."""
    fmin, fmax = band
    freqs, psd = welch(signal, fs=fs, nperseg=min(len(signal), fs * 2))
    idx = np.logical_and(freqs >= fmin, freqs <= fmax)
    return float(_TRAPEZOID(psd[idx], freqs[idx]))


def z_score(value, history):
    """Calculate z-score against a rolling baseline history."""
    mean = np.mean(history)
    std = np.std(history)
    if std <= 1e-9:
        std = 1.0
    return float((value - mean) / std)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Muse 2 EEG band analysis and rule-based micro mental states for Max/MSP."
    )

    parser.add_argument("--osc-ip", default=DEFAULT_OSC_IP, help="OSC target IP address.")
    parser.add_argument("--osc-port", type=int, default=DEFAULT_OSC_PORT, help="OSC target port.")

    parser.add_argument("--fs", type=int, default=DEFAULT_FS, help="Sampling rate. Muse 2 is usually 256 Hz.")
    parser.add_argument("--win-sec", type=float, default=DEFAULT_WIN_SEC, help="Analysis window length in seconds.")
    parser.add_argument("--baseline-sec", type=float, default=DEFAULT_BASELINE_SEC, help="Rolling baseline length in seconds.")
    parser.add_argument("--z-threshold", type=float, default=DEFAULT_Z_THRESHOLD, help="Z-score threshold for high band activity.")
    parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL_INDEX, help="EEG channel index. Default 1 is usually AF7.")
    parser.add_argument("--stream-timeout", type=float, default=10.0, help="Seconds to wait for an EEG LSL stream.")

    parser.add_argument(
        "--record",
        type=str,
        default=None,
        help="CSV output path. Records processed band/z-score/state values.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional duration in seconds. The script stops after this time.",
    )

    # Backward compatibility with the old README command.
    parser.add_argument(
        "--print",
        dest="print_output",
        action="store_true",
        default=True,
        help="Print live values to console. Kept for compatibility; printing is enabled by default.",
    )
    parser.add_argument(
        "--no-print",
        dest="print_output",
        action="store_false",
        help="Disable live console output.",
    )

    return parser


def open_csv_writer(record_path):
    """Create CSV file and write header row."""
    path = Path(record_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(handle)

    writer.writerow(
        [
            "timestamp",
            "alpha",
            "beta",
            "theta",
            "gamma",
            "z_alpha",
            "z_beta",
            "z_theta",
            "z_gamma",
            "state",
            "state_name",
        ]
    )

    return handle, writer


def send_initializing(client, bp):
    """Send initializing OSC messages while collecting the first baseline windows."""
    client.send_message("/bands", [bp["alpha"], bp["beta"], bp["theta"], bp["gamma"]])
    client.send_message("/state", 0)
    client.send_message("/state_name", "initializing")


def main():
    args = build_arg_parser().parse_args()

    win_samples = int(args.fs * args.win_sec)
    baseline_windows = max(5, int(args.baseline_sec // args.win_sec))

    print("Resolving Muse EEG stream (type='EEG')...")
    streams = resolve_byprop("type", "EEG", timeout=args.stream_timeout)

    if len(streams) == 0:
        print("No EEG stream found. Is muselsl stream running?")
        return

    inlet = StreamInlet(streams[0])
    info = inlet.info()
    stream_name = info.name()
    n_channels = info.channel_count()

    print(f"Connected to stream: {stream_name} with {n_channels} channels")

    if args.channel < 0 or args.channel >= n_channels:
        print(f"Invalid channel index {args.channel}. Stream has {n_channels} channels.")
        return

    client = udp_client.SimpleUDPClient(args.osc_ip, args.osc_port)
    print(f"Sending OSC to {args.osc_ip}:{args.osc_port}")

    csv_handle = None
    csv_writer = None

    if args.record:
        csv_handle, csv_writer = open_csv_writer(args.record)
        print(f"Recording processed values to: {args.record}")

    buffer = []
    start_time = time.time()

    history = {
        "theta": deque(maxlen=baseline_windows),
        "alpha": deque(maxlen=baseline_windows),
        "beta": deque(maxlen=baseline_windows),
        "gamma": deque(maxlen=baseline_windows),
    }

    try:
        while True:
            if args.duration is not None and (time.time() - start_time) >= args.duration:
                print("Duration reached. Stopping.")
                break

            sample, ts = inlet.pull_sample()
            if sample is None:
                continue

            buffer.append(sample)

            if len(buffer) < win_samples:
                continue

            data = np.array(buffer)
            buffer = []

            ch = data[:, args.channel]

            bp = {
                band_name: bandpower(ch, args.fs, band_range)
                for band_name, band_range in BANDS.items()
            }

            for band_name in BANDS:
                history[band_name].append(bp[band_name])

            if len(history["alpha"]) < 5:
                send_initializing(client, bp)

                if args.print_output:
                    print("Collecting baseline...")

                continue

            z_vals = {
                band_name: z_score(bp[band_name], history[band_name])
                for band_name in BANDS
            }

            high_flags = {
                band_name: z_vals[band_name] > args.z_threshold
                for band_name in BANDS
            }

            state_idx, state_name = detect_state(high_flags, z_vals, args.z_threshold)

            # OSC messages to Max/MSP
            client.send_message("/bands", [bp["alpha"], bp["beta"], bp["theta"], bp["gamma"]])
            client.send_message(
                "/bands_z",
                [z_vals["alpha"], z_vals["beta"], z_vals["theta"], z_vals["gamma"]],
            )
            client.send_message("/state", state_idx)
            client.send_message("/state_name", state_name)

            if csv_writer:
                csv_writer.writerow(
                    [
                        time.time(),
                        bp["alpha"],
                        bp["beta"],
                        bp["theta"],
                        bp["gamma"],
                        z_vals["alpha"],
                        z_vals["beta"],
                        z_vals["theta"],
                        z_vals["gamma"],
                        state_idx,
                        state_name,
                    ]
                )
                csv_handle.flush()

            if args.print_output:
                print(
                    f"BP: { {k: round(v, 3) for k, v in bp.items()} } | "
                    f"Z: A={z_vals['alpha']:.2f}, B={z_vals['beta']:.2f}, "
                    f"T={z_vals['theta']:.2f}, G={z_vals['gamma']:.2f} | "
                    f"state={state_idx} ({state_name})"
                )

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        if csv_handle:
            csv_handle.close()
            print(f"Saved recording to: {args.record}")


if __name__ == "__main__":
    main()
