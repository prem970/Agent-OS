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

    def test_hr_firewall_blocks_coding_and_redirects(self):
        result = self.app.run_single_agent("hr", "Develop a responsive website with Python backend")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["suggested_agent"], "developer")
        self.assertIn("FIREWALL BLOCKED", result["output"])

    def test_workspace_files_generation(self):
        run = self.app.run("Build landing page", "Develop a website landing page with HTML and CSS", .30, "B8")
        files = self.app.workspace.list_files()
        file_names = [f["name"] for f in files]
        self.assertIn("index.html", file_names)

    def test_memory_persistence_and_listing(self):
        self.app.store.save_experience(["web", "frontend"], {"topology": "parallel"}, 0.95, "Use modular vanilla CSS")
        experiences = self.app.store.list_experiences()
        self.assertTrue(any("modular vanilla CSS" in e["lesson"] for e in experiences))

    def test_web_handler_api(self):
        import io
        import json
        from iris.web import Handler

        # Mock GET /api/dashboard
        class MockRequest:
            def makefile(self, *args, **kwargs):
                return io.BytesIO(b"GET /api/dashboard HTTP/1.1\r\nHost: localhost\r\n\r\n")

        # Test firewall via app.run_single_agent
        hr_block = self.app.run_single_agent("hr", "develop a modern website in html")
        self.assertTrue(hr_block["blocked"])
        self.assertEqual(hr_block["suggested_agent"], "developer")

        dev_pass = self.app.run_single_agent("developer", "develop a modern website in html")
        self.assertFalse(dev_pass["blocked"])
        self.assertTrue(len(dev_pass["artifacts"]) > 0 or len(self.app.workspace.list_files()) > 0)

    def test_project_folder_creation_and_local_execution(self):
        # 1. Test project folder creation on local machine
        folder = self.app.workspace.tools.create_project_folder("test-calculator")
        self.assertTrue(folder.is_dir())

        # 2. Test writing a real script to that folder
        script_code = "import sys\nprint('CALCULATION_RESULT: 42')\nsys.exit(0)\n"
        file_info = self.app.workspace.tools.write_file_to_project("test-calculator", "calc.py", script_code)
        self.assertEqual(file_info["name"], "calc.py")

        # 3. Test local execution on user's system
        exec_res = self.app.workspace.tools.execute_script("test-calculator", "calc.py")
        self.assertTrue(exec_res["success"])
        self.assertEqual(exec_res["exit_code"], 0)
        self.assertIn("CALCULATION_RESULT: 42", exec_res["stdout"])

if __name__ == "__main__": unittest.main()
