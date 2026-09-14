#!/usr/bin/env python3
"""
Device-independent EEG band analysis and rule-based interaction states.

Any EEG device that publishes a regular Lab Streaming Layer stream with
type="EEG" can feed the same OSC interface used by Hyponoia/Max/MSP.

This software is intended for artistic research and performance. It is not
intended for medical, diagnostic, therapeutic, or clinical use.
"""

import argparse
import csv
import re
import time
from collections import deque
from pathlib import Path

import numpy as np
from scipy.signal import welch
from pythonosc import udp_client


DEFAULT_WIN_SEC = 2.0
DEFAULT_BASELINE_SEC = 60.0
DEFAULT_Z_THRESHOLD = 0.5
DEFAULT_OSC_IP = "127.0.0.1"
DEFAULT_OSC_PORT = 5001

BANDS = {
    "theta": (4, 8),
    "alpha": (8, 12),
    "beta": (13, 30),
    "gamma": (30, 45),
}

_TRAPEZOID = getattr(np, "trapezoid", None) or np.trapz
_NON_EEG_LABEL = re.compile(
    r"(^|[_ -])(acc|accelerometer|aux|marker|status|trigger|event)([_ -]|$)",
    re.IGNORECASE,
)

_UNIT_TO_MICROVOLTS = {
    "v": 1_000_000.0,
    "volt": 1_000_000.0,
    "volts": 1_000_000.0,
    "mv": 1_000.0,
    "millivolt": 1_000.0,
    "millivolts": 1_000.0,
    "uv": 1.0,
    "microvolt": 1.0,
    "microvolts": 1.0,
    "nv": 0.001,
    "nanovolt": 0.001,
    "nanovolts": 0.001,
}


def detect_state(high_flags, z_vals, z_threshold):
    """Return the existing Hyponoia artistic state index and name."""
    alpha = high_flags["alpha"]
    beta = high_flags["beta"]
    theta = high_flags["theta"]
    gamma = high_flags["gamma"]

    z_alpha = z_vals["alpha"]
    z_beta = z_vals["beta"]
    z_theta = z_vals["theta"]
    z_gamma = z_vals["gamma"]

    if (
        z_theta > z_threshold
        and z_theta > z_alpha
        and z_theta > z_beta
        and z_theta > z_gamma
    ):
        return 5, "theta_dominant"
    if alpha and theta and not (beta or gamma):
        return 1, "alpha_theta"
    if beta and gamma and not (alpha or theta):
        return 2, "beta_gamma"
    if beta and alpha and not (theta or gamma):
        return 3, "beta_alpha"
    if alpha and gamma and not (beta or theta):
        return 4, "alpha_gamma"
    return 0, "neutral"


def bandpower(signal, fs, band):
    """Calculate absolute bandpower with Welch's method."""
    fmin, fmax = band
    freqs, psd = welch(signal, fs=fs, nperseg=min(len(signal), int(fs * 2)))
    selected = np.logical_and(freqs >= fmin, freqs <= fmax)
    return float(_TRAPEZOID(psd[selected], freqs[selected]))


def unit_scale_to_microvolts(unit):
    """Return a scale to microvolts, or None for missing/unknown units."""
    normalized = unit.strip().casefold().replace("µ", "u").replace("μ", "u")
    return _UNIT_TO_MICROVOLTS.get(normalized)


def aggregate_bandpowers(
    data, fs, channel_indices, aggregation="median", channel_scales=None
):
    """Calculate bandpower per channel, then combine channels robustly."""
    if data.ndim != 2:
        raise ValueError("EEG window must have shape samples x channels.")
    if not channel_indices:
        raise ValueError("At least one EEG channel must be selected.")

    if channel_scales is None:
        channel_scales = [1.0] * len(channel_indices)
    if len(channel_scales) != len(channel_indices):
        raise ValueError("A unit scale is required for every selected EEG channel.")

    values = {name: [] for name in BANDS}
    for index, scale in zip(channel_indices, channel_scales):
        signal = data[:, index] * scale
        for name, band in BANDS.items():
            values[name].append(bandpower(signal, fs, band))

    if aggregation == "single":
        combine = lambda items: items[0]
    elif aggregation == "mean":
        combine = np.mean
    else:
        combine = np.median
    return {name: float(combine(items)) for name, items in values.items()}


def z_score(value, history):
    """Calculate z-score against a rolling baseline history."""
    mean = np.mean(history)
    std = np.std(history)
    if std <= 1e-9:
        std = 1.0
    return float((value - mean) / std)


