"""Write a job's scores to the step's outputs and summary, and check them against min-mean-reward.

Usage: report.py RESULT_JSON

Reads hbench's result.json. Each eval (agent, model and dataset) gets a row with its trials, errors, mean
reward and pass@k; the trials that did not reach a reward of 1 are listed below. An eval's mean reward is
its first metric's `reward` (a task's reward.json) or `mean` (a task's reward.txt). mean-reward is the mean
over every trial of every eval. Exits 1 when INPUT_MIN_MEAN_REWARD is set and mean-reward is below it.
"""

import json
import os
import sys

LISTED_TRIALS = 50


def numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def eval_rows(stats):
    rows = []
    for name, entry in sorted((stats.get("evals") or {}).items()):
        metrics = entry.get("metrics") or [{}]
        rewards = (entry.get("reward_stats") or {}).get("reward") or {}
        below_one = sorted(
            trial for value, trials in rewards.items() if (numeric(value) or 0.0) < 1.0 for trial in trials
        )
        rows.append(
            {
                "name": name,
                "trials": entry.get("n_trials") or 0,
                "errors": entry.get("n_errors") or 0,
                "mean": numeric(metrics[0].get("reward", metrics[0].get("mean"))),
                "pass_at_k": entry.get("pass_at_k") or {},
                "below_one": below_one,
            }
        )
    return rows


def overall_mean(rows):
    weighted = [(row["mean"], row["trials"]) for row in rows if row["mean"] is not None and row["trials"]]
    trials = sum(count for _, count in weighted)
    return sum(mean * count for mean, count in weighted) / trials if trials else None


def text(value, digits=3):
    return "–" if value is None else f"{value:.{digits}f}"


def summary(result, rows, mean, threshold):
    stats = result.get("stats") or {}
    lines = [
        "## hbench",
        "",
        "| Eval | Trials | Errors | Mean reward | pass@k |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        pass_at_k = ", ".join(f"pass@{k} {text(numeric(v))}" for k, v in sorted(row["pass_at_k"].items())) or "–"
        lines.append(f"| `{row['name']}` | {row['trials']} | {row['errors']} | {text(row['mean'])} | {pass_at_k} |")
    lines.append("")
    verdict = f"Mean reward **{text(mean)}** over {sum(row['trials'] for row in rows)} trials"
    if threshold is not None:
        verdict += f", {'at or above' if mean is not None and mean >= threshold else 'below'} min-mean-reward {threshold:g}"
    lines.append(verdict + ".")
    tokens = [
        f"{label} {stats[key]:,}"
        for key, label in (("n_input_tokens", "input"), ("n_cache_tokens", "cached"), ("n_output_tokens", "output"))
        if isinstance(stats.get(key), int)
    ]
    if tokens:
        lines.append(f"Tokens: {', '.join(tokens)}.")
    if isinstance(stats.get("cost_usd"), (int, float)):
        lines.append(f"Cost: ${stats['cost_usd']:.4f}.")
    for row in rows:
        if row["below_one"]:
            shown = row["below_one"][:LISTED_TRIALS]
            more = len(row["below_one"]) - len(shown)
            lines += [
                "",
                f"<details><summary>{len(row['below_one'])} trials of <code>{row['name']}</code> below a reward of 1</summary>",
                "",
                *[f"- `{trial}`" for trial in shown],
                *([f"- and {more} more"] if more > 0 else []),
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
    with open(arguments[0], encoding="utf-8") as stream:
        result = json.load(stream)
    rows = eval_rows(result.get("stats") or {})
    mean = overall_mean(rows)
    threshold = numeric(os.environ.get("INPUT_MIN_MEAN_REWARD") or None)
    append(
        "GITHUB_OUTPUT",
        f"result-path={arguments[0]}\n"
        f"mean-reward={'' if mean is None else round(mean, 6)}\n"
        f"n-trials={sum(row['trials'] for row in rows)}\n"
        f"n-errors={sum(row['errors'] for row in rows)}\n",
    )
    report = summary(result, rows, mean, threshold)
    append("GITHUB_STEP_SUMMARY", report)
    print(report)
    if threshold is not None and (mean is None or mean < threshold):
        print(f"::error title=hbench::Mean reward {text(mean)} is below min-mean-reward {threshold:g}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
