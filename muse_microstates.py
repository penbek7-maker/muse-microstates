#!/usr/bin/env python3
"""
muse_microstates.py

Muse 2 -> Python -> Max/MSP
Real-time comparison of every unordered pair formed by theta, alpha, beta,
and gamma band-power deviations. The winning pair becomes an interaction
state only when both of its bands are elevated relative to baseline.

The output is intended for artistic research and interactive performance.
It does not infer emotions, diagnoses, or validated psychological states.
"""

import argparse
import csv
import time
from collections import deque
from pathlib import Path

import numpy as np
from pylsl import StreamInlet, resolve_byprop
from pythonosc import udp_client
from scipy.signal import welch


DEFAULT_FS = 256
DEFAULT_WIN_SEC = 2.0
DEFAULT_BASELINE_SEC = 60.0
DEFAULT_Z_THRESHOLD = 0.5
DEFAULT_PAIR_MARGIN = 0.0
DEFAULT_OSC_IP = "127.0.0.1"
DEFAULT_OSC_PORT = 5001
# Muse 2 / muselsl usually exposes 1=AF7 and 2=AF8. The frontal pair is the
# default because temporal dry-electrode channels can be less reliable.
DEFAULT_CHANNELS = "1,2"

BANDS = {
    "theta": (4, 8),
    "alpha": (8, 12),
    "beta": (13, 30),
    "gamma": (30, 45),
}

# Fixed order for OSC lists, CSV columns, and pair indices. The first four
# names preserve the original script's terminology; the last two complete
# the set of six possible unordered pairs.
BAND_ORDER = tuple(BANDS)
OSC_BAND_ORDER = ("alpha", "beta", "theta", "gamma")
PAIR_ORDER = (
    ("alpha", "theta"),
    ("beta", "gamma"),
    ("beta", "alpha"),
    ("alpha", "gamma"),
    ("theta", "beta"),
    ("theta", "gamma"),
)
PAIR_NAMES = tuple(f"{left}_{right}" for left, right in PAIR_ORDER)

_TRAPEZOID = getattr(np, "trapezoid", None) or np.trapz


def bandpower(signal, fs, band):
    """Return absolute band power estimated with Welch's method."""
    fmin, fmax = band
    freqs, psd = welch(signal, fs=fs, nperseg=min(len(signal), fs * 2))
    selected = np.logical_and(freqs >= fmin, freqs <= fmax)
    return float(_TRAPEZOID(psd[selected], freqs[selected]))


def z_score(value, history):
    """Standardize a current value against previous baseline windows."""
    mean = float(np.mean(history))
    std = float(np.std(history))
    if std <= 1e-9:
        return 0.0
    return float((value - mean) / std)


def power_to_db(value):
    """Convert strictly positive band power to decibels."""
    return float(10.0 * np.log10(max(value, np.finfo(float).tiny)))


def calculate_pair_scores(z_values):
    """
    Score every pair using the mean of its two band z-scores.

    Z-scores put the bands on a shared deviation-from-baseline scale, so their
    mean is a transparent combined-elevation score. This is descriptive and
    is not a connectivity, synchrony, or cross-frequency-coupling metric.
    """
    return {
        pair_name: (z_values[left] + z_values[right]) / 2.0
        for pair_name, (left, right) in zip(PAIR_NAMES, PAIR_ORDER)
    }


def rank_pairs(pair_scores):
    """Return pair names from highest to lowest joint-elevation score."""
    return sorted(PAIR_NAMES, key=lambda name: pair_scores[name], reverse=True)


def select_dominant_pair(pair_scores, z_values, z_threshold, pair_margin):
    """
    Select the pair that is more elevated than all five alternatives.

    The winner is active only when both constituent bands exceed the z-score
    threshold and its score exceeds the runner-up by more than pair_margin.
    State 0 is neutral; pair states use stable one-based indices 1..6.
    """
    ranking = rank_pairs(pair_scores)
    top_pair = ranking[0]
    runner_up = ranking[1]
    top_score = pair_scores[top_pair]
    margin = top_score - pair_scores[runner_up]
    left, right = PAIR_ORDER[PAIR_NAMES.index(top_pair)]

    both_high = z_values[left] > z_threshold and z_values[right] > z_threshold
    clearly_first = margin > pair_margin
    if not (both_high and clearly_first):
        return 0, "neutral", ranking

    return PAIR_NAMES.index(top_pair) + 1, f"{top_pair}_high", ranking


