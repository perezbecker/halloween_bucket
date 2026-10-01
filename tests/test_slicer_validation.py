import json
from pathlib import Path
import unittest

from tools.check_slicer import verify_carrier_guard_sequence


class CarrierGuardSequenceTests(unittest.TestCase):
    counts = {"M2 x 20 carrier": 2, "Battery guard": 3}

    def contents(self, carrier_id=0, guard_id=1, layers=None):
        if layers is None:
            layers = ((carrier_id, guard_id), (guard_id, carrier_id), (guard_id,))
        lines = [
            f"M486 S{carrier_id}", "M486 AM2 x 20 carrier", "M486 S-1",
            f"M486 S{guard_id}", "M486 ABattery guard", "M486 S-1",
        ]
        for objects in layers:
            lines.append(";LAYER_CHANGE")
            for object_id in objects:
                lines.extend((f"M486 S{object_id}", "G1 X20 Y30 E0.1"))
        return "\n".join(lines)

    def test_either_native_object_order_is_valid(self):
        for carrier_id, guard_id in ((0, 1), (1, 0)):
            with self.subTest(carrier_id=carrier_id):
                result = verify_carrier_guard_sequence(self.contents(carrier_id, guard_id), self.counts)
                self.assertEqual(result["layer_count"], 3)
                self.assertEqual(result["layers_printing_both_objects"], 2)
                self.assertEqual(result["remaining_guard_only_layers"], 1)

    def test_invalid_layer_sequences_are_rejected(self):
        for layers in (
            ((0, 1), (0, 1), (0,)),
            ((0,), (0, 1), (1,)),
            ((0,), (0,), (1,), (1,), (1,)),
            ((0, 1), (0, 1)),
            ((0, 1), (0, 1), (1,), (1,)),
            ((0, 1), (0, 1), (2,)),
            ((0, 1), (0, 1), (-1,)),
        ):
            with self.subTest(layers=layers), self.assertRaises(ValueError):
                verify_carrier_guard_sequence(self.contents(layers=layers), self.counts)

    def test_invalid_object_declarations_are_rejected(self):
        original = self.contents()
        for contents in (
            original.replace("M486 ABattery guard\n", ""),
            original.replace("M486 ABattery guard", "M486 AUnknown part"),
            original.replace("M486 ABattery guard", "M486 AM2 x 20 carrier"),
            original.replace("M486 S1\nM486 ABattery guard", "M486 S0\nM486 ABattery guard"),
            original + "\nM486 S2\nM486 ABattery guard",
        ):
            with self.subTest(contents=contents), self.assertRaises(ValueError):
                verify_carrier_guard_sequence(contents, self.counts)

    def test_invalid_expected_layer_counts_are_rejected(self):
        for counts in ({}, {"M2 x 20 carrier": 2}, {"M2 x 20 carrier": 0, "Battery guard": 3}):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                verify_carrier_guard_sequence(self.contents(), counts)


class BuildManifestTests(unittest.TestCase):
    def test_base_manifest_only_tracks_its_own_exports(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root / "docs/validation.json").read_text())
        expected = set(report["plates"]) | {f"{name}.stl" for name in report["parts"]}
        self.assertEqual(set(report["files_sha256"]), expected)
        combined = json.loads((root / "docs/carrier_guard_validation.json").read_text())
        self.assertNotIn(Path(combined["source_3mf"]).name, report["files_sha256"])


if __name__ == "__main__":
    unittest.main()
