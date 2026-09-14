import unittest

from simulate_liveamp import DEFAULT_SIMULATED_CHANNEL_LABELS


class SimulatedLiveAmpTests(unittest.TestCase):
    def test_representative_montage_has_32_unique_labels(self):
        self.assertEqual(len(DEFAULT_SIMULATED_CHANNEL_LABELS), 32)
        self.assertEqual(
            len({label.casefold() for label in DEFAULT_SIMULATED_CHANNEL_LABELS}), 32
        )


if __name__ == "__main__":
    unittest.main()
