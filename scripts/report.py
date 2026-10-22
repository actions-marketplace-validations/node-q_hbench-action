"""Write a job's results to the step's outputs and summary, and check them against min-mean-reward.

Usage: report.py RESULT_JSON

Reads hbench's result.json, and beside it the job's config.json and lock.json and each trial's result.json.
A trial is solved when its reward is 1. Each eval (agent, model and tasks) gets a row: solved trials and the
pass rate, mean reward, pass@k, errors, agent time, tokens and cost. Below come what ran (hbench, agent,
model, tasks and digest), the tasks' own metrics, the errors by type, and a row per trial, errors and
failures first. mean-reward is the trial-weighted mean of the evals' mean rewards, as hbench computes them
(a task's reward.json `reward`, or its reward.txt). Exits 1 when INPUT_MIN_MEAN_REWARD is set and
mean-reward is below it.
"""

import datetime
import json
import os
import pathlib
import re
import statistics
import sys

LISTED_TRIALS = 500
PRIMARY_METRICS = ("reward", "mean")


def numeric(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def timestamp(value):
    if not isinstance(value, str):
        return None
    trimmed = re.sub(r"(\.\d{6})\d+", r"\1", value).replace("Z", "+00:00")
    try:
        return datetime.datetime.fromisoformat(trimmed)
    except ValueError:
        return None


def seconds_between(span):
    if not isinstance(span, dict):
        return None
    started, finished = timestamp(span.get("started_at")), timestamp(span.get("finished_at"))
    return (finished - started).total_seconds() if started and finished else None


def read_json(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError):
        return {}


def eval_key(trial):
    agent = (trial.get("agent_info") or {}).get("name") or "agent"
    model = ((trial.get("agent_info") or {}).get("model_info") or {}).get("name")
    source = trial.get("source") or "tasks"
    return "__".join(part for part in (agent, model, source) if part)


def load_trials(job_directory):
    trials = []
    for result_path in sorted(pathlib.Path(job_directory).glob("*/result.json")):
        result = read_json(result_path)
        if "trial_name" not in result:
            continue
        rewards = (result.get("verifier_result") or {}).get("rewards") or {}
        usage = result.get("agent_result") or {}
        exception = result.get("exception_info") or {}
        trials.append(
            {
                "eval": eval_key(result),
                "task": result.get("task_name") or result["trial_name"],
                "trial": result["trial_name"],
                "reward": numeric(rewards.get("reward")),
                "error": exception.get("exception_type"),
                "agent_seconds": seconds_between(result.get("agent_execution")),
                "input_tokens": usage.get("n_input_tokens"),
                "cache_tokens": usage.get("n_cache_tokens"),
                "output_tokens": usage.get("n_output_tokens"),
                "cost": numeric(usage.get("cost_usd")),
            }
        )
    return trials


def solved(trial):
    return trial["error"] is None and trial["reward"] is not None and trial["reward"] >= 1.0


def total(values):
    present = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return sum(present) if present else None


def eval_rows(stats, trials):
    evals = stats.get("evals") or {}
    rows = []
    for name, entry in sorted(evals.items()):
        metrics = (entry.get("metrics") or [{}])[0]
        mine = [trial for trial in trials if trial["eval"] == name]
        if not mine and len(evals) == 1:
            mine = trials
        agent_times = [trial["agent_seconds"] for trial in mine if trial["agent_seconds"] is not None]
        n_solved = sum(1 for trial in mine if solved(trial))
        cost = total(trial["cost"] for trial in mine)
        rows.append(
            {
                "name": name,
                "trials": entry.get("n_trials") or len(mine),
                "errors": entry.get("n_errors") or 0,
                "mean": numeric(metrics.get("reward", metrics.get("mean"))),
                "other_metrics": {
                    key: numeric(value)
                    for key, value in sorted(metrics.items())
                    if key not in PRIMARY_METRICS and numeric(value) is not None
                },
                "pass_at_k": {k: numeric(v) for k, v in sorted((entry.get("pass_at_k") or {}).items())},
                "exceptions": {kind: sorted(names) for kind, names in sorted((entry.get("exception_stats") or {}).items())},
                "solved": n_solved,
                "graded": len(mine),
                "agent_total": sum(agent_times) if agent_times else None,
                "agent_median": statistics.median(agent_times) if agent_times else None,
                "input_tokens": total(trial["input_tokens"] for trial in mine),
                "cache_tokens": total(trial["cache_tokens"] for trial in mine),
                "output_tokens": total(trial["output_tokens"] for trial in mine),
                "cost": cost,
                "cost_per_solved": cost / n_solved if cost is not None and n_solved else None,
            }
        )
    return rows


def overall_mean(rows):
    weighted = [(row["mean"], row["trials"]) for row in rows if row["mean"] is not None and row["trials"]]
    trials = sum(count for _, count in weighted)
    return sum(mean * count for mean, count in weighted) / trials if trials else None


def score(value, digits=3):
    return "–" if value is None else f"{value:.{digits}f}"


def duration(seconds):
    if seconds is None:
        return "–"
    seconds = round(seconds)
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def tokens(count):
    if count is None:
        return "–"
    for limit, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if count >= limit:
            return f"{count / limit:.1f}{suffix}"
    return str(count)


def dollars(amount):
    if amount is None:
        return "–"
    return f"${amount:.2f}" if amount >= 1 else f"${amount:.4f}"


def percent(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else "–"


def scorecard(rows):
    lines = [
        "| Eval | Solved | Mean reward | pass@k | Errors | Agent time | Tokens in / out | Cost |",
        "|---|---:|---:|---|---:|---|---|---|",
    ]
    for row in rows:
        pass_at_k = ", ".join(f"@{k} {score(v)}" for k, v in row["pass_at_k"].items()) or "–"
        agent_time = "–"
        if row["agent_total"] is not None:
            agent_time = f"{duration(row['agent_total'])} total, {duration(row['agent_median'])} median"
        token_text = "–"
        if row["input_tokens"] is not None or row["output_tokens"] is not None:
            token_text = f"{tokens(row['input_tokens'])} / {tokens(row['output_tokens'])}"
            if row["cache_tokens"]:
                token_text += f" ({tokens(row['cache_tokens'])} cached)"
        cost_text = dollars(row["cost"])
        if row["cost_per_solved"] is not None:
            cost_text += f" ({dollars(row['cost_per_solved'])} per solved)"
        lines.append(
            f"| `{row['name']}` | **{row['solved']} / {row['trials']}** ({percent(row['solved'], row['trials'])}) "
            f"| {score(row['mean'])} | {pass_at_k} | {row['errors']} | {agent_time} | {token_text} | {cost_text} |"
        )
    return lines


def shown_path(path):
    absolute, here = os.path.abspath(path), os.getcwd()
    return os.path.relpath(absolute, here) if os.path.commonpath([absolute, here]) == here else path


def run_details(result, config, lock):
    hbench = lock.get("hbench") or {}
    lines = []
    if hbench.get("version"):
        epoch = f", results epoch {hbench['results_epoch']}" if hbench.get("results_epoch") else ""
        lines.append(f"- **hbench** {hbench['version']}{epoch}")
    for agent in config.get("agents") or []:
        model = f", model `{agent['model_name']}`" if agent.get("model_name") else ""
        lines.append(f"- **Agent** `{agent.get('name') or 'oracle'}`{model}")
    for dataset in config.get("datasets") or []:
        if dataset.get("name"):
            where = dataset.get("registry") or dataset.get("registry_url") or dataset.get("registry_path")
            label = f"`{dataset['name']}@{dataset['version']}`" if dataset.get("version") else f"`{dataset['name']}`"
            lines.append(
                f"- **Tasks** {label}"
                + (f" from `{where}`" if where else "")
                + (f", manifest `{dataset['digest']}`" if dataset.get("digest") else "")
            )
        elif dataset.get("path"):
            lines.append(f"- **Tasks** `{shown_path(dataset['path'])}`")
    attempts = config.get("n_attempts") or 1
    concurrent = lock.get("n_concurrent_trials") or config.get("n_concurrent_trials")
    lines.append(f"- **Attempts** {attempts} per task" + (f", {concurrent} at a time" if concurrent else ""))
    started, finished = timestamp(result.get("started_at")), timestamp(result.get("finished_at"))
    if started and finished:
        lines.append(
            f"- **Ran** {started:%Y-%m-%d %H:%M} to {finished:%H:%M} UTC, "
            f"{duration((finished - started).total_seconds())}"
        )
    return lines


def trial_table(trials):
    def order(trial):
        return (0 if trial["error"] else 1 if not solved(trial) else 2, trial["task"], trial["trial"])

    ordered = sorted(trials, key=order)
    shown = ordered[:LISTED_TRIALS]
    lines = [
        "| Task | Result | Reward | Agent time | Tokens in / out | Cost |",
        "|---|---|---:|---|---|---|",
    ]
    for trial in shown:
        result = f"⚠️ {trial['error']}" if trial["error"] else "✅ solved" if solved(trial) else "❌ failed"
        token_text = "–"
        if trial["input_tokens"] is not None or trial["output_tokens"] is not None:
            token_text = f"{tokens(trial['input_tokens'])} / {tokens(trial['output_tokens'])}"
        lines.append(
            f"| `{trial['task']}` | {result} | {score(trial['reward'])} | {duration(trial['agent_seconds'])} "
            f"| {token_text} | {dollars(trial['cost'])} |"
        )
    if len(ordered) > len(shown):
        lines.append(f"| and {len(ordered) - len(shown)} more | | | | | |")
    return lines


def summary(result, config, lock, rows, trials, mean, threshold):
    n_trials = sum(row["trials"] for row in rows)
    n_solved = sum(row["solved"] for row in rows)
    lines = ["## Harness Benchmark", "", *scorecard(rows), ""]
    verdict = (
        f"**{n_solved} of {n_trials}** trials solved ({percent(n_solved, n_trials)}), mean reward **{score(mean)}**."
    )
    if threshold is not None:
        passed = mean is not None and mean >= threshold
        verdict += f" {'✅ At or above' if passed else '❌ Below'} min-mean-reward {threshold:g}."
    lines += [verdict, "", "### What ran", "", *run_details(result, config, lock)]
    for row in rows:
        if row["other_metrics"]:
            metrics = ", ".join(f"`{key}` {score(value)}" for key, value in row["other_metrics"].items())
            lines += ["", f"The tasks' own metrics for `{row['name']}`, as means over its trials: {metrics}."]
    errors = [(row["name"], kind, names) for row in rows for kind, names in row["exceptions"].items()]
    if errors:
        lines += ["", "### Errors", ""]
        for name, kind, names in errors:
            shown = ", ".join(f"`{trial}`" for trial in names[:10])
            more = f" and {len(names) - 10} more" if len(names) > 10 else ""
            lines.append(f"- **{kind}** in `{name}`: {len(names)} ({shown}{more})")
    if trials:
        lines += [
            "",
            f"<details><summary>{len(trials)} trials, errors and failures first</summary>",
            "",
            *trial_table(trials),
            "",
            "</details>",
        ]
    return "\n".join(lines) + "\n"


def append(path_variable, content):
    path = os.environ.get(path_variable)
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(content)


def main(arguments):
    if len(arguments) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    result_path = pathlib.Path(arguments[0])
    result = read_json(result_path)
    job_directory = result_path.parent
    config, lock = read_json(job_directory / "config.json"), read_json(job_directory / "lock.json")
    trials = load_trials(job_directory)
    rows = eval_rows(result.get("stats") or {}, trials)
    mean = overall_mean(rows)
    threshold = numeric(os.environ.get("INPUT_MIN_MEAN_REWARD") or None)
    n_trials = sum(row["trials"] for row in rows)
    n_solved = sum(row["solved"] for row in rows)
    cost = total(row["cost"] for row in rows)
    append(
        "GITHUB_OUTPUT",
        f"result-path={result_path}\n"
        f"mean-reward={'' if mean is None else round(mean, 6)}\n"
        f"n-trials={n_trials}\n"
        f"n-errors={sum(row['errors'] for row in rows)}\n"
        f"n-solved={n_solved}\n"
        f"pass-rate={round(n_solved / n_trials, 6) if n_trials else ''}\n"
        f"cost-usd={'' if cost is None else round(cost, 6)}\n",
    )
    report = summary(result, config, lock, rows, trials, mean, threshold)
    append("GITHUB_STEP_SUMMARY", report)
    print(report)
    if threshold is not None and (mean is None or mean < threshold):
        print(f"::error title=hbench::Mean reward {score(mean)} is below min-mean-reward {threshold:g}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
