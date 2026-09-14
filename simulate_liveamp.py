#!/usr/bin/env python3
"""Publish a realistic synthetic 32-channel LiveAmp-like EEG stream via LSL."""

import argparse
import time

import numpy as np


# Representative standard 32-channel actiCAP/LiveAmp montage used only by the
# simulator. The delivered cap and BrainVision workspace remain authoritative.
DEFAULT_SIMULATED_CHANNEL_LABELS = [
    "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "FT9",
    "FC5", "FC1", "FC2", "FC6", "FT10", "C3", "Cz", "C4",
    "T7", "T8", "TP9", "CP5", "CP1", "CP2", "CP6", "TP10",
    "P7", "P3", "Pz", "P4", "P8", "O1", "Oz", "O2",
]

SCENARIO_AMPLITUDES = {
    "neutral": (2.0, 2.0, 1.5, 1.0),
    "alpha_theta": (6.0, 6.0, 1.0, 0.7),
    "beta_gamma": (1.0, 1.0, 6.0, 5.0),
    "beta_alpha": (1.0, 6.0, 6.0, 0.7),
    "alpha_gamma": (1.0, 6.0, 1.0, 5.0),
    "theta_dominant": (8.0, 1.0, 1.0, 0.7),
}


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Synthetic LiveAmp-32 LSL EEG source.")
    parser.add_argument("--name", default="Hyponoia-Simulated-LiveAmp-32")
    parser.add_argument("--fs", type=float, default=500.0)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--chunk-ms", type=float, default=20.0)
    parser.add_argument("--state-sec", type=float, default=12.0)
    parser.add_argument(
        "--marker-stream-name",
        default="Hyponoia-Simulated-TriggerBox-Markers",
    )
    parser.add_argument(
        "--no-markers",
        action="store_true",
        help="Do not publish the simulated TriggerBox marker stream.",
    )
    parser.add_argument(
        "--channel-labels",
        help=(
            "Comma-separated labels for all 32 simulated channels. Default is a "
            "representative standard montage, not a guaranteed delivery mapping."
        ),
    )
    parser.add_argument(
        "--scenario",
        choices=("cycle", *SCENARIO_AMPLITUDES),
        default="cycle",
    )
    parser.add_argument("--seed", type=int, default=7)
    return parser


def synthetic_chunk(
    rng, start_sample, sample_count, fs, scenario, phases, channel_count
):
    """Create samples x channels EEG values in microvolts."""
    theta_amp, alpha_amp, beta_amp, gamma_amp = SCENARIO_AMPLITUDES[scenario]
    t = (start_sample + np.arange(sample_count)) / fs
    frequencies = (6.0, 10.0, 20.0, 38.0)
    amplitudes = (theta_amp, alpha_amp, beta_amp, gamma_amp)

    chunk = np.empty((sample_count, channel_count), dtype=np.float32)
    for channel in range(channel_count):
        signal = np.zeros(sample_count)
        spatial_scale = 0.8 + 0.4 * np.sin((channel + 1) * 0.73) ** 2
        for band_index, (frequency, amplitude) in enumerate(zip(frequencies, amplitudes)):
            signal += (
                spatial_scale
                * amplitude
                * np.sin(2 * np.pi * frequency * t + phases[channel, band_index])
            )
        signal += rng.normal(0.0, 1.5, sample_count)
        chunk[:, channel] = signal
    return chunk


def main():
    args = build_arg_parser().parse_args()
    if args.fs <= 90:
        raise SystemExit("--fs must be above 90 Hz for the configured gamma band.")
    if args.chunk_ms <= 0 or args.state_sec <= 0:
        raise SystemExit("--chunk-ms and --state-sec must be positive.")

    channel_labels = (
        [label.strip() for label in args.channel_labels.split(",")]
        if args.channel_labels
        else DEFAULT_SIMULATED_CHANNEL_LABELS
    )
    if len(channel_labels) != 32 or any(not label for label in channel_labels):
        raise SystemExit("--channel-labels must contain exactly 32 non-empty labels.")
    if len({label.casefold() for label in channel_labels}) != 32:
        raise SystemExit("--channel-labels must not contain duplicate labels.")

    try:
        from pylsl import IRREGULAR_RATE, StreamInfo, StreamOutlet, cf_string
    except ImportError as error:
        raise SystemExit(
            "pylsl is required. Install the project requirements first."
        ) from error

    info = StreamInfo(
        args.name,
        "EEG",
        len(channel_labels),
        args.fs,
        "float32",
        "hyponoia-sim-liveamp32",
    )
    info.desc().append_child_value("manufacturer", "Brain Products (simulated)")
    info.desc().append_child_value("model", "LiveAmp 32")
    channels = info.desc().append_child("channels")
    for label in channel_labels:
        channel = channels.append_child("channel")
        channel.append_child_value("label", label)
        channel.append_child_value("type", "EEG")
        channel.append_child_value("unit", "microvolts")

    outlet = StreamOutlet(info, chunk_size=max(1, int(args.fs * args.chunk_ms / 1000)))
    marker_outlet = None
    if not args.no_markers:
        marker_info = StreamInfo(
            args.marker_stream_name,
            "Markers",
            1,
            IRREGULAR_RATE,
            cf_string,
            "hyponoia-sim-triggerbox",
        )
        marker_info.desc().append_child_value(
            "manufacturer", "Brain Products TriggerBox Plus (simulated)"
        )
        marker_channel = marker_info.desc().append_child("channels").append_child(
            "channel"
        )
        marker_channel.append_child_value("label", "Trigger")
        marker_channel.append_child_value("type", "Markers")
        marker_outlet = StreamOutlet(marker_info)
    rng = np.random.default_rng(args.seed)
    phases = rng.uniform(0, 2 * np.pi, (len(channel_labels), 4))
    scenarios = list(SCENARIO_AMPLITUDES)
    chunk_samples = max(1, int(round(args.fs * args.chunk_ms / 1000)))
    start = time.perf_counter()
    next_push = start
    sample_index = 0
    last_scenario = None

    print(f"Publishing '{args.name}': 32 EEG channels at {args.fs:g} Hz")
    if marker_outlet:
        print(f"Publishing markers: '{args.marker_stream_name}'")
    print("Simulator montage only; the real LSL stream metadata are authoritative.")
    print("Start hyponoia_microstates.py in another terminal. Ctrl-C stops the stream.")

    try:
        while args.duration is None or time.perf_counter() - start < args.duration:
            elapsed = time.perf_counter() - start
            if args.scenario == "cycle":
                scenario = scenarios[int(elapsed // args.state_sec) % len(scenarios)]
            else:
                scenario = args.scenario
            if scenario != last_scenario:
                print(f"Scenario: {scenario}")
                if marker_outlet:
                    marker_outlet.push_sample([f"state:{scenario}"])
                last_scenario = scenario

            chunk = synthetic_chunk(
                rng,
                sample_index,
                chunk_samples,
                args.fs,
                scenario,
                phases,
                len(channel_labels),
            )
            outlet.push_chunk(chunk.tolist())
            sample_index += chunk_samples
            next_push += chunk_samples / args.fs
            time.sleep(max(0.0, next_push - time.perf_counter()))
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
