#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "::error title=hbench run::$*"
  exit 1
}

add_lines() {
  local flag="$1" text="$2" line
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" ]] && continue
    if [[ -n "$flag" ]]; then
      arguments+=("$flag" "$line")
    else
      arguments+=("$line")
    fi
  done <<<"$text"
}

add_option() {
  [[ -n "$2" ]] && arguments+=("$1" "$2")
  return 0
}

[[ -n "${INPUT_PATH}${INPUT_DATASET}${INPUT_CONFIG}" ]] || fail "set path, dataset or config"
case "${INPUT_LOCKED:-false}" in
  true | false) ;;
  *) fail "locked is '$INPUT_LOCKED'; use true or false" ;;
esac
if [[ -n "${INPUT_MIN_MEAN_REWARD}" ]]; then
  [[ "$INPUT_MIN_MEAN_REWARD" =~ ^(0(\.[0-9]+)?|1(\.0+)?)$ ]] || fail "min-mean-reward is '$INPUT_MIN_MEAN_REWARD'; use a number from 0 to 1"
fi
while IFS= read -r line; do
  case "${line#"${line%%[![:space:]]*}"}" in
    --job-name | --job-name=*) fail "args sets --job-name; set the job-name input instead" ;;
  esac
done <<<"$INPUT_ARGS"

jobs_directory="${INPUT_JOBS_DIR:-$RUNNER_TEMP/hbench-jobs}"
mkdir -p "$jobs_directory"
jobs_directory="$(cd "$jobs_directory" && pwd)"
run_id="${GITHUB_JOB:-job}-$(date -u +%Y%m%dT%H%M%SZ)-$RANDOM"
config_job_name=""
if [[ -n "$INPUT_CONFIG" && -z "$INPUT_JOB_NAME" ]]; then
  config_job_name="$(python3 "$GITHUB_ACTION_PATH/scripts/config_job_name.py" "$INPUT_CONFIG")" ||
    fail "could not read config '$INPUT_CONFIG'"
fi
job_name="${INPUT_JOB_NAME:-${config_job_name:-$run_id}}"
job_directory="$jobs_directory/$job_name"

arguments=(run)
add_option --config "$INPUT_CONFIG"
add_option --path "$INPUT_PATH"
add_option --dataset "$INPUT_DATASET"
case "$INPUT_REGISTRY" in
  "") ;;
  oci://* | oci-layout:*) arguments+=(--registry "$INPUT_REGISTRY") ;;
  http://* | https://*) arguments+=(--registry-url "$INPUT_REGISTRY") ;;
  *)
    [[ -f "$INPUT_REGISTRY" ]] || fail "registry is '$INPUT_REGISTRY', which is not a file; use oci://<registry>/<namespace>, oci-layout:<dir>, or a registry.json URL or path"
    arguments+=(--registry-path "$INPUT_REGISTRY")
    ;;
esac
add_option --agent "$INPUT_AGENT"
add_option --model "$INPUT_MODEL"
add_option --n-tasks "$INPUT_N_TASKS"
add_option --n-attempts "$INPUT_N_ATTEMPTS"
add_option --n-concurrent "$INPUT_N_CONCURRENT"
add_lines --include-task-name "$INPUT_INCLUDE"
add_lines --exclude-task-name "$INPUT_EXCLUDE"
[[ "${INPUT_LOCKED:-false}" == true ]] && arguments+=(--locked)
arguments+=(--jobs-dir "$jobs_directory")
[[ -z "$config_job_name" ]] && arguments+=(--job-name "$job_name")
add_lines "" "$INPUT_ARGS"

echo "job-dir=$job_directory" >> "$GITHUB_OUTPUT"
artifact_name="${INPUT_ARTIFACT_NAME:-hbench-$run_id}"
echo "artifact-name=$artifact_name" >> "$GITHUB_OUTPUT"

printf 'hbench'
printf ' %q' "${arguments[@]}"
printf '\n'
status=0
hbench "${arguments[@]}" || status=$?

if [[ ! -f "$job_directory/result.json" ]]; then
  fail "hbench run exited $status without writing $job_directory/result.json"
fi

report_status=0
if [[ "${INPUT_UPLOAD_ARTIFACT:-true}" == true ]]; then
  export HBENCH_ARTIFACT_NAME="$artifact_name"
fi
python3 "$GITHUB_ACTION_PATH/scripts/report.py" "$job_directory/result.json" || report_status=$?
if [[ "$status" -ne 0 ]]; then
  fail "hbench run exited $status"
fi
exit "$report_status"
