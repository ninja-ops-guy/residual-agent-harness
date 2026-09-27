"""Structural governance checks only; not an operational release-authority gate."""
from graphlib import TopologicalSorter
from pathlib import Path
import re
import unittest

MATRIX = Path(__file__).parents[1] / "docs/v1/V1_CLAIMS_VERIFICATION_MATRIX.md"
EXPECTED = {
    "RC_SELECTED": ("NONE", "NONE"),
    "RC_QUALIFIED": ("RC_SELECTED", "CV-01..CV-16"),
    "SOAK_VERIFIED": ("RC_QUALIFIED", "CV-17"),
    "RELEASE_AUTHORIZED": ("SOAK_VERIFIED", "CV-18"),
}


def lifecycle(text):
    rows = {}
    for raw in text.splitlines():
        cells = [cell.strip().strip("`") for cell in raw.split("|")[1:-1]]
        if cells and cells[0] in EXPECTED:
            if len(cells) != 3 or cells[0] in rows:
                raise ValueError("ambiguous lifecycle row")
            rows[cells[0]] = (cells[1], cells[2])
    return rows


def check_contract(text):
    rows = lifecycle(text)
    if rows != EXPECTED:
        raise ValueError("missing, reordered or weakened lifecycle prerequisite")
    graph = {state: (() if parent == "NONE" else (parent,))
             for state, (parent, _) in rows.items()}
    return tuple(TopologicalSorter(graph).static_order())


class ClaimsLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.text = MATRIX.read_text(encoding="utf-8")

    def test_all_eighteen_claim_rows_remain(self):
        ids = re.findall(r"^\| (CV-[0-9]{2}) \|", self.text, re.MULTILINE)
        self.assertEqual(ids, [f"CV-{n:02}" for n in range(1, 19)])

    def test_selection_precedes_qualification_soak_and_authorization(self):
        self.assertEqual(check_contract(self.text), tuple(EXPECTED))

    def test_selection_has_no_future_evidence_dependency(self):
        self.assertEqual(lifecycle(self.text).get("RC_SELECTED"), ("NONE", "NONE"))
        self.assertIn("identity only", self.text)

    def test_final_claim_cannot_depend_on_itself(self):
        row = next(line for line in self.text.splitlines() if line.startswith("| CV-18 |"))
        dependency = row.split("|")[-2].strip()
        self.assertIn("CV-01..CV-17", dependency)
        self.assertNotIn("CV-18", dependency)

    def test_legacy_ready_names_have_unambiguous_meaning(self):
        self.assertIn("`RC_READY` is an alias for `RC_QUALIFIED`", self.text)
        self.assertIn("`V1_RELEASE_READY` is an alias for `RELEASE_AUTHORIZED`", self.text)

    def test_mandatory_final_gates_cannot_be_scope_excluded(self):
        self.assertIn("CV-16, CV-17 and CV-18 are mandatory and cannot be scope-excluded", self.text)
        self.assertIn("PROPOSED", self.text)

    def test_negative_cycle_and_omission_controls(self):
        check_contract(self.text)
        for bad in (
            self.text.replace("| `RC_SELECTED` | `NONE` |", "| `RC_SELECTED` | `RELEASE_AUTHORIZED` |"),
            self.text.replace("| `SOAK_VERIFIED` | `RC_QUALIFIED` | `CV-17` |", "| `SOAK_VERIFIED` | `RC_QUALIFIED` | `NONE` |"),
            self.text.replace("CV-01..CV-16", "CV-01..CV-15"),
            self.text.replace("| `RELEASE_AUTHORIZED` | `SOAK_VERIFIED` |", "| `RELEASE_AUTHORIZED` | `RC_SELECTED` |"),
        ):
            with self.subTest(bad=bad):
                self.assertNotEqual(bad, self.text)
                with self.assertRaises(ValueError):
                    check_contract(bad)


if __name__ == "__main__":
    unittest.main()