def parse_channels(raw_channels, channel_count):
    """Parse and validate a comma-separated channel list."""
    try:
        channels = tuple(dict.fromkeys(int(item.strip()) for item in raw_channels.split(",")))
    except ValueError as exc:
        raise ValueError(
            "--channels must be comma-separated integers, for example 0,1,2,3"
        ) from exc

    if not channels:
        raise ValueError("--channels must contain at least one channel index")

    invalid = [index for index in channels if index < 0 or index >= channel_count]
    if invalid:
        raise ValueError(
            f"Invalid channel index/indices {invalid}; EEG stream has {channel_count} channels"
        )

    return channels


def aggregate_bandpowers(window, channels, fs):
    """Compute each band per selected channel, then take the channel median."""
    powers = {}
    for band_name, band_range in BANDS.items():
        channel_powers = [
            bandpower(window[:, channel], fs, band_range)
            for channel in channels
        ]
        powers[band_name] = float(np.median(channel_powers))
    return powers


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Muse 2 analysis that scores all six theta/alpha/beta/gamma pairs "
            "without assigning psychological state labels."
        )
    )
    parser.add_argument("--osc-ip", default=DEFAULT_OSC_IP)
    parser.add_argument("--osc-port", type=int, default=DEFAULT_OSC_PORT)
    parser.add_argument("--fs", type=int, default=DEFAULT_FS)
    parser.add_argument("--win-sec", type=float, default=DEFAULT_WIN_SEC)
    parser.add_argument("--baseline-sec", type=float, default=DEFAULT_BASELINE_SEC)
    parser.add_argument(
        "--z-threshold",
        type=float,
        default=DEFAULT_Z_THRESHOLD,
        help="A pair is active only when both band z-scores exceed this value.",
    )
    parser.add_argument(
        "--pair-margin",
        type=float,
        default=DEFAULT_PAIR_MARGIN,
        help="Minimum winning pair-score lead over the runner-up.",
    )
    parser.add_argument(
        "--channels",
        default=DEFAULT_CHANNELS,
        help="Comma-separated EEG channel indices. Default: 1,2 (AF7,AF8).",
    )
    parser.add_argument("--stream-timeout", type=float, default=10.0)
    parser.add_argument("--record", type=str, default=None)
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument(
        "--print",
        dest="print_output",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--no-print",
        dest="print_output",
        action="store_false",
    )
    return parser


