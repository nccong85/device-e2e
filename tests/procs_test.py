import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PROCS = HERE / "plugins/device-e2e/skills/playbook/harness/procs.py"
sys.path.insert(0, str(PROCS.parent))
import procs

passed = 0
failed = 0


def check(name, cond, out=""):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}")
        if out:
            print(out)


def cli(*args):
    r = subprocess.run([sys.executable, str(PROCS), *args], capture_output=True, encoding="utf-8")
    return r.returncode, r.stdout


# A stand-in for a suite: its command line carries the suite name and the platform, like `<suite> android E1`.
MARK = f"e2e_fake_suite_{int(time.time())}"
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", MARK, "android"])
# Another session's shell wrapper holds the text too; it is not the suite, and --kill must leave it alone.
shell = subprocess.Popen(["/bin/sh", "-c", f"sleep 60; : {MARK} android"]) if Path("/bin/sh").exists() else None
try:
    time.sleep(0.5)
    found = procs.find(MARK)
    check("find lists the process whose command line holds the text", [pid for pid, _ in found] == [child.pid], found)
    check("find returns the command line", found and MARK in found[0][1] and "android" in found[0][1], found)
    code, out = cli(MARK)
    check("cli prints pid and command line, exit 0", code == 0 and out.startswith(f"{child.pid} "), out)
    check("cli does not list itself", out.count("\n") == 1, out)
    code, out = cli(f"{MARK} ios")
    check("a different platform does not match", code == 1 and out == "", out)
    code, out = cli(f"{MARK} android", "--kill")
    check("--kill reports what it stopped", code == 0 and out.startswith(f"{child.pid} "), out)
    try:
        child.wait(timeout=10)
        check("--kill stops the process", True)
    except subprocess.TimeoutExpired:
        check("--kill stops the process", False)
    check("nothing left after --kill", procs.find(MARK) == [])
    code, out = cli()
    check("usage without a text, exit 2", code == 2 and "Usage:" in out, out)
    if shell:
        check("--kill leaves a shell whose command line holds the text", shell.poll() is None)
    for cmd, want in [
        ("/bin/zsh -c eval 'python3 x.py'", "zsh"), ("-bash", "bash"),
        ('"C:\\Program Files\\Git\\bin\\bash.exe" -c x', "bash"), ("C:\\Python312\\python.exe suite.py", "python"),
    ]:
        check(f"program name of {cmd!r}", procs._program(cmd) == want, procs._program(cmd))
finally:
    child.kill()
    if shell:
        shell.kill()

print(f"procs: pass={passed} fail={failed}")
sys.exit(1 if failed else 0)
