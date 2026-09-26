#!/usr/bin/env bash
# Put `ai-toolkit` on your PATH with a wrapper that runs bin/ai-toolkit from this checkout.
#
#   bash tooling/install-cli.sh                 # installs ~/.local/bin/ai-toolkit
#   bash tooling/install-cli.sh --prefix DIR    # installs DIR/ai-toolkit
#   bash tooling/install-cli.sh --uninstall     # removes it
#
# The wrapper runs this checkout, so `git pull` updates the command too.
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

marker="# ai-toolkit launcher (written by tooling/install-cli.sh)"
managed() { [[ -L "$1" ]] || { [[ -f "$1" ]] && grep -qF "${marker}" "$1"; }; }

if [[ "${uninstall}" == 1 ]]; then
  if managed "${link}"; then rm "${link}"; echo "Removed ${link}"; else echo "Nothing to remove at ${link}"; fi
  exit 0
fi
if [[ -e "${link}" ]] && ! managed "${link}"; then
  echo "ERROR ${link} exists and was not created by this installer; remove it or choose --prefix." >&2
  exit 1
fi
mkdir -p "${prefix}"
# A small wrapper (not a symlink) so the checkout's file modes are never changed
# and the command works even where the launcher lost its executable bit.
rm -f "${link}"
printf '#!/usr/bin/env bash\n%s\nexec bash %q "$@"\n' "${marker}" "${repo_root}/bin/ai-toolkit" > "${link}"
chmod +x "${link}"
echo "Installed ${link} -> ${repo_root}/bin/ai-toolkit"
case ":${PATH}:" in
  *":${prefix}:"*) ;;
  *) echo "Add ${prefix} to your PATH, for example: echo 'export PATH=\"${prefix}:\$PATH\"' >> ~/.bashrc" ;;
esac
echo "Try: ai-toolkit    (tab completion: ai-toolkit completion bash|zsh|fish)"