def open_csv_writer(record_path):
    path = Path(record_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(handle)
    writer.writerow(
        ["timestamp"]
        + list(BAND_ORDER)
        + [f"db_{name}" for name in BAND_ORDER]
        + [f"z_{name}" for name in BAND_ORDER]
        + [f"pair_{name}" for name in PAIR_NAMES]
        + [f"active_{name}" for name in PAIR_NAMES]
        + [
            "state",
            "state_name",
            "top_pair_index",
            "top_pair_name",
            "top_pair_score",
            "top_pair_margin",
        ]
    )
    return handle, writer


def send_initializing(client, powers, db_powers, completed, required):
    client.send_message("/analysis_status", "initializing")
    client.send_message("/baseline_progress", completed / required)
    client.send_message("/bands", [powers[name] for name in OSC_BAND_ORDER])
    client.send_message("/bands_db", [db_powers[name] for name in OSC_BAND_ORDER])
    client.send_message("/state", 0)
    client.send_message("/state_name", "initializing")


def send_analysis(
    client,
    powers,
    db_powers,
    z_values,
    high_flags,
    pair_scores,
    active_mask,
    state_index,
    state_name,
    ranking,
):
    top_pair = ranking[0]
    top_index = PAIR_NAMES.index(top_pair)
    client.send_message("/analysis_status", "running")
    client.send_message("/bands", [powers[name] for name in OSC_BAND_ORDER])
    client.send_message("/bands_db", [db_powers[name] for name in OSC_BAND_ORDER])
    client.send_message("/bands_z", [z_values[name] for name in OSC_BAND_ORDER])
    client.send_message("/bands_high", [int(high_flags[name]) for name in OSC_BAND_ORDER])
    client.send_message("/pair_names", list(PAIR_NAMES))
    client.send_message("/pair_scores", [pair_scores[name] for name in PAIR_NAMES])
    client.send_message("/pair_active", [int(active_mask[name]) for name in PAIR_NAMES])
    client.send_message("/state", state_index)
    client.send_message("/state_name", state_name)
    client.send_message("/top_pair_index", top_index)
    client.send_message("/top_pair_name", top_pair)
    client.send_message("/top_pair_score", pair_scores[top_pair])
    client.send_message(
        "/top_pair_margin",
        pair_scores[top_pair] - pair_scores[ranking[1]],
    )


def main():
    args = build_arg_parser().parse_args()

    if args.fs <= 0 or args.win_sec <= 0 or args.baseline_sec <= 0:
        raise SystemExit("--fs, --win-sec, and --baseline-sec must be positive")
    if args.pair_margin < 0:
        raise SystemExit("--pair-margin must be zero or positive")

    window_samples = int(args.fs * args.win_sec)
    if window_samples < 2:
        raise SystemExit("Analysis window is too short for the selected sampling rate")

    baseline_windows = max(5, int(np.ceil(args.baseline_sec / args.win_sec)))

    print("Resolving Muse EEG stream (type='EEG')...")
    streams = resolve_byprop("type", "EEG", timeout=args.stream_timeout)
    if not streams:
        print("No EEG stream found. Is muselsl stream running?")
        return

    inlet = StreamInlet(streams[0])
    info = inlet.info()
    try:
        channels = parse_channels(args.channels, info.channel_count())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Connected to {info.name()} with {info.channel_count()} channels")
    print(f"Using channels: {','.join(map(str, channels))}")
    print(f"Pair order: {', '.join(PAIR_NAMES)}")

    client = udp_client.SimpleUDPClient(args.osc_ip, args.osc_port)
    print(f"Sending OSC to {args.osc_ip}:{args.osc_port}")

    csv_handle = None
    csv_writer = None
    if args.record:
        csv_handle, csv_writer = open_csv_writer(args.record)
        print(f"Recording processed values to: {args.record}")

    sample_buffer = []
    start_time = time.time()
    history = {
        band_name: deque(maxlen=baseline_windows)
        for band_name in BAND_ORDER
    }

    try:
        while True:
            if args.duration is not None and time.time() - start_time >= args.duration:
                print("Duration reached. Stopping.")
                break

            sample, _ = inlet.pull_sample()
            if sample is None:
                continue
            sample_buffer.append(sample)
            if len(sample_buffer) < window_samples:
                continue

            window = np.asarray(sample_buffer[:window_samples], dtype=float)
            sample_buffer = sample_buffer[window_samples:]
            powers = aggregate_bandpowers(window, channels, args.fs)
            db_powers = {name: power_to_db(powers[name]) for name in BAND_ORDER}

            # Build the initial baseline before scoring. Later z-scores are
            # calculated against previous windows, never against themselves.
            if len(history[BAND_ORDER[0]]) < baseline_windows:
                for band_name in BAND_ORDER:
                    history[band_name].append(db_powers[band_name])
                completed = len(history[BAND_ORDER[0]])
                send_initializing(client, powers, db_powers, completed, baseline_windows)
                if args.print_output:
                    print(f"Collecting baseline: {completed}/{baseline_windows}")
                continue

            z_values = {
                band_name: z_score(db_powers[band_name], history[band_name])
                for band_name in BAND_ORDER
            }
            high_flags = {
                band_name: z_values[band_name] > args.z_threshold
                for band_name in BAND_ORDER
            }
            pair_scores = calculate_pair_scores(z_values)
            state_index, state_name, ranking = select_dominant_pair(
                pair_scores,
                z_values,
                args.z_threshold,
                args.pair_margin,
            )
            active_mask = {
                name: state_name == f"{name}_high"
                for name in PAIR_NAMES
            }
            top_pair = ranking[0]
            top_pair_index = PAIR_NAMES.index(top_pair)
            top_pair_margin = pair_scores[top_pair] - pair_scores[ranking[1]]

            send_analysis(
                client,
                powers,
                db_powers,
                z_values,
                high_flags,
                pair_scores,
                active_mask,
                state_index,
                state_name,
                ranking,
            )

            if csv_writer:
                csv_writer.writerow(
                    [time.time()]
                    + [powers[name] for name in BAND_ORDER]
                    + [db_powers[name] for name in BAND_ORDER]
                    + [z_values[name] for name in BAND_ORDER]
                    + [pair_scores[name] for name in PAIR_NAMES]
                    + [int(active_mask[name]) for name in PAIR_NAMES]
                    + [
                        state_index,
                        state_name,
                        top_pair_index,
                        top_pair,
                        pair_scores[top_pair],
                        top_pair_margin,
                    ]
                )
                csv_handle.flush()

            if args.print_output:
                print(
                    "Z: "
                    + ", ".join(f"{name}={z_values[name]:.2f}" for name in BAND_ORDER)
                    + f" | top={top_pair} ({pair_scores[top_pair]:.2f})"
                    + f" | margin={top_pair_margin:.2f}"
                    + f" | state={state_index} ({state_name})"
                )

            for band_name in BAND_ORDER:
                history[band_name].append(db_powers[band_name])

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if csv_handle:
            csv_handle.close()
            print(f"Saved recording to: {args.record}")


if __name__ == "__main__":
    main()
