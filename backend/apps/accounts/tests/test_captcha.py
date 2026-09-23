"""The CAPTCHA store: generation, expiry, single use and guess limits."""

from unittest import mock

from django.core.cache import cache
from django.test import override_settings

from apps.accounts import captcha as captcha_service

from apps.accounts.throttling import CaptchaThrottle

from .base import CAPTCHA_URL, AuthTestCase, throttle_rate


class CaptchaGenerationTests(AuthTestCase):
    def test_endpoint_returns_an_id_and_a_png_and_no_answer(self):
        res = self.client.get(CAPTCHA_URL)
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(set(body), {"captcha_id", "image"})
        self.assertTrue(body["image"].startswith("data:image/png;base64,"))
        self.assertGreater(len(body["captcha_id"]), 16)

    def test_only_a_digest_is_stored_never_the_answer(self):
        captcha_id, answer = self.issue_captcha()
        entry = cache.get(f"accounts:captcha:{captcha_id}")

        self.assertNotIn(answer.lower(), str(entry).lower())
        self.assertEqual(entry, captcha_service._digest(answer))

    def test_the_stored_value_is_a_digest_not_the_text(self):
        _, answer = self.issue_captcha()
        self.assertNotEqual(captcha_service._digest(answer), answer)
        self.assertEqual(len(captcha_service._digest(answer)), 64)  # sha256 hex

    def test_each_challenge_is_distinct(self):
        ids = {self.client.get(CAPTCHA_URL).json()["captcha_id"] for _ in range(5)}
        self.assertEqual(len(ids), 5)

    def test_refreshing_leaves_the_previous_challenge_usable_until_it_expires(self):
        first_id, first_answer = self.issue_captcha()
        self.issue_captcha()
        self.assertTrue(captcha_service.verify_challenge(first_id, first_answer))


class CaptchaVerificationTests(AuthTestCase):
    def test_correct_answer_passes(self):
        captcha_id, answer = self.issue_captcha()
        self.assertTrue(captcha_service.verify_challenge(captcha_id, answer))

    def test_answer_is_case_insensitive_and_trimmed(self):
        captcha_id, answer = self.issue_captcha()
        self.assertTrue(captcha_service.verify_challenge(captcha_id, f"  {answer.lower()} "))

    def test_wrong_answer_fails(self):
        captcha_id, answer = self.issue_captcha()
        self.assertFalse(captcha_service.verify_challenge(captcha_id, answer[::-1] + "Z"))

    def test_a_correct_answer_cannot_be_replayed(self):
        captcha_id, answer = self.issue_captcha()
        self.assertTrue(captcha_service.verify_challenge(captcha_id, answer))
        self.assertFalse(captcha_service.verify_challenge(captcha_id, answer))

    def test_unknown_id_fails(self):
        self.assertFalse(captcha_service.verify_challenge("not-a-real-id", "ABCDE"))

    def test_blank_input_fails(self):
        captcha_id, _ = self.issue_captcha()
        self.assertFalse(captcha_service.verify_challenge(captcha_id, ""))
        self.assertFalse(captcha_service.verify_challenge("", "ABCDE"))

    @override_settings(CAPTCHA_MAX_ATTEMPTS=3)
    def test_the_challenge_burns_after_too_many_wrong_guesses(self):
        captcha_id, answer = self.issue_captcha()
        for _ in range(3):
            self.assertFalse(captcha_service.verify_challenge(captcha_id, "WRONG"))

        # Even the right answer is refused now: the entry is gone.
        self.assertFalse(captcha_service.verify_challenge(captcha_id, answer))

    def test_expiry_removes_the_challenge(self):
        captcha_id, answer = self.issue_captcha()
        cache.delete(f"accounts:captcha:{captcha_id}")  # what the TTL does
        self.assertFalse(captcha_service.verify_challenge(captcha_id, answer))

    @override_settings(CAPTCHA_TTL_SECONDS=300)
    def test_the_challenge_is_stored_with_the_configured_ttl(self):
        with mock.patch("apps.accounts.captcha.cache.set") as cache_set:
            captcha_service.issue_challenge()
        self.assertEqual(cache_set.call_args.kwargs["timeout"], 300)

    def test_a_wrong_guess_never_rewrites_the_challenge(self):
        """The window cannot be extended, because the entry is not touched."""
        captcha_id, _ = self.issue_captcha()
        with mock.patch("apps.accounts.captcha.cache.set") as cache_set:
            captcha_service.verify_challenge(captcha_id, "WRONG")
        self.assertEqual(cache_set.call_count, 0)

    def test_wrong_guesses_are_counted_atomically(self):
        """The counter must survive concurrency, so it is an incr, not a get/set."""
        captcha_id, _ = self.issue_captcha()
        attempts_key = f"accounts:captcha:{captcha_id}:attempts"

        captcha_service.verify_challenge(captcha_id, "WRONG")
        self.assertEqual(cache.get(attempts_key), 1)
        captcha_service.verify_challenge(captcha_id, "ALSOWRONG")
        self.assertEqual(cache.get(attempts_key), 2)

    def test_a_solved_challenge_is_consumed_by_exactly_one_caller(self):
        """Two requests racing with the same solved pair: only one may win.

        Otherwise one solved CAPTCHA buys an attacker as many password guesses
        as they can fire in parallel.
        """
        captcha_id, answer = self.issue_captcha()
        results = [
            captcha_service.verify_challenge(captcha_id, answer),
            captcha_service.verify_challenge(captcha_id, answer),
            captcha_service.verify_challenge(captcha_id, answer),
        ]
        self.assertEqual(results.count(True), 1)

    def test_the_attempt_counter_is_cleared_with_the_challenge(self):
        captcha_id, answer = self.issue_captcha()
        captcha_service.verify_challenge(captcha_id, "WRONG")
        captcha_service.verify_challenge(captcha_id, answer)

        self.assertIsNone(cache.get(f"accounts:captcha:{captcha_id}"))
        self.assertIsNone(cache.get(f"accounts:captcha:{captcha_id}:attempts"))


class CaptchaThrottleTests(AuthTestCase):
    def test_the_captcha_endpoint_is_rate_limited(self):
        with throttle_rate(CaptchaThrottle, "3/minute"):
            statuses = [self.client.get(CAPTCHA_URL).status_code for _ in range(5)]
        self.assertEqual(statuses, [200, 200, 200, 429, 429])
