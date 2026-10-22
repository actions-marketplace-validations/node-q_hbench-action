```text
██╗  ██╗██████╗ ███████╗███╗   ██╗ ██████╗██╗  ██╗
██║  ██║██╔══██╗██╔════╝████╗  ██║██╔════╝██║  ██║
███████║██████╔╝█████╗  ██╔██╗ ██║██║     ███████║
██╔══██║██╔══██╗██╔══╝  ██║╚██╗██║██║     ██╔══██║
██║  ██║██████╔╝███████╗██║ ╚████║╚██████╗██║  ██║
╚═╝  ╚═╝╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝

 █████╗  ██████╗████████╗██╗ ██████╗ ███╗   ██╗
██╔══██╗██╔════╝╚══██╔══╝██║██╔═══██╗████╗  ██║
███████║██║        ██║   ██║██║   ██║██╔██╗ ██║
██╔══██║██║        ██║   ██║██║   ██║██║╚██╗██║
██║  ██║╚██████╗   ██║   ██║╚██████╔╝██║ ╚████║
╚═╝  ╚═╝ ╚═════╝   ╚═╝   ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
```

# hbench-action

A GitHub Action for [hbench](https://github.com/node-q/hbench), the benchmark engine behind
[Harness Playground](https://nodeq.tech), by node-q.

Run coding agents (Claude Code, Codex, Gemini CLI and more) on benchmark tasks in your workflows, and see how
many they solve in the job summary.

- [Installation](#installation)
- [Quick start](#quick-start)
- [Docs](#docs)
- [Usage](#usage)
- [Agents](#agents)
- [License](#license)
- [Contributors and contact](#contributors-and-contact)

## Installation

You need a Linux runner with Docker. GitHub's `ubuntu-*` runners have it.

```yaml
- uses: node-q/hbench-action@v1
```

The action installs hbench and checks its checksum and build provenance before it runs.

## Quick start

Check every task in your repository with the oracle, which runs each task's reference solution, on each
pull request:

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
          min-mean-reward: 1
```

To run Claude Code instead, add your Anthropic key as a repository secret and pass it in `env`:

```yaml
      - uses: node-q/hbench-action@v1
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        with:
          dataset: terminal-bench@2.0.1
          registry: oci://ghcr.io/node-q/hbench-datasets
          agent: claude-code
          model: anthropic/claude-opus-5-5
          n-tasks: 5
```

The scores go to the job summary, and the job's files are uploaded as an artifact.

## Docs

Every input and output, more examples and the security notes are in [docs/REFERENCE.md](docs/REFERENCE.md).
For hbench itself, the docs are at [nodeq.tech/docs](https://nodeq.tech/docs):

- [Agents](https://nodeq.tech/docs/reference/agents) and the [hbench command line](https://nodeq.tech/docs/reference/hbench-cli)
- [Read your result](https://nodeq.tech/docs/get-started/read-your-result)
- [Troubleshooting](https://nodeq.tech/docs/troubleshooting)

## Usage

```yaml
- uses: node-q/hbench-action@v1
  with:
    # What to run: one of these
    path: tasks                                   # a local task, or a folder of tasks
    # dataset: terminal-bench@2.0.1               # or a dataset, with its registry
    # registry: oci://ghcr.io/node-q/hbench-datasets
    # config: job.yaml                            # or a job config (YAML/JSON)

    # Who runs it
    agent: claude-code                            # default: oracle
    model: anthropic/claude-opus-5-5

    # How much
    n-tasks: 5                                    # only 5 tasks
    n-attempts: 3                                 # each task 3 times
    n-concurrent: 4                               # 4 at a time

    # When it fails
    min-mean-reward: 0.8                          # fail the step below this mean reward
```

With none of `path`, `dataset` or `config`, the action only installs hbench, and later steps can call
`hbench` themselves. Useful outputs: `mean-reward`, `n-trials`, `n-errors` and `job-dir`.

## Agents

Each agent reads its key from the environment, so pass it in the step's `env` from a secret.

| Agent | What it runs | Example model (`model`) | Key |
|---|---|---|---|
| `claude-code` | Claude Code | `anthropic/claude-opus-5-5` | `ANTHROPIC_API_KEY` |
| `codex` | OpenAI Codex CLI | `openai/gpt-5` | `OPENAI_API_KEY` |
| `gemini-cli` | Google Gemini CLI | `google/gemini-3-pro` | `GEMINI_API_KEY` |
| `deepseek-harness` | DeepSeek's harness ([dsh](https://github.com/deepseek-ai/deepseek-harness)) | `deepseek/deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| `oracle` | Each task's reference solution, to check the tasks | | |
| … and a lot more | [hbench's agent list](https://github.com/node-q/hbench#agents) | | |

## License

Apache-2.0. See [LICENSE](LICENSE).

## Contributors and contact

hbench-action is built and maintained by [node-q](https://nodeq.tech). See the
[contributors graph](https://github.com/node-q/hbench-action/graphs/contributors) for everyone who has
contributed.

Report bugs and request features in [GitHub issues](https://github.com/node-q/hbench-action/issues); for hbench
itself, use [node-q/hbench's issues](https://github.com/node-q/hbench/issues). The full reference is in
[docs/REFERENCE.md](docs/REFERENCE.md); to release, see [docs/RELEASING.md](docs/RELEASING.md).
