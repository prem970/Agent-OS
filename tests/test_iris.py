import os
import tempfile
import unittest
from iris.orchestrator import IrisController
from iris.storage import Store


class IrisTests(unittest.TestCase):
    def setUp(self):
        fd, self.file = tempfile.mkstemp()
        os.close(fd)
        self.app = IrisController(Store(self.file))
    def tearDown(self): os.unlink(self.file)
    def test_coding_task_selects_startup_delivery_squad_and_persists_trace(self):
        run = self.app.run("Fix parser", "Implement Python code and tests with verification", .30, "B8")
        ids = {a["id"] for a in run["strategy"]["agents"]}
        self.assertTrue({"ceo", "developer", "testing", "review"}.issubset(ids))
        self.assertTrue(run["result"]["trace"])
        self.assertEqual(self.app.store.task(run["id"])["title"], "Fix parser")
    def test_experience_is_retrieved_for_related_task(self):
        self.app.run("Research sources", "Research a document and compare sources", .30, "B8")
        run = self.app.run("More research", "Research document sources", .30, "B7")
        self.assertIsNotNone(run["strategy"]["experience_id"])
    def test_b0_uses_one_agent(self):
        run = self.app.run("Simple", "reason about this", .10, "B0")
        self.assertEqual(len(run["strategy"]["agents"]), 1)

    def test_b8_runs_multiple_parallel_delivery_agents(self):
        run = self.app.run("Launch web app", "Build and test a web app", .30, "B8")
        parallel = [event for event in run["result"]["trace"] if event.get("phase") == "parallel_delivery"]
        self.assertGreaterEqual(len(parallel), 4)

if __name__ == "__main__": unittest.main()
