import contextlib
import io
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import report  # noqa: E402

AGENT_JOB = HERE / "report" / "agent-job" / "result.json"
ORACLE_JOB = HERE / "report" / "oracle-job" / "result.json"


def run_report(result_path, min_mean_reward="", artifact=""):
    with tempfile.TemporaryDirectory() as directory:
        output, summary = pathlib.Path(directory, "output"), pathlib.Path(directory, "summary")
        environment = {
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(summary),
            "INPUT_MIN_MEAN_REWARD": min_mean_reward,
            "HBENCH_ARTIFACT_NAME": artifact,
            "GITHUB_REPOSITORY": "you/tasks",
            "GITHUB_RUN_ID": "123456",
        }
        with mock.patch.dict(os.environ, environment), contextlib.redirect_stdout(io.StringIO()):
            status = report.main([str(result_path)])
        outputs = dict(line.split("=", 1) for line in output.read_text().splitlines())
        return status, outputs, summary.read_text()


class AgentJobTest(unittest.TestCase):
    def setUp(self):
        self.status, self.outputs, self.summary = run_report(AGENT_JOB)

    def test_outputs_count_solved_trials_and_cost(self):
        self.assertEqual(self.status, 0)
        self.assertEqual(self.outputs["n-trials"], "3")
        self.assertEqual(self.outputs["n-solved"], "1")
        self.assertEqual(self.outputs["pass-rate"], "0.333333")
        self.assertEqual(self.outputs["n-errors"], "1")
        self.assertEqual(self.outputs["mean-reward"], "0.5")
        self.assertEqual(self.outputs["cost-usd"], "0.1234")

    def test_scorecard_has_pass_rate_time_tokens_and_cost_per_solved_task(self):
        self.assertIn("**1 / 3** (33.3%)", self.summary)
        self.assertIn("12m 15s total, 1m 30s median", self.summary)
        self.assertIn("400.0K / 14.5K (250.0K cached)", self.summary)
        self.assertIn("$0.1234 ($0.1234 per solved)", self.summary)

    def test_what_ran_names_hbench_agent_model_and_tasks(self):
        self.assertIn("- **hbench** 0.3.0, results epoch 0.2", self.summary)
        self.assertIn("- **Agent** `claude-code`, model `anthropic/claude-opus-5-5`", self.summary)
        self.assertIn("- **Tasks** `example@1.0` from `registry.json`", self.summary)
        self.assertIn("- **Attempts** 1 per task, 3 at a time", self.summary)
        self.assertIn("- **Ran** 2026-10-22 05:21 to 05:33 UTC, 11m 30s", self.summary)

    def test_tasks_metrics_and_errors_are_listed(self):
        self.assertIn("`field_score` 0.750", self.summary)
        self.assertIn("- **AgentTimeoutError** in `claude-code__claude-opus-5-5__example`: 1 (`hello-world__c3`)", self.summary)

    def test_trials_list_errors_then_failures_then_solved(self):
        error = self.summary.index("| `example/hello-world` | ⚠️ AgentTimeoutError |")
        failure = self.summary.index("| `example/count-words` | ❌ failed | 0.000 |")
        solved = self.summary.index("| `example/fix-median` | ✅ solved | 1.000 |")
        self.assertLess(error, failure)
        self.assertLess(failure, solved)

    def test_charts_show_the_trials_by_outcome_and_the_mean_reward_by_eval(self):
        self.assertIn('```mermaid\npie showData\n    title Trials\n    "Solved" : 1\n    "Failed" : 1\n    "Error" : 1\n```', self.summary)
        self.assertIn('    x-axis ["claude-code / claude-opus-5-5 / example"]', self.summary)
        self.assertIn("    bar [0.500]", self.summary)

    def test_an_uploaded_job_gets_the_command_that_opens_it_in_the_dashboard(self):
        summary = run_report(AGENT_JOB, artifact="hbench-bench")[2]
        self.assertIn("View interactive dashboard by hbench:", summary)
        self.assertIn(
            "gh run download 123456 -R you/tasks -n hbench-bench -D hbench-jobs/agent-job && hbench view hbench-jobs",
            summary,
        )

    def test_a_job_that_is_not_uploaded_gets_no_dashboard_command(self):
        self.assertNotIn("View interactive dashboard", self.summary)

    def test_mean_reward_below_the_threshold_fails(self):
        self.assertEqual(run_report(AGENT_JOB, "0.6")[0], 1)
        self.assertEqual(run_report(AGENT_JOB, "0.5")[0], 0)


class OracleJobTest(unittest.TestCase):
    def test_reward_txt_mean_and_no_usage(self):
        status, outputs, summary = run_report(ORACLE_JOB, "1")
        self.assertEqual(status, 0)
        self.assertEqual(outputs["mean-reward"], "1.0")
        self.assertEqual(outputs["pass-rate"], "1.0")
        self.assertEqual(outputs["cost-usd"], "")
        self.assertIn("**1 / 1** (100.0%)", summary)
        self.assertIn("- **Agent** `oracle`", summary)
        self.assertIn("- **Tasks** `tasks`", summary)
        self.assertIn("✅ At or above min-mean-reward 1.", summary)
        self.assertNotIn("### Errors", summary)
        self.assertIn('    "Solved" : 1\n```', summary)
        self.assertNotIn('"Failed"', summary)
        self.assertNotIn('"Error"', summary)


if __name__ == "__main__":
    unittest.main()
