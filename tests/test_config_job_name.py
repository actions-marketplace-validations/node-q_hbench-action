import contextlib
import importlib.util
import io
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import config_job_name  # noqa: E402

HAS_PYYAML = importlib.util.find_spec("yaml") is not None


def job_name_of(text, suffix):
    with tempfile.TemporaryDirectory() as directory:
        path = pathlib.Path(directory, "config" + suffix)
        path.write_text(text, encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            status = config_job_name.main([str(path)])
        return status, output.getvalue()


class JsonConfigTest(unittest.TestCase):
    def test_a_spec_names_its_job(self):
        spec = '{\n  "job_name": "spec-7f3a",\n  "datasets": [{"name": "hello", "version": "1.0"}]\n}\n'
        self.assertEqual(job_name_of(spec, ".json"), (0, "spec-7f3a\n"))

    def test_a_config_without_job_name_names_none(self):
        self.assertEqual(job_name_of('{"tasks": [{"path": "tasks"}]}', ".json"), (0, "\n"))

    def test_an_empty_or_null_job_name_names_none(self):
        self.assertEqual(job_name_of('{"job_name": ""}', ".json"), (0, "\n"))
        self.assertEqual(job_name_of('{"job_name": null}', ".json"), (0, "\n"))

    def test_invalid_json_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory, "spec.json")
            path.write_text("job_name: not-json", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(config_job_name.main([str(path)]), 1)
        self.assertEqual(error.getvalue(), f"{path} is not valid JSON: Expecting value: line 1 column 1 (char 0)\n")

    def test_a_missing_config_fails(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(config_job_name.main(["/nonexistent/config.json"]), 1)
        self.assertEqual(error.getvalue(), "could not read /nonexistent/config.json: No such file or directory\n")


class YamlWithoutPyyamlTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(sys.modules, {"yaml": None})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_plain_job_name(self):
        self.assertEqual(job_name_of("tasks:\n  - path: tasks\njob_name: nightly\n", ".yaml"), (0, "nightly\n"))

    def test_quoted_job_names_and_comments(self):
        self.assertEqual(job_name_of('job_name: "a # b"  # the name\n', ".yml"), (0, "a # b\n"))
        self.assertEqual(job_name_of("job_name: 'it''s'\n", ".yml"), (0, "it's\n"))
        self.assertEqual(job_name_of("job_name: nightly # the name\n", ".yml"), (0, "nightly\n"))
        self.assertEqual(job_name_of('"job_name": nightly\n', ".yml"), (0, "nightly\n"))

    def test_a_null_or_nested_job_name_names_none(self):
        self.assertEqual(job_name_of("job_name:\nn_attempts: 2\n", ".yaml"), (0, "\n"))
        self.assertEqual(job_name_of("job_name: ~\n", ".yaml"), (0, "\n"))
        self.assertEqual(job_name_of("agents:\n  - name: oracle\n    job_name: x\n", ".yaml"), (0, "\n"))

    def test_json_in_a_yaml_file(self):
        self.assertEqual(job_name_of('{\n  "job_name": "spec-7f3a"\n}\n', ".yaml"), (0, "spec-7f3a\n"))


@unittest.skipUnless(HAS_PYYAML, "PyYAML is not installed")
class YamlWithPyyamlTest(unittest.TestCase):
    def test_a_job_name_in_any_yaml_style(self):
        self.assertEqual(job_name_of("job_name: nightly\n", ".yaml"), (0, "nightly\n"))
        self.assertEqual(job_name_of("{job_name: nightly, n_attempts: 2}\n", ".yaml"), (0, "nightly\n"))
        self.assertEqual(job_name_of("agents:\n  - job_name: x\n", ".yaml"), (0, "\n"))


if __name__ == "__main__":
    unittest.main()
