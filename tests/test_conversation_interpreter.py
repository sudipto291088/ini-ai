import unittest

from api.conversation_interpreter import interpret_turn


class ConversationInterpreterTests(unittest.TestCase):
    def test_discourse_markers_are_not_part_of_topic(self):
        cases = {
            "yea hexadecimal code": "hexadecimal code",
            "Yeah, machine learning": "machine learning",
            "okay then explain spatial artificial intelligence": "explain spatial artificial intelligence",
            "all right, quantum computing": "quantum computing",
            "I mean hexadecimal code": "hexadecimal code",
            "Actually, I meant multi-core scaling": "multi-core scaling",
            "So, cognitive science": "cognitive science",
            "yea octa core, sorry": "octa core",
            "okay quantum computing — my bad": "quantum computing",
            "right, data science; apologies": "data science",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(interpret_turn(raw).semantic_text, expected)

    def test_standalone_confirmation_is_preserved(self):
        for raw in ("yes", "Yeah!", "okay", "go ahead", "please"):
            with self.subTest(raw=raw):
                turn = interpret_turn(raw)
                self.assertTrue(turn.is_confirmation)
                self.assertEqual(turn.semantic_text, raw.strip())

    def test_standalone_denial_is_preserved(self):
        for raw in ("no", "Nope!", "not that"):
            with self.subTest(raw=raw):
                self.assertTrue(interpret_turn(raw).is_denial)

    def test_contextual_followup_is_not_recast_as_topic(self):
        for raw in ("what else", "So what else?", "anything else"):
            with self.subTest(raw=raw):
                self.assertTrue(interpret_turn(raw).is_ambiguous_followup)

    def test_raw_record_is_never_rewritten(self):
        raw = "  Yeah,   machine learning! "
        turn = interpret_turn(raw)
        self.assertEqual(turn.raw_text, "Yeah, machine learning!")
        self.assertEqual(turn.semantic_text, "machine learning!")


if __name__ == "__main__":
    unittest.main()
