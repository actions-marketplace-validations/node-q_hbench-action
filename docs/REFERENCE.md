# Reference

Every input and output of hbench-action, more examples, how it keeps your keys safe, and how to work on it.
The [README](../README.md) has the short version.

- [Inputs](#inputs)
- [Outputs](#outputs)
- [More examples](#more-examples)
- [Security](#security)
- [Development](#development)

## Inputs

| Input | Default | Description |
|---|---|---|
| `version` | `latest` | hbench release to install, such as v0.3.0, or latest. |
| `verify-provenance` | `auto` | Check the release archive's build provenance with gh attestation verify. true, false, or auto (when the GitHub CLI is installed). |
| `token` | `${{ github.token }}` | GitHub token for gh attestation verify. |
| `path` |  | A task directory, or a directory of task directories (hbench run --path). Set path, dataset or config to run; with none of them the action only installs hbench. |
| `dataset` |  | Dataset to run, name@version (hbench run --dataset). Needs registry. |
| `registry` |  | Where the dataset is listed. An OCI registry, oci://<registry>/<namespace>, or OCI image layouts on disk, oci-layout:<dir> (hbench run --registry); or a registry.json, by https:// URL (--registry-url) or path (--registry-path). |
| `config` |  | Job config, YAML or JSON (hbench run --config). The other inputs override it. |
| `agent` |  | Agent to run (hbench run --agent); hbench agents list shows them. Empty runs hbench's default, the oracle. |
| `model` |  | Model, as provider/name (hbench run --model). |
| `n-tasks` |  | Run at most this many tasks (hbench run --n-tasks). |
| `n-attempts` |  | Attempts per task (hbench run --n-attempts). |
| `n-concurrent` |  | Trials to run at once (hbench run --n-concurrent). |
| `include` |  | Only tasks whose names match these globs, one per line (hbench run --include-task-name). |
| `exclude` |  | Skip tasks whose names match these globs, one per line (hbench run --exclude-task-name). |
| `locked` | `false` | Refuse an OCI dataset that is not in hbench.lock, or whose tag now resolves to another digest (hbench run --locked). |
| `args` |  | More hbench run arguments, one per line, each line a whole argument. |
| `working-directory` | `.` | Directory to run hbench in. Relative paths and hbench.lock are read from it. |
| `jobs-dir` |  | Where hbench writes the job directory. Empty uses hbench-jobs under the runner's temporary directory. |
| `min-mean-reward` |  | Fail the step when the mean reward over every trial is below this number, from 0 to 1. Empty never fails on the score. |
| `upload-artifact` | `true` | Upload the job directory as a workflow artifact. |
| `artifact-name` |  | Name of the artifact. Empty uses hbench-<job id>-<time>-<random>; set it to something stable in a matrix. |
| `artifact-retention-days` |  | Days to keep the artifact. Empty uses the repository's setting. |

## Outputs

| Output | Description |
|---|---|
| `version` | The hbench release installed, such as v0.3.0. |
| `hbench-path` | Path of the installed hbench binary. |
| `job-dir` | The job directory hbench wrote. |
| `result-path` | The job's result.json. |
| `mean-reward` | Mean reward over every trial of every eval. |
| `n-trials` | Trials run. |
| `n-errors` | Trials that ended in an error. |
| `artifact-id` | ID of the uploaded artifact. |

`mean-reward` weighs each eval's mean reward by its trials. The job summary has a row per eval and lists the
trials below a reward of 1.

## More examples

Check every task in a repository with the oracle on each pull request, so a broken test or solution fails CI:

```yaml
name: Tasks
on: [pull_request]
jobs:
  oracle:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v7
      - uses: node-q/hbench-action@v1
        with:
          path: tasks
          n-concurrent: '4'
          min-mean-reward: '1'
```

Compare models on the same tasks, one job each, with stable artifact names:

```yaml
jobs:
  bench:
    runs-on: ubuntu-24.04
    strategy:
      matrix:
        model: [anthropic/claude-opus-5-5, openai/gpt-5]
    steps:
      - uses: node-q/hbench-action@v1
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        with:
          dataset: humaneval-plus@1.0
          registry: oci://ghcr.io/node-q/hbench-datasets
          agent: terminus-2
          model: ${{ matrix.model }}
          n-concurrent: '4'
          artifact-name: hbench-${{ strategy.job-index }}
```

Run the same bytes every time: record the dataset's manifest digest once with `--lock-write`, commit
`hbench.lock`, and run with `locked`, which refuses a dataset whose tag has moved:

```yaml
- uses: actions/checkout@v7
- uses: node-q/hbench-action@v1
  with:
    dataset: terminal-bench@2.0.1
    registry: oci://ghcr.io/node-q/hbench-datasets
    locked: 'true'          # reads ./hbench.lock from working-directory
```

Run a dataset listed in a `registry.json`, by path or by https:// URL. A task with `git_url` is checked out at
`git_commit_id`; one without is read from `working-directory`:

```yaml
- uses: actions/checkout@v7
- uses: node-q/hbench-action@v1
  with:
    dataset: my-tasks@1.0
    registry: registry.json   # or https://raw.githubusercontent.com/you/tasks/<commit>/registry.json
```

Install only, then call hbench yourself:

```yaml
- uses: node-q/hbench-action@v1
  id: hbench
  with:
    version: v0.3.0
- run: hbench tasks check --path tasks
```

Pass any other `hbench run` flag through `args`, one argument per line:

```yaml
- uses: node-q/hbench-action@v1
  with:
    path: tasks
    args: |
      --timeout-multiplier
      2
      --fail-on-error
```

## Security

- **The install is checked.** The archive must match the release's `SHA256SUMS`, and `gh attestation verify`
  checks that node-q/hbench's release workflow built it on a GitHub-hosted runner, from the tag. GitHub's
  runners have `gh`; on a runner without it, `verify-provenance: auto` skips that check with a warning and
  `true` fails.
- **Secrets stay out of the job directory.** hbench replaces the values of environment variables that look
  like secrets (`*_KEY`, `*TOKEN`, `*SECRET*`, `*PASSWORD*`, `*CREDENTIAL*`, `*AUTH*`) with `[REDACTED]` in
  every file it writes. The artifact still holds the agents' trajectories and outputs, and anyone with read
  access to the repository can download it: set `upload-artifact: 'false'` when they should not.
- **Inputs never become shell code.** Every input reaches the scripts as an environment variable, and `args`
  is split by lines only.
- **Pull requests from forks get no secrets.** Don't work around that with `pull_request_target`: it would run
  the fork's tasks with your keys.
- Pin the action to a full commit SHA for the strictest supply chain, as with any action:
  `uses: node-q/hbench-action@<sha> # v1.0.0`.

## Development

```text
action.yml          the inputs, outputs and three steps: install, run, upload
scripts/install.sh  download, checksum, provenance, tool cache
scripts/run.sh      build the hbench run command line, run it, report
scripts/report.py   result.json to outputs, job summary and the threshold
tests/tasks/        a one-task folder the tests run
```

`.github/workflows/test.yml` runs on GitHub-hosted runners only: actionlint and shellcheck; installing
`latest` and a pinned release on Linux x86_64 and arm64 and macOS arm64 and x86_64, with provenance checked;
the oracle on the local task with `min-mean-reward: '1'`; the `nop` agent, which must fail the step on its
score; two tasks of an OCI dataset with `--lock-write`; and a dataset listed in a `registry.json`, by path and
by URL.

To try the scripts outside GitHub, set the variables the runner sets (`RUNNER_TEMP`, `GITHUB_ACTION_PATH`,
`GITHUB_OUTPUT`, `GITHUB_PATH`, `GITHUB_STEP_SUMMARY`) and the `INPUT_*` ones `action.yml` passes, then run
`scripts/install.sh` and `scripts/run.sh`.

Releases are tagged `vX.Y.Z`, and the major tag `vX` moves to the latest of them. See
[RELEASING.md](RELEASING.md).
