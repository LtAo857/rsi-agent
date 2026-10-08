import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rsi import compare, evaluate, guard
from rsi.runner import BudgetExceeded, Tools
from rsi.llm import load_env


def agent(name):
    path = compare.ROOT / "baselines" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeTools:
    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.prompts = []

    @property
    def calls_left(self):
        return len(self.candidates)

    def llm(self, messages, **kwargs):
        self.prompts.append(str(messages))
        return self.candidates.pop(0)

    def run_tests(self, code):
        passed = {"bad": 0, "partial": 1, "good": 2, "tie": 2}[code]
        return {"passed": passed, "total": 2,
                "failures": [] if passed == 2 else [{"test": "visible example", "error": "example failed"}]}


class BaselineTests(unittest.TestCase):
    def test_env_loading_preserves_overrides_and_literal_values(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {"AGENT_MODEL": "override"}, clear=True):
            p = Path(d) / ".env"
            p.write_text("# config\nexport AGENT_MODEL=from-file\nLLM_API_KEY='literal-$value' # comment\nEMPTY=\n")
            load_env(p)
            self.assertEqual(os.environ["AGENT_MODEL"], "override")
            self.assertEqual(os.environ["LLM_API_KEY"], "literal-$value")
            self.assertEqual(os.environ["EMPTY"], "")

    def test_invalid_env_does_not_echo_value(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text("LLM_API_KEY='private-value\n")
            with self.assertRaises(ValueError) as error:
                load_env(p)
            self.assertNotIn("private-value", str(error.exception))

    def test_baselines_pass_guard(self):
        for name in ("repair", "best_of_n"):
            self.assertIsNone(guard.check((compare.ROOT / "baselines" / f"{name}.py").read_text()))

    def test_repair_feedback_and_early_stop(self):
        tools = FakeTools(["bad", "good", "bad"])
        self.assertEqual(agent("repair").solve({"prompt": "task"}, tools), "good")
        self.assertEqual(tools.calls_left, 1)
        self.assertIn("example failed", tools.prompts[1])

    def test_repair_retains_best_after_regression(self):
        tools = FakeTools(["partial", "bad"])
        self.assertEqual(agent("repair").solve({"prompt": "task"}, tools), "partial")

    def test_best_of_n_uses_budget_and_stable_tie(self):
        tools = FakeTools(["bad", "good", "tie"])
        self.assertEqual(agent("best_of_n").solve({"prompt": "task"}, tools), "good")
        self.assertEqual(tools.calls_left, 0)
        self.assertTrue(all(p == tools.prompts[0] for p in tools.prompts))

    def test_budget_enforced(self):
        tools = Tools({}, 1)
        with patch("rsi.runner.llm.chat", return_value=("code", 7)) as chat:
            tools.llm("task")
            with self.assertRaises(BudgetExceeded):
                tools.llm("task")
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(tools.tokens, 7)

    def test_caught_api_failure_remains_visible(self):
        tools = Tools({}, 1)
        with patch("rsi.runner.llm.chat", side_effect=ConnectionError("offline")):
            with self.assertRaises(ConnectionError):
                tools.llm("task")
        self.assertEqual(tools.llm_errors, ["ConnectionError"])

    def test_evaluator_passes_budget_but_no_hidden_tests(self):
        task = {"id": "test", "prompt": "task", "entry": "f", "visible": ["visible"], "hidden": ["secret"]}
        reply = {"code": "answer", "error": None, "llm_calls": 2, "tokens": 10, "log": []}
        process = SimpleNamespace(stdout=evaluate.RESULT_MARK + json.dumps(reply), stderr="")
        with patch("rsi.evaluate.subprocess.run", return_value=process) as run, \
                patch("rsi.evaluate.sandbox.run_tests", return_value={"passed": 2, "total": 2, "failures": []}) as test:
            result = evaluate.run_one(Path("agent.py"), task, max_calls=4)
        request = json.loads(run.call_args.kwargs["input"])
        self.assertEqual(request["max_calls"], 4)
        self.assertNotIn("secret", run.call_args.kwargs["input"])
        self.assertEqual(test.call_args.args[1], ["visible", "secret"])
        self.assertTrue(result["solved"])

    def test_selection_uses_confirmed_development_scores(self):
        def node(i, score, confirmed):
            ev = {"score": score, "test_rate": score, "llm_calls": 1}
            return {"id": i, "status": "ok", "eval": ev, "eval_mean": ev if confirmed else None}
        self.assertEqual(compare.select_best([node(0, .4, True), node(1, .9, False), node(2, .6, True)])["id"], 2)

    def test_paired_results_use_task_ids(self):
        data = {"config": {"budgets": [4], "repeats": 1}, "records": [
            {"budget": 4, "strategy": "evolved", "repeat": 0, "eval": {"results": [
                {"task": "a", "solved": True}, {"task": "b", "solved": False}]}},
            {"budget": 4, "strategy": "repair", "repeat": 0, "eval": {"results": [
                {"task": "b", "solved": False}, {"task": "a", "solved": False}]}}]}
        pair = compare.paired_deltas(data)[0]
        self.assertEqual((pair["wins"], pair["losses"], pair["ties"], pair["score_delta"]), (1, 0, 1, .5))


if __name__ == "__main__":
    unittest.main()
