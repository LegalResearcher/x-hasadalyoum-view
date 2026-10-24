import os
import tempfile
import unittest

from main import run_send
from processing_state import load_failures, load_successes


class FakeSender:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def __call__(self, link):
        self.calls.append(link)
        return self.outcomes.pop(0) if self.outcomes else "ok"


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = self.temp.name
        self.links = [f"https://x.com/hasadalyoum1/status/{number}" for number in range(1, 8)]
        with open(os.path.join(self.state, "telegram_links.txt"), "w", encoding="utf-8") as file:
            file.write("\n".join(self.links) + "\n")

    def tearDown(self):
        self.temp.cleanup()

    def test_run_limit_and_success_count_carry_over_to_five(self):
        first = FakeSender(["ok"] * 5)
        self.assertEqual(run_send(first, self.state), 0)
        self.assertEqual(len(first.calls), 5)
        self.assertEqual(load_successes(self.state)[self.links[0]], 1)
        second = FakeSender(["ok"] * 5)
        self.assertEqual(run_send(second, self.state), 0)
        self.assertEqual(len(second.calls), 5)
        self.assertEqual(load_successes(self.state)[self.links[0]], 2)
        for _ in range(3):
            run_send(FakeSender(["ok"] * 5), self.state)
        self.assertEqual(load_successes(self.state)[self.links[0]], 5)
        later = FakeSender(["ok"] * 5)
        run_send(later, self.state)
        self.assertEqual(later.calls, self.links[5:])

    def test_failure_does_not_increase_success_and_three_failures_skip(self):
        run_send(FakeSender(["fail"] * 5), self.state)
        self.assertEqual(load_successes(self.state), {})
        self.assertEqual(load_failures(self.state)[self.links[0]], 1)
        run_send(FakeSender(["fail"] * 5), self.state)
        run_send(FakeSender(["fail"] * 5), self.state)
        self.assertEqual(load_failures(self.state)[self.links[0]], 3)
        later = FakeSender(["ok"] * 5)
        run_send(later, self.state)
        self.assertNotIn(self.links[0], later.calls)

    def test_legacy_done_links_stay_complete_and_unchanged(self):
        done_path = os.path.join(self.state, "done_links.txt")
        with open(done_path, "w", encoding="utf-8") as file:
            file.write(self.links[0] + "\n")
        with open(done_path, "rb") as file:
            original = file.read()
        sender = FakeSender(["ok"] * 5)
        run_send(sender, self.state)
        self.assertNotIn(self.links[0], sender.calls)
        self.assertNotIn(self.links[0], load_successes(self.state))
        with open(done_path, "rb") as file:
            self.assertEqual(file.read(), original)

    def test_failure_only_updates_failure_counter(self):
        run_send(FakeSender(["fail"] * 5), self.state)
        self.assertEqual(load_successes(self.state), {})
        self.assertEqual(load_failures(self.state)[self.links[0]], 1)


if __name__ == "__main__":
    unittest.main()