def extract_channel_metadata(info):
    """Read labels, channel kinds, and units from LSL XML metadata."""
    count = int(info.channel_count())
    labels = []
    kinds = []
    units = []

    channel = info.desc().child("channels").child("channel")
    for index in range(count):
        if channel.empty():
            labels.append(f"CH{index + 1}")
            kinds.append("")
            units.append("")
        else:
            labels.append(channel.child_value("label") or f"CH{index + 1}")
            kinds.append(channel.child_value("type") or "")
            units.append(channel.child_value("unit") or "")
            channel = channel.next_sibling()
    return labels, kinds, units


def infer_profile(stream_name, labels):
    """Infer a convenience profile without tying processing to one device."""
    name = stream_name.casefold()
    folded = {label.casefold() for label in labels}
    if "muse" in name or {"tp9", "af7", "af8", "tp10"}.issubset(folded):
        return "muse"
    if "liveamp" in name or "brainvision" in name:
        return "liveamp"
    return "generic"


def _is_eeg_channel(label, kind):
    if kind and kind.casefold() not in {"eeg", "exg"}:
        return False
    return not _NON_EEG_LABEL.search(label)


def select_channel_indices(labels, kinds, requested=None, profile="generic"):
    """Select channels by label/index, with safe automatic device defaults."""
    if requested:
        indices = []
        lookup = {label.casefold(): index for index, label in enumerate(labels)}
        for token in (part.strip() for part in requested.split(",")):
            if not token:
                continue
            if token.lstrip("-").isdigit():
                index = int(token)
                if index < 0 or index >= len(labels):
                    raise ValueError(
                        f"Channel index {index} is outside 0..{len(labels) - 1}."
                    )
            else:
                try:
                    index = lookup[token.casefold()]
                except KeyError as error:
                    raise ValueError(
                        f"Unknown channel '{token}'. Available: {', '.join(labels)}"
                    ) from error
            if index not in indices:
                indices.append(index)
        if not indices:
            raise ValueError("--channels did not select any channels.")
        return indices

    if profile == "muse":
        for index, label in enumerate(labels):
            if label.casefold() == "af7":
                return [index]
        return [1 if len(labels) > 1 else 0]

    eeg_indices = [
        index
        for index, (label, kind) in enumerate(zip(labels, kinds))
        if _is_eeg_channel(label, kind)
    ]
    return eeg_indices or list(range(len(labels)))


def liveamp32_compatibility_issues(labels, kinds):
    """Return metadata issues that would make a LiveAmp-32 setup ambiguous."""
    eeg_indices = [
        index
        for index, (label, kind) in enumerate(zip(labels, kinds))
        if _is_eeg_channel(label, kind)
    ]
    issues = []
    if len(eeg_indices) != 32:
        issues.append(
            f"expected 32 EEG channels for LiveAmp 32, found {len(eeg_indices)}"
        )

    eeg_labels = [labels[index] for index in eeg_indices]
    folded = [label.casefold() for label in eeg_labels]
    if len(folded) != len(set(folded)):
        issues.append("EEG channel labels are not unique")
    if any(re.fullmatch(r"ch\d+", label, re.IGNORECASE) for label in eeg_labels):
        issues.append("one or more EEG channels have fallback labels instead of cap labels")
    return issues


