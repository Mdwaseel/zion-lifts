"""The lifecycle rules, tested as rules rather than through a document."""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.knowledge.states import (
    INGESTION_SEQUENCE,
    TRANSITIONS,
    DocumentState,
    InvalidTransition,
    can_transition,
    check,
    progress_for,
)

S = DocumentState


class TransitionRulesTests(SimpleTestCase):
    def test_the_happy_path_is_walkable_end_to_end(self):
        for current, following in zip(INGESTION_SEQUENCE, INGESTION_SEQUENCE[1:]):
            self.assertTrue(
                can_transition(current, following), f"{current} -> {following} should be allowed"
            )

    def test_every_working_stage_can_fail(self):
        for stage in (S.PROCESSING, S.EXTRACTING, S.CHUNKING, S.EMBEDDING, S.INDEXING):
            self.assertTrue(can_transition(stage, S.FAILED), f"{stage} must be able to fail")

    def test_failed_can_be_retried(self):
        self.assertTrue(can_transition(S.FAILED, S.PROCESSING))

    def test_ready_can_be_reindexed(self):
        self.assertTrue(can_transition(S.READY, S.PROCESSING))

    def test_stages_cannot_be_skipped(self):
        # The point of separate stages is that they are reported in order; a
        # jump from EXTRACTING straight to READY would mean nothing was indexed.
        self.assertFalse(can_transition(S.EXTRACTING, S.READY))
        self.assertFalse(can_transition(S.CHUNKING, S.READY))
        self.assertFalse(can_transition(S.EMBEDDING, S.READY))
        self.assertFalse(can_transition(S.UPLOADED, S.INDEXING))
        self.assertFalse(can_transition(S.UPLOADED, S.READY))

    def test_processing_may_go_straight_to_ready(self):
        # The documented exception: a Document summarises its versions rather
        # than being extracted itself, so re-indexing one that is already live
        # returns it to READY without marching through stages nothing reports
        # on its behalf. A *version* still cannot take this route, because a
        # version reaches READY from INDEXING and the stages above are closed.
        self.assertTrue(can_transition(S.PROCESSING, S.READY))

    def test_a_stage_cannot_re_enter_itself(self):
        # A duplicated task delivery must not look like fresh progress.
        for state in TRANSITIONS:
            self.assertFalse(can_transition(state, state), f"{state} -> {state}")

    def test_deletion_is_a_one_way_street(self):
        self.assertTrue(can_transition(S.READY, S.DELETING))
        self.assertTrue(can_transition(S.DELETING, S.DELETED))
        # A document being deleted must not fall back into the ingestion path.
        self.assertFalse(can_transition(S.DELETING, S.PROCESSING))
        self.assertFalse(can_transition(S.DELETING, S.READY))

    def test_deleted_is_terminal(self):
        self.assertEqual(TRANSITIONS[S.DELETED], frozenset())

    def test_check_raises_with_the_allowed_moves_named(self):
        with self.assertRaises(InvalidTransition) as caught:
            check(S.READY, S.INDEXING)
        message = str(caught.exception)
        self.assertIn("ready", message)
        self.assertIn("indexing", message)
        # The message has to say what *is* allowed, or it only reports a dead end.
        self.assertIn("processing", message)

    def test_every_target_is_itself_a_known_state(self):
        known = set(TRANSITIONS)
        for source, targets in TRANSITIONS.items():
            for target in targets:
                self.assertIn(target, known, f"{source} -> {target} names an unknown state")


class ProgressTests(SimpleTestCase):
    def test_progress_rises_monotonically_through_the_sequence(self):
        values = [progress_for(stage) for stage in INGESTION_SEQUENCE]
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], 100)

    def test_states_outside_the_sequence_report_nothing(self):
        self.assertEqual(progress_for(S.UPLOADED), 0)
        self.assertEqual(progress_for(S.FAILED), 0)

    def test_progress_is_a_whole_percent(self):
        for stage in INGESTION_SEQUENCE:
            value = progress_for(stage)
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)
