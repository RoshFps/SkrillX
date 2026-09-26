"""Generate shell completion scripts from the CLI's own argument parser.

The scripts are static: they list the commands, each command's options, and
fixed choices (actions, profiles, shells). Nothing is executed at completion
time, so completion stays instant and never touches the repository.
"""

from __future__ import annotations

import argparse
import shlex

SHELLS = ("bash", "zsh", "fish")


def describe(parser: argparse.ArgumentParser) -> dict[str, dict[str, object]]:
    """Command -> {'help', 'options', 'choices' (positional choices), 'option_choices'}."""
    commands: dict[str, dict[str, object]] = {}
    for action in parser._actions:  # argparse exposes no public API for this
        if not isinstance(action, argparse._SubParsersAction):
            continue
        helps = {choice.dest: choice.help or "" for choice in action._choices_actions}
        for name, sub in action.choices.items():
            options: list[str] = []
            positional: list[str] = []
            option_choices: dict[str, list[str]] = {}
            for item in sub._actions:
                if item.option_strings:
                    options.extend(flag for flag in item.option_strings if flag.startswith("--"))
                    if item.choices:
                        option_choices[item.option_strings[-1]] = [str(choice) for choice in item.choices]
                elif item.choices:
                    positional.extend(str(choice) for choice in item.choices)
            commands[name] = {"help": helps.get(name, ""), "options": sorted(set(options)),
                              "choices": positional, "option_choices": option_choices}
    return commands


def global_options(parser: argparse.ArgumentParser) -> list[str]:
    return sorted({flag for action in parser._actions for flag in action.option_strings if flag.startswith("--")})


def bash(parser: argparse.ArgumentParser, program: str = "ai-toolkit") -> str:
    commands = describe(parser)
    cases = []
    for name, info in commands.items():
        words = " ".join([*info["choices"], *info["options"]])  # type: ignore[misc]
        option_cases = "".join(
            f'            {flag}) COMPREPLY=( $(compgen -W {shlex.quote(" ".join(choices))} -- "$cur") ); return ;;\n'
            for flag, choices in info["option_choices"].items()  # type: ignore[union-attr]
        )
        cases.append(
            f"        {name})\n"
            f'          case "$prev" in\n{option_cases}'
            f'            --target|--output|--html) COMPREPLY=( $(compgen -f -- "$cur") ); return ;;\n'
            f"          esac\n"
            f'          COMPREPLY=( $(compgen -W {shlex.quote(words)} -- "$cur") ) ;;\n'
        )
    function = "_" + program.replace("-", "_")
    return f"""# bash completion for {program}. Install with:
#   {program} completion bash > ~/.local/share/bash-completion/completions/{program}
{function}() {{
  local cur prev command i
  cur="${{COMP_WORDS[COMP_CWORD]}}"
  prev="${{COMP_WORDS[COMP_CWORD-1]}}"
  command=""
  for ((i = 1; i < COMP_CWORD; i++)); do
    case "${{COMP_WORDS[i]}}" in -*) ;; *) command="${{COMP_WORDS[i]}}"; break ;; esac
  done
  if [[ -z "$command" ]]; then
    COMPREPLY=( $(compgen -W {shlex.quote(" ".join([*commands, *global_options(parser)]))} -- "$cur") )
    return
  fi
  case "$command" in
{"".join(cases)}  esac
}}
complete -F {function} {program}
"""


def zsh(parser: argparse.ArgumentParser, program: str = "ai-toolkit") -> str:
    commands = describe(parser)
    described = "\n".join(f"    {shlex.quote(name + ':' + str(info['help']).replace(':', ' -'))}" for name, info in commands.items())
    cases = []
    for name, info in commands.items():
        words = " ".join([*info["choices"], *info["options"]])  # type: ignore[misc]
        cases.append(f"    {name}) compadd -- {words} ;;")
    return f"""#compdef {program}
# zsh completion for {program}. Install with:
#   {program} completion zsh > "${{fpath[1]}}/_{program}"   (then restart your shell)
_{program.replace("-", "_")}() {{
  local -a commands
  commands=(
{described}
  )
  if (( CURRENT == 2 )); then
    _describe 'command' commands
    return
  fi
  case "$words[2]" in
{chr(10).join(cases)}
  esac
}}
compdef _{program.replace("-", "_")} {program}
"""


def fish(parser: argparse.ArgumentParser, program: str = "ai-toolkit") -> str:
    commands = describe(parser)
    lines = [f"# fish completion for {program}. Install with:",
             f"#   {program} completion fish > ~/.config/fish/completions/{program}.fish",
             f"complete -c {program} -f"]
    names = " ".join(commands)
    for name, info in commands.items():
        lines.append(f"complete -c {program} -n 'not __fish_seen_subcommand_from {names}' -a {name} -d {shlex.quote(str(info['help']))}")
        for choice in info["choices"]:  # type: ignore[union-attr]
            lines.append(f"complete -c {program} -n '__fish_seen_subcommand_from {name}' -a {shlex.quote(choice)}")
        for flag in info["options"]:  # type: ignore[union-attr]
            lines.append(f"complete -c {program} -n '__fish_seen_subcommand_from {name}' -l {flag[2:]}")
    return "\n".join(lines) + "\n"


def script(shell: str, parser: argparse.ArgumentParser) -> str:
    if shell == "bash":
        return bash(parser)
    if shell == "zsh":
        return zsh(parser)
    if shell == "fish":
        return fish(parser)
    raise ValueError(f"unsupported shell: {shell}")
