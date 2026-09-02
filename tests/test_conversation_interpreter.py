import unittest

from api.conversation_interpreter import (
    ensure_honest_ai_voice,
    interpret_turn,
    should_preserve_conversation_context,
)


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
            "Actually, switch topics: should governments regulate facial recognition?":
                "should governments regulate facial recognition?",
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

    def test_established_conversation_is_sticky_for_random_ordinary_turns(self):
        for message in (
            "so everything all right?",
            "what have you been up to?",
            "that was a strange day",
            "tell me something funny",
            "do you ever get bored?",
            "anyway what were we saying?",
            "the morning has been oddly slow",
            "sometimes old memories appear randomly",
            "often the smallest things bring back memories",
            "Relax, I’m only teasing you.",
            "I was joking with you.",
            "We are just bantering.",
        ):
            with self.subTest(message=message):
                self.assertTrue(
                    should_preserve_conversation_context(
                        user_text=message,
                        prior_response_mode="conversation",
                        study_mode_established=False,
                        requests_learning_map=True,
                        explicit_question_map_request=False,
                    )
                )

    def test_explicit_rejection_of_learning_mode_preserves_conversation(self):
        for message in (
            "I'm just chatting, not trying to study anything.",
            "We are only talking, not asking you to teach us.",
            "Let's chat; I do not want a Question Map.",
            "Let’s keep chatting—I don’t want to learn a topic.",
            "Don’t explain anything—I just want company.",
            "I don’t need a Question Map; tell me how you’re doing.",
        ):
            with self.subTest(message=message):
                self.assertTrue(
                    should_preserve_conversation_context(
                        user_text=message,
                        prior_response_mode="conversation",
                        study_mode_established=False,
                        requests_learning_map=True,
                        explicit_question_map_request=False,
                    )
                )

    def test_clear_learning_request_can_leave_casual_conversation(self):
        self.assertFalse(
            should_preserve_conversation_context(
                user_text="explain gradient descent",
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=True,
                explicit_question_map_request=False,
            )
        )
        self.assertFalse(
            should_preserve_conversation_context(
                user_text="anything",
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=False,
                explicit_question_map_request=True,
            )
        )

    def test_ordinary_preference_question_preserves_conversation(self):
        self.assertTrue(
            should_preserve_conversation_context(
                user_text="What kind of music suits a quiet evening?",
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=True,
                explicit_question_map_request=False,
            )
        )

    def test_bare_subject_can_leave_casual_conversation(self):
        self.assertFalse(
            should_preserve_conversation_context(
                user_text="linear regression",
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=True,
                explicit_question_map_request=False,
            )
        )

    def test_definition_question_can_leave_casual_conversation(self):
        self.assertFalse(
            should_preserve_conversation_context(
                user_text="what is linear regression?",
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=True,
                explicit_question_map_request=False,
            )
        )

    def test_compound_why_and_how_questions_leave_casual_conversation(self):
        for question in (
            "Why does inflation occur, and how do interest-rate increases attempt to control it?",
            "Why do transformers use attention, and how does it preserve context?",
        ):
            with self.subTest(question=question):
                self.assertFalse(
                    should_preserve_conversation_context(
                        user_text=question,
                        prior_response_mode="conversation",
                        study_mode_established=False,
                        requests_learning_map=True,
                        explicit_question_map_request=False,
                    )
                )

    def test_causal_learning_question_can_leave_casual_conversation(self):
        self.assertFalse(
            should_preserve_conversation_context(
                user_text=(
                    "What causes antibiotic resistance, and how can healthcare "
                    "systems limit it?"
                ),
                prior_response_mode="conversation",
                study_mode_established=False,
                requests_learning_map=True,
                explicit_question_map_request=False,
            )
        )

    def test_broad_topic_guess_cannot_override_established_conversation(self):
        casual_turns = (
            "na na its ok...",
            "it was a pretty busy day for me",
            "I was only thinking aloud",
            "let's not turn every thought into a lesson",
            "that is not what I meant",
            "you know what I mean right",
            "maybe we can just talk for a while",
            "I am feeling a little lost today",
            "well that was awkward",
            "no worries, carry on",
            "I liked your earlier answer",
            "that made me laugh",
            "what kind of humor do you understand",
            "I don't need a lesson right now",
            "sometimes I just want company",
            "it has been a long day",
            "you seem more natural now",
            "I was teasing you",
            "nothing serious, mate",
            "we are simply chatting",
            "okay, that is enough for tonight",
        )
        for turn in casual_turns:
            with self.subTest(turn=turn):
                self.assertTrue(
                    should_preserve_conversation_context(
                        user_text=turn,
                        prior_response_mode="conversation",
                        study_mode_established=False,
                        requests_learning_map=True,
                        explicit_question_map_request=False,
                    )
                )

    def test_personal_anecdote_is_explicitly_labeled_fictional(self):
        for generated in (
            "Once I tried to help and forgot what I had suggested.",
            "Once at a coffee shop I was trying to impress a friend.",
            "I once waved at someone I thought I knew.",
        ):
            with self.subTest(generated=generated):
                reply = ensure_honest_ai_voice(
                    "tell me a harmless embarrassing story",
                    generated,
                )
                self.assertTrue(reply.startswith("I don't have personal experiences or memories"))
                self.assertIn("fictional story", reply)

    def test_non_anecdotal_conversation_is_unchanged(self):
        reply = "I don't have personal likes, but rainy afternoons appeal to many people."
        self.assertEqual(
            ensure_honest_ai_voice("do you like rainy afternoons?", reply),
            reply,
        )

if __name__ == "__main__":
    unittest.main()
