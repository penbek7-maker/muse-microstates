import unittest

import numpy as np

from hyponoia_microstates import (
    aggregate_bandpowers,
    detect_state,
    infer_profile,
    select_channel_indices,
    unit_scale_to_microvolts,
)


class HyponoiaMicrostatesTests(unittest.TestCase):
    def test_preserves_artistic_state_rules(self):
        z = {"alpha": 1.0, "beta": 0.0, "theta": 1.0, "gamma": 0.0}
        flags = {name: value > 0.5 for name, value in z.items()}
        self.assertEqual(detect_state(flags, z, 0.5), (1, "alpha_theta"))

    def test_muse_profile_selects_af7(self):
        labels = ["TP9", "AF7", "AF8", "TP10", "AUX"]
        kinds = ["EEG", "EEG", "EEG", "EEG", "AUX"]
        self.assertEqual(select_channel_indices(labels, kinds, profile="muse"), [1])

    def test_generic_profile_excludes_auxiliary_channels(self):
        labels = ["Fp1", "Cz", "ACC_X", "Trigger"]
        kinds = ["EEG", "EEG", "ACC", "Markers"]
        self.assertEqual(select_channel_indices(labels, kinds), [0, 1])

    def test_named_and_indexed_channel_selection(self):
        labels = ["Fp1", "Cz", "Pz"]
        kinds = ["EEG"] * 3
        self.assertEqual(
            select_channel_indices(labels, kinds, requested="Pz,0"), [2, 0]
        )

    def test_profile_inference(self):
        self.assertEqual(
            infer_profile("Muse-2", ["TP9", "AF7", "AF8", "TP10"]), "muse"
        )
        self.assertEqual(infer_profile("LiveAmpSN123", ["Fp1"]), "liveamp")

    def test_bandpower_finds_dominant_alpha(self):
        fs = 500
        t = np.arange(fs * 2) / fs
        alpha = np.sin(2 * np.pi * 10 * t)
        data = np.column_stack([alpha, alpha * 0.8])
        powers = aggregate_bandpowers(data, fs, [0, 1], aggregation="median")
        self.assertGreater(powers["alpha"], powers["theta"] * 100)
        self.assertGreater(powers["alpha"], powers["beta"] * 100)

    def test_units_are_normalized_to_microvolts(self):
        self.assertEqual(unit_scale_to_microvolts("V"), 1_000_000.0)
        self.assertEqual(unit_scale_to_microvolts("µV"), 1.0)
        self.assertEqual(unit_scale_to_microvolts("nanovolts"), 0.001)
        self.assertIsNone(unit_scale_to_microvolts("counts"))


if __name__ == "__main__":
    unittest.main()