def choose_stream(streams, requested_name=None, requested_source_id=None):
    """Choose one LSL stream deterministically from resolved candidates."""
    candidates = list(streams)
    if requested_source_id:
        candidates = [
            stream for stream in candidates if stream.source_id() == requested_source_id
        ]
    if requested_name:
        exact = [
            stream
            for stream in candidates
            if stream.name().casefold() == requested_name.casefold()
        ]
        if exact:
            candidates = exact
        else:
            candidates = [
                stream
                for stream in candidates
                if requested_name.casefold() in stream.name().casefold()
            ]
    if not candidates:
        raise ValueError("No LSL EEG stream matches the requested selection.")
    candidates.sort(key=lambda stream: (stream.name().casefold(), stream.source_id()))
    return candidates[0], len(candidates)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Device-independent EEG band analysis and Hyponoia OSC states via LSL."
        )
    )
    parser.add_argument("--stream-type", default="EEG", help="LSL stream type.")
    parser.add_argument("--stream-name", help="Exact or partial LSL stream name.")
    parser.add_argument("--source-id", help="Exact LSL source_id.")
    parser.add_argument(
        "--profile",
        choices=("auto", "muse", "liveamp", "generic"),
        default="auto",
        help="Channel-selection profile. Auto detects Muse/LiveAmp when possible.",
    )
    parser.add_argument(
        "--channels",
        help="Comma-separated channel labels or zero-based indices. Default: AF7 for Muse, all EEG channels otherwise.",
    )
    parser.add_argument(
        "--require-liveamp32",
        action="store_true",
        help=(
            "Fail unless the selected stream is recognised as LiveAmp and exposes "
            "exactly 32 uniquely labelled EEG channels."
        ),
    )
    parser.add_argument(
        "--aggregation",
        choices=("median", "mean", "single"),
        default="median",
        help="How to combine bandpower across selected channels.",
    )
    parser.add_argument(
        "--fs",
        type=float,
        default=None,
        help="Override sampling rate. Default: read nominal rate from LSL metadata.",
    )
    parser.add_argument(
        "--input-unit",
        choices=("auto", "volts", "millivolts", "microvolts", "nanovolts", "raw"),
        default="auto",
        help="Input amplitude unit. Auto reads per-channel LSL metadata.",
    )
    parser.add_argument("--win-sec", type=float, default=DEFAULT_WIN_SEC)
    parser.add_argument("--baseline-sec", type=float, default=DEFAULT_BASELINE_SEC)
    parser.add_argument("--z-threshold", type=float, default=DEFAULT_Z_THRESHOLD)
    parser.add_argument("--stream-timeout", type=float, default=10.0)
    parser.add_argument("--osc-ip", default=DEFAULT_OSC_IP)
    parser.add_argument("--osc-port", type=int, default=DEFAULT_OSC_PORT)
    parser.add_argument("--record", help="CSV path for processed values.")
    parser.add_argument("--duration", type=float, help="Optional run duration in seconds.")
    parser.add_argument("--no-print", dest="print_output", action="store_false")
    parser.set_defaults(print_output=True)
    return parser


