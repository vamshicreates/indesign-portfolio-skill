import unittest
from pathlib import Path
from sys import path as sys_path

sys_path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from laya_decision import decide  # noqa: E402


class FakeRouter:
    calls = 0

    def predict(self, state, questions, min_confidence):
        type(self).calls += 1
        assert min_confidence == 0.7
        return {"answers": {"portfolio_choice": {"choice": "editorial", "answer_confidence": 0.86}},
                "routing": {"model": "english"}}


class LayaDecisionTests(unittest.TestCase):
    def setUp(self):
        FakeRouter.calls = 0
        self.criteria = {"editorial": "project-led pages", "gallery": "image-led pages"}

    def test_direct_choice_bypasses_laya(self):
        result = decide("Use the editorial layout", "Which layout?", self.criteria,
                        ambiguous=False, router_factory=FakeRouter)
        self.assertFalse(result["laya_called"])
        self.assertIsNone(result["choice"])
        self.assertEqual(FakeRouter.calls, 0)

    def test_ambiguous_choice_calls_laya_once(self):
        result = decide("Both layouts fit the reference", "Which layout?", self.criteria,
                        ambiguous=True, reason="Two plausible visual directions remain", router_factory=FakeRouter)
        self.assertTrue(result["laya_called"])
        self.assertEqual(result["choice"], "editorial")
        self.assertEqual(FakeRouter.calls, 1)

    def test_reason_is_required_for_model_call(self):
        with self.assertRaisesRegex(ValueError, "Explain why"):
            decide("Ambiguous", "Which layout?", self.criteria, ambiguous=True, router_factory=FakeRouter)


if __name__ == "__main__":
    unittest.main()
