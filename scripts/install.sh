#!/usr/bin/env bash
set -euo pipefail

readonly HBENCH_REPOSITORY=node-q/hbench
readonly HBENCH_RELEASE_WORKFLOW=node-q/hbench/.github/workflows/release.yml

fail() {
  echo "::error title=hbench install::$*"
  exit 1
}

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) target=x86_64-unknown-linux-musl ;;
  Linux-aarch64 | Linux-arm64) target=aarch64-unknown-linux-musl ;;
  Darwin-x86_64) target=x86_64-apple-darwin ;;
  Darwin-arm64) target=aarch64-apple-darwin ;;
  *) fail "hbench has no release for $(uname -s) $(uname -m); use a Linux or macOS runner" ;;
esac

requested="${INPUT_VERSION:-latest}"
if [[ "$requested" == latest ]]; then
  latest_url="$(curl -fsSLI --retry 3 -o /dev/null -w '%{url_effective}' "https://github.com/$HBENCH_REPOSITORY/releases/latest")"
  tag="${latest_url##*/}"
else
  tag="v${requested#v}"
fi
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]] || fail "'$requested' is not an hbench release such as v0.3.0 or latest"

case "${INPUT_VERIFY_PROVENANCE:-auto}" in
  true) verify_provenance=true ;;
  false) verify_provenance=false ;;
  auto) if command -v gh > /dev/null; then verify_provenance=true; else verify_provenance=false; fi ;;
  *) fail "verify-provenance is '$INPUT_VERIFY_PROVENANCE'; use true, false or auto" ;;
esac

install_directory="${RUNNER_TOOL_CACHE:-$RUNNER_TEMP}/hbench/${tag#v}/$target"
if [[ ! -x "$install_directory/hbench" || ! -f "$install_directory.complete" ]]; then
  archive="hbench-$tag-$target.tar.gz"
  download_directory="$(mktemp -d)"
  trap 'rm -rf "$download_directory"' EXIT
  for file in "$archive" SHA256SUMS; do
    curl -fsSL --retry 3 --output "$download_directory/$file" \
      "https://github.com/$HBENCH_REPOSITORY/releases/download/$tag/$file" ||
      fail "could not download $file of hbench $tag"
  done

  checksum_line="$(awk -v name="$archive" '$2 == name' "$download_directory/SHA256SUMS")"
  [[ -n "$checksum_line" && "$(wc -l <<<"$checksum_line")" -eq 1 ]] || fail "SHA256SUMS of $tag lists $archive no or several times"
  if command -v sha256sum > /dev/null; then
    (cd "$download_directory" && sha256sum --check --strict <<<"$checksum_line") || fail "$archive does not match SHA256SUMS"
  else
    (cd "$download_directory" && shasum -a 256 --check <<<"$checksum_line") || fail "$archive does not match SHA256SUMS"
  fi

  if [[ "$verify_provenance" == true ]]; then
    command -v gh > /dev/null || fail "verify-provenance is true, but the GitHub CLI (gh) is not installed"
    GH_TOKEN="$INPUT_TOKEN" gh attestation verify "$download_directory/$archive" \
      --repo "$HBENCH_REPOSITORY" \
      --signer-workflow "$HBENCH_RELEASE_WORKFLOW" \
      --source-ref "refs/tags/$tag" \
      --deny-self-hosted-runners ||
      fail "the build provenance of $archive does not verify"
  else
    echo "::warning title=hbench install::Build provenance not checked (verify-provenance: ${INPUT_VERIFY_PROVENANCE:-auto}, gh $(command -v gh > /dev/null && echo installed || echo 'not installed'))"
  fi

  tar -xzf "$download_directory/$archive" -C "$download_directory"
  rm -rf "$install_directory"
  mkdir -p "$install_directory"
  install -m 0755 "$download_directory/hbench-$tag-$target/hbench" "$install_directory/hbench"
  touch "$install_directory.complete"
fi

installed_version="$("$install_directory/hbench" --version)"
[[ "$installed_version" == "hbench ${tag#v}" ]] || fail "the installed binary reports '$installed_version', not hbench ${tag#v}"

echo "$install_directory" >> "$GITHUB_PATH"
{
  echo "version=$tag"
  echo "hbench-path=$install_directory/hbench"
} >> "$GITHUB_OUTPUT"
echo "Installed $installed_version for $target in $install_directory"