def open_csv_writer(record_path):
    path = Path(record_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(handle)
    writer.writerow(
        [
            "timestamp",
            "source",
            "sampling_rate",
            "channels",
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


def send_metadata(client, stream_name, profile, fs, selected_labels, output_unit):
    """Tell Hyponoia what source is feeding its stable OSC state interface."""
    client.send_message("/eeg/source", stream_name)
    client.send_message("/eeg/profile", profile)
    client.send_message("/eeg/fs", float(fs))
    client.send_message("/eeg/channels", len(selected_labels))
    client.send_message("/eeg/channel_names", selected_labels)
    client.send_message("/eeg/unit", output_unit)


def send_initializing(client, bp):
    client.send_message("/bands", [bp["alpha"], bp["beta"], bp["theta"], bp["gamma"]])
    client.send_message("/state", 0)
    client.send_message("/state_name", "initializing")


def main():
    args = build_arg_parser().parse_args()

    try:
        from pylsl import StreamInlet, resolve_byprop
    except ImportError as error:
        raise SystemExit(
            "pylsl is required. Install the project requirements first."
        ) from error

    print(f"Resolving LSL stream (type='{args.stream_type}')...")
    streams = resolve_byprop("type", args.stream_type, timeout=args.stream_timeout)
    if not streams:
        raise SystemExit("No EEG LSL stream found. Start an EEG source or the simulator.")

    try:
        selected_stream, candidate_count = choose_stream(
            streams, args.stream_name, args.source_id
        )
    except ValueError as error:
        available = ", ".join(stream.name() for stream in streams)
        raise SystemExit(f"{error} Available streams: {available}") from error

    if candidate_count > 1 and not (args.stream_name or args.source_id):
        print(
            f"Found {candidate_count} matching streams; using '{selected_stream.name()}'. "
            "Use --stream-name to choose explicitly."
        )

    inlet = StreamInlet(selected_stream, max_buflen=10)
    info = inlet.info(timeout=args.stream_timeout)
    stream_name = info.name()
    labels, kinds, units = extract_channel_metadata(info)
    profile = args.profile if args.profile != "auto" else infer_profile(stream_name, labels)

    liveamp_issues = liveamp32_compatibility_issues(labels, kinds)
    if args.require_liveamp32:
        if profile != "liveamp":
            raise SystemExit(
                "The selected EEG stream is not recognised as LiveAmp. "
                "Choose the Brain Products stream or pass --profile liveamp."
            )
        if liveamp_issues:
            raise SystemExit(
                "LiveAmp-32 compatibility check failed: " + "; ".join(liveamp_issues)
            )
    elif profile == "liveamp" and liveamp_issues:
        print("LiveAmp metadata warning: " + "; ".join(liveamp_issues))

    try:
        channel_indices = select_channel_indices(
            labels, kinds, requested=args.channels, profile=profile
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error

    selected_labels = [labels[index] for index in channel_indices]
    selected_units = [units[index] for index in channel_indices]

    if args.input_unit == "raw":
        channel_scales = [1.0] * len(channel_indices)
        output_unit = "raw input units"
    elif args.input_unit == "auto":
        channel_scales = []
        unknown_units = []
        for label, unit in zip(selected_labels, selected_units):
            scale = unit_scale_to_microvolts(unit)
            if scale is None:
                scale = 1.0
                unknown_units.append(label)
            channel_scales.append(scale)
        output_unit = "microvolts"
        if unknown_units:
            print(
                "Warning: no recognised unit metadata for "
                f"{', '.join(unknown_units)}; treating those values as microvolts. "
                "Use --input-unit to override."
            )
    else:
        scale = unit_scale_to_microvolts(args.input_unit)
        channel_scales = [scale] * len(channel_indices)
        output_unit = "microvolts"
    fs = args.fs if args.fs is not None else float(info.nominal_srate())
    if fs <= 0:
        raise SystemExit("The stream has no nominal sampling rate; provide --fs.")
    if fs <= 2 * max(high for _low, high in BANDS.values()):
        raise SystemExit("Sampling rate is too low for the configured gamma band.")

    win_samples = max(2, int(round(fs * args.win_sec)))
    baseline_windows = max(5, int(args.baseline_sec // args.win_sec))

    print(f"Connected to: {stream_name}")
    print(f"Profile: {profile} | {fs:g} Hz | {len(labels)} stream channels")
    print(
        f"Analysing: {', '.join(selected_labels)} ({args.aggregation}, {output_unit})"
    )

    client = udp_client.SimpleUDPClient(args.osc_ip, args.osc_port)
    send_metadata(client, stream_name, profile, fs, selected_labels, output_unit)
    if profile == "liveamp" and not liveamp_issues:
        client.send_message("/eeg/compatibility", "brainproducts-liveamp32")
    print(f"Sending OSC to {args.osc_ip}:{args.osc_port}")

    csv_handle = None
    csv_writer = None
    if args.record:
        csv_handle, csv_writer = open_csv_writer(args.record)
        print(f"Recording processed values to: {args.record}")

    history = {name: deque(maxlen=baseline_windows) for name in BANDS}
    buffer = []
    start_time = time.time()

    try:
        while True:
            if args.duration is not None and time.time() - start_time >= args.duration:
                print("Duration reached. Stopping.")
                break

            chunk, _timestamps = inlet.pull_chunk(
                timeout=1.0, max_samples=max(win_samples, int(fs))
            )
            if not chunk:
                continue
            buffer.extend(chunk)

            while len(buffer) >= win_samples:
                data = np.asarray(buffer[:win_samples], dtype=float)
                del buffer[:win_samples]
                if data.ndim != 2 or data.shape[1] != len(labels):
                    print("Ignoring malformed EEG window.")
                    continue

                bp = aggregate_bandpowers(
                    data,
                    fs,
                    channel_indices,
                    aggregation=args.aggregation,
                    channel_scales=channel_scales,
                )
                for band_name in BANDS:
                    history[band_name].append(bp[band_name])

                if len(history["alpha"]) < 5:
                    send_initializing(client, bp)
                    if args.print_output:
                        print("Collecting baseline...")
                    continue

                z_vals = {
                    name: z_score(bp[name], history[name]) for name in BANDS
                }
                high_flags = {
                    name: z_vals[name] > args.z_threshold for name in BANDS
                }
                state_idx, state_name = detect_state(
                    high_flags, z_vals, args.z_threshold
                )

                client.send_message(
                    "/bands", [bp["alpha"], bp["beta"], bp["theta"], bp["gamma"]]
                )
                client.send_message(
                    "/bands_z",
                    [
                        z_vals["alpha"],
                        z_vals["beta"],
                        z_vals["theta"],
                        z_vals["gamma"],
                    ],
                )
                client.send_message("/state", state_idx)
                client.send_message("/state_name", state_name)

                if csv_writer:
                    csv_writer.writerow(
                        [
                            time.time(),
                            stream_name,
                            fs,
                            ";".join(selected_labels),
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
