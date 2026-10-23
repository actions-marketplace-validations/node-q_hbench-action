"""Print the job_name a job config sets, or an empty line when it sets none.

Usage: config_job_name.py CONFIG

Reads the config as hbench run --config does: a .json file as JSON, any other as YAML. Without PyYAML, a YAML
config's job_name is read from its top-level job_name line.
"""

import json
import pathlib
import re
import sys

TOP_LEVEL_JOB_NAME = re.compile(r"""^(?:job_name|"job_name"|'job_name')[ \t]*:(?:[ \t]+(.*))?$""", re.MULTILINE)
DOUBLE_QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')
SINGLE_QUOTED = re.compile(r"'(?:[^']|'')*'")


def yaml_scalar(text):
    text = text.strip()
    if match := DOUBLE_QUOTED.match(text):
        return json.loads(match.group())
    if match := SINGLE_QUOTED.match(text):
        return match.group()[1:-1].replace("''", "'")
    plain = re.split(r"[ \t]#", text, maxsplit=1)[0].strip()
    return None if plain in ("", "~", "null", "Null", "NULL") else plain


def top_level_job_name(text):
    try:
        return json.loads(text)
    except ValueError:
        pass
    match = TOP_LEVEL_JOB_NAME.search(text)
    return {"job_name": yaml_scalar(match.group(1) or "")} if match else {}


def read_config(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    try:
        import yaml
    except ImportError:
        return top_level_job_name(text)
    return yaml.safe_load(text)


def job_name(config):
    name = config.get("job_name") if isinstance(config, dict) else None
    return name if isinstance(name, str) and name.strip() else ""


def main(arguments):
    path = pathlib.Path(arguments[0])
    try:
        config = read_config(path)
    except OSError as error:
        print(f"could not read {path}: {error.strerror}", file=sys.stderr)
        return 1
    except Exception as error:
        kind = "JSON" if path.suffix == ".json" else "YAML"
        detail = str(error).strip().splitlines()[0] if str(error).strip() else type(error).__name__
        print(f"{path} is not valid {kind}: {detail}", file=sys.stderr)
        return 1
    print(job_name(config))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
