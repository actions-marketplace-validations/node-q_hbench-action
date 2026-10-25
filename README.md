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

The scores go to the job summary, and the job's files are uploaded as an artifact. `n-tasks: 5` runs 5 of the
dataset's 89 tasks; leave it out to run them all. A score compares only with runs of the same tasks: the same
dataset and version from the same registry, with the same `n-tasks`, `include` and `exclude`. To run a job
spec you were given, under the job name it sets, pass it as `config` alone (see
[Run a job spec](docs/REFERENCE.md#more-examples)).

For a whole repository to fork, with three tasks, the workflow that checks them on every pull request and
workflows that run agents on them, see
[node-q/hbench-action-example](https://github.com/node-q/hbench-action-example).

## Docs

Every input and output, more examples and the security notes are in [docs/REFERENCE.md](docs/REFERENCE.md),
and a working repository is at [node-q/hbench-action-example](https://github.com/node-q/hbench-action-example).
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
    # dataset: terminal-bench@2.0.1               # or a dataset from an OCI registry
    # registry: oci://ghcr.io/node-q/hbench-datasets
    # dataset: my-tasks@1.0                       # or a dataset listed in a registry.json
    # registry: registry.json                     #   a path, or an https:// URL
    # config: job.yaml                            # or a job config (YAML/JSON), run under its job_name

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
`hbench` themselves. Useful outputs: `pass-rate`, `n-solved`, `mean-reward`, `cost-usd` and `job-dir`.

The job summary shows, for each agent and model, how many tasks it solved, its mean reward and pass@k, its
errors, the time it spent, its tokens and its cost per solved task; the trials by outcome and each eval's
mean reward, each with a bar; the command that opens the job in
hbench's interactive dashboard on your machine; what ran (the hbench release, the agent, the model, the tasks
and their digest); the errors by type; and a row per task.

A `registry.json` lists datasets and where each of their tasks is: a git repository at a commit, or a folder
in your repository, read from `working-directory`:

```json
[
  {
    "name": "my-tasks",
    "version": "1.0",
    "description": "Tasks from our own codebase",
    "tasks": [
      { "name": "fix-the-parser", "git_url": "https://github.com/you/tasks.git",
        "git_commit_id": "<full commit SHA>", "path": "fix-the-parser" },
      { "name": "hello-world", "path": "tasks/hello-world" }
    ]
  }
]
```

Run one of its datasets by the file's path, or by its https:// URL:

```yaml
- uses: actions/checkout@v7
- uses: node-q/hbench-action@v1
  with:
    dataset: my-tasks@1.0
    registry: registry.json       # or https://raw.githubusercontent.com/you/tasks/<commit>/registry.json
    agent: oracle
```

On your machine, the same run is `hbench run -d my-tasks@1.0 --registry-path registry.json -a oracle`, or
`--registry-url <https URL>`.

## Agents

Each agent reads its key from the environment, so pass it in the step's `env` from a secret.

| Agent | What it runs | Example model (`model`) | Key |
|---|---|---|---|
| `claude-code` | Claude Code | `anthropic/claude-opus-5-5` | `ANTHROPIC_API_KEY` |
| `codex` | OpenAI Codex CLI | `openai/gpt-5` | `OPENAI_API_KEY` |
| `gemini-cli` | Google Gemini CLI | `google/gemini-3-pro` | `GEMINI_API_KEY` |
| `deepseek-harness` | DeepSeek's harness ([dsh](https://github.com/deepseek-ai/deepseek-harness)) | `deepseek/deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| `oracle` | Each task's reference solution, to check the tasks | | |
| … and 40 more | the lists below | | |

The action runs the agents and providers of the hbench release it installs. With hbench, that is 46
agents, and 51 providers for the agents that take any model. `hbench agents list` prints the agents of the
release you have.

<details><summary>All 46 agents</summary>

`oracle` runs each task's reference solution and `nop` does nothing; both check tasks. The other 44 are coding
agents:

`acp`, `aider`, `antigravity-cli`, `antigravity-sdk`, `claude-code`, `cline-cli`, `code-puppy`, `codex`,
`computer-1`, `copilot-cli`, `cortex-code`, `cursor-cli`, `deepseek-harness`, `deerflow`, `devin`, `dspy-rlm`,
`eve`, `fx`, `fx-dev`, `gemini-cli`, `goose`, `grok-build`, `hermes`, `junie`, `kimi-cli`, `kimi-code`,
`langgraph`, `mcode`, `mimo`, `mini-swe-agent`, `muse-code`, `nemo-agent`, `openclaw`, `opencode`,
`openhands`, `openhands-sdk`, `pi`, `qwen-coder`, `rovodev-cli`, `strands`, `swe-agent`, `terminus-2`,
`trae-agent`, `vibe`.

`terminus` and `terminus-1` are other names for `terminus-2`, and `acp:<id>` runs any agent that speaks the
Agent Client Protocol. Agents from a vendor, such as `claude-code`, `codex`, `gemini-cli` and
`deepseek-harness`, sign in to that vendor with its own key.

</details>

<details><summary>All 51 providers</summary>

Agents that take any model, such as `terminus-2`, `aider`, `opencode`, `goose`, `mini-swe-agent` and
`swe-agent`, name it as `provider/model` and read the provider's key, any one of those listed:

| Provider (`model` prefix) | Key |
|---|---|
| `ai21`, `ai21_chat` | `AI21_API_KEY` |
| `aleph_alpha` | `ALEPH_ALPHA_API_KEY` |
| `amazon-bedrock`, `sagemaker`, `bedrock` | `AWS_ACCESS_KEY_ID`, with `AWS_SECRET_ACCESS_KEY` and `AWS_REGION` (and `AWS_SESSION_TOKEN`) passed along |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `azure` | `AZURE_API_KEY`, with `AZURE_API_VERSION` and `AZURE_RESOURCE_NAME` passed along |
| `anyscale` | `ANYSCALE_API_KEY` |
| `baseten` | `BASETEN_API_KEY` |
| `cerebras` | `CEREBRAS_API_KEY` |
| `cloudflare` | `CLOUDFLARE_API_KEY` |
| `codestral` | `CODESTRAL_API_KEY` |
| `cohere` | `COHERE_API_KEY` |
| `dashscope` | `DASHSCOPE_API_KEY` |
| `databricks` | `DATABRICKS_TOKEN` |
| `datarobot` | `DATAROBOT_API_TOKEN` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `deepinfra` | `DEEPINFRA_API_KEY` |
| `doubao` | `DOUBAO_API_KEY` |
| `featherless_ai` | `FEATHERLESS_AI_API_KEY` |
| `fireworks_ai` | `FIREWORKS_AI_API_KEY` |
| `github-copilot` | `GITHUB_TOKEN` |
| `google`, `gemini` | `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY` |
| `groq` | `GROQ_API_KEY` |
| `huggingface` | `HF_TOKEN`, `HUGGINGFACE_API_KEY` |
| `infinity` | `INFINITY_API_KEY` |
| `kimi` | `KIMI_API_KEY`, `MOONSHOT_API_KEY` |
| `llama`, `llamaapi` | `LLAMA_API_KEY` |
| `mistral` | `MISTRAL_API_KEY` |
| `minimax` | `MINIMAX_API_KEY` |
| `moonshot` | `MOONSHOT_API_KEY` |
| `nebius` | `NEBIUS_API_KEY` |
| `nlp_cloud` | `NLP_CLOUD_API_KEY` |
| `nvidia` | `NVIDIA_API_KEY` |
| `nvidia_nim` | `NVIDIA_NIM_API_KEY` |
| `novita` | `NOVITA_API_KEY` |
| `ollama` | `OLLAMA_API_KEY` |
| `openai`, `openai-responses`, `litellm_proxy`, `openai_responses` | `OPENAI_API_KEY` |
| `opencode` | `OPENCODE_API_KEY` |
| `openrouter` | `OPENROUTER_API_KEY` |
| `ovhcloud` | `OVHCLOUD_API_KEY` |
| `palm` | `PALM_API_KEY` |
| `perplexity` | `PERPLEXITYAI_API_KEY` |
| `replicate` | `REPLICATE_API_KEY` |
| `tetrate` | `TETRATE_API_KEY` |
| `together`, `together_ai` | `TOGETHER_API_KEY`, `TOGETHERAI_API_KEY` |
| `vercel_ai_gateway` | `VERCEL_AI_GATEWAY_API_KEY` |
| `vertex_ai` | `VERTEXAI_PROJECT` |
| `volcengine` | `VOLCENGINE_API_KEY` |
| `voyage` | `VOYAGE_API_KEY` |
| `writer` | `WRITER_API_KEY` |
| `xai` | `XAI_API_KEY` |
| `zai` | `ZAI_API_KEY` |

An OpenAI-compatible server, such as ollama, vLLM or LM Studio, works as `openai/<model>` with
`OPENAI_BASE_URL` set to its address.

</details>

## License

Apache-2.0. See [LICENSE](LICENSE).

## Contributors and contact

hbench-action is built and maintained by [node-q](https://nodeq.tech). See the
[contributors graph](https://github.com/node-q/hbench-action/graphs/contributors) for everyone who has
contributed.

- Questions and help: [#support on Discord](https://discord.gg/5b6wCn5sEK)
- New releases: [#announcements on Discord](https://discord.gg/dEvy6DCMTn)
- Bugs and feature requests for the action: [GitHub issues](https://github.com/node-q/hbench-action/issues);
  for hbench itself, [node-q/hbench's issues](https://github.com/node-q/hbench/issues)
- The full reference: [docs/REFERENCE.md](docs/REFERENCE.md)
- Releasing: [docs/RELEASING.md](docs/RELEASING.md)
