#!/usr/bin/env bash
# Put `ai-toolkit` on your PATH by linking bin/ai-toolkit from this checkout.
#
#   bash tooling/install-cli.sh                 # links into ~/.local/bin
#   bash tooling/install-cli.sh --prefix DIR    # links into DIR
#   bash tooling/install-cli.sh --uninstall     # removes the link
#
# The link points at this checkout, so `git pull` updates the command too.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
prefix="${HOME}/.local/bin"
uninstall=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) prefix="${2:?--prefix needs a directory}"; shift 2 ;;
    --uninstall) uninstall=1; shift ;;
    -h|--help) sed -n '2,8p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "ERROR unknown option: $1" >&2; exit 2 ;;
  esac
done
link="${prefix}/ai-toolkit"

if [[ "${uninstall}" == 1 ]]; then
  if [[ -L "${link}" ]]; then rm "${link}"; echo "Removed ${link}"; else echo "Nothing to remove at ${link}"; fi
  exit 0
fi
if [[ -e "${link}" && ! -L "${link}" ]]; then
  echo "ERROR ${link} exists and is not a symlink; remove it or choose --prefix." >&2
  exit 1
fi
mkdir -p "${prefix}"
# Checkouts made from an archive or a web upload can lose the executable bit.
chmod +x "${repo_root}/bin/ai-toolkit" 2>/dev/null || true
ln -sfn "${repo_root}/bin/ai-toolkit" "${link}"
echo "Linked ${link} -> ${repo_root}/bin/ai-toolkit"
case ":${PATH}:" in
  *":${prefix}:"*) ;;
  *) echo "Add ${prefix} to your PATH, for example: echo 'export PATH=\"${prefix}:\$PATH\"' >> ~/.bashrc" ;;
esac
echo "Try: ai-toolkit    (tab completion: ai-toolkit completion bash|zsh|fish)"
