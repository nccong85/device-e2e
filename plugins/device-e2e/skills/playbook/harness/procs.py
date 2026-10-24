"""Find or stop the processes whose command line contains a text: `pgrep -fl` / `pkill -f` on every host.

Git Bash on Windows has neither pgrep nor pkill, and its `ps` does not show command lines.

Usage:
  procs.py <text>          print "<pid> <command line>" per match; exit 1 when none
  procs.py <text> --kill   stop every match
"""
import os
import re
import signal
import subprocess
import sys

# Win32_Process is the only stock source of another process's command line on Windows.
# PowerShell 5.1 writes a pipe in the OEM code page unless told otherwise.
_WINDOWS_QUERY = (
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-CimInstance Win32_Process | ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"
)


def _all_processes():
    if os.name == "nt":
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _WINDOWS_QUERY],
            capture_output=True, check=True,
        ).stdout.decode("utf-8", errors="replace")
        rows = (line.split("\t", 1) for line in out.splitlines() if "\t" in line)
    else:
        out = subprocess.run(["ps", "-A", "-o", "pid=,args="], capture_output=True, check=True).stdout.decode(
            "utf-8", errors="replace"
        )
        rows = (line.strip().split(None, 1) for line in out.splitlines() if line.strip())
    for row in rows:
        if len(row) == 2 and row[0].strip().isdigit():
            yield int(row[0]), row[1].strip()


# A shell's command line holds the text of every command it runs: an agent's `zsh -c "... procs.py <suite>"`
# wrapper, or another session's. A suite runs under Python, never as a shell, so shells are not matches.
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "cmd", "powershell", "pwsh"}


def _program(cmd):
    first = cmd[1:].split('"', 1)[0] if cmd.startswith('"') else cmd.split(None, 1)[0]
    name = re.split(r"[\\/]", first)[-1].lstrip("-").lower()
    return name[:-4] if name.endswith(".exe") else name


def find(text):
    # This process and the shell that started it carry the text in their own command lines.
    mine = {os.getpid(), os.getppid()}
    return [
        (pid, cmd) for pid, cmd in _all_processes()
        if text in cmd and pid not in mine and _program(cmd) not in _SHELLS
    ]


def kill(text):
    found = find(text)
    for pid, _ in found:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    return found


def main(argv):
    if not argv or argv[0].startswith("-") or argv[1:] not in ([], ["--kill"]):
        print(__doc__[__doc__.index("Usage:"):].rstrip())
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    found = kill(argv[0]) if argv[1:] else find(argv[0])
    for pid, cmd in found:
        print(pid, cmd)
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
