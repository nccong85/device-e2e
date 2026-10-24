import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "plugins/device-e2e/skills/playbook/harness"))

passed = 0
failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}")


WORK = Path(tempfile.mkdtemp(prefix="e2e_drv_"))
LOG = WORK / "adb.log"
DUMP = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?><hierarchy rotation="0">
<node index="0" text="" resource-id="" class="android.widget.FrameLayout" content-desc="" bounds="[0,0][720,1600]">
<node index="1" text="Documents" resource-id="app:id/title" class="android.widget.TextView" content-desc="" bounds="[40,100][300,160]" />
<node index="2" text="" resource-id="" class="android.widget.Button" content-desc="Import" bounds="[600,1400][700,1500]" />
<node index="3" text="hidden" resource-id="" class="android.view.View" content-desc="" bounds="[10,10][10,10]" />
</node></hierarchy>"""
(WORK / "dump.xml").write_text(DUMP)
# A Python fake, so the same adb stand-in runs on macOS, Linux and Windows.
fake_adb = WORK / "adb"
fake_adb.write_text(
    f"#!{sys.executable}\n"
    "import os, sys\n"
    "args = ' '.join(sys.argv[1:])\n"
    f"with open({str(LOG)!r}, 'a', encoding='utf-8') as log:\n"
    "    log.write(args + '\\n')\n"
    "if 'uiautomator dump' in args:\n"
    "    print('UI hierchary dumped to: /sdcard/e2e_window.xml')\n"
    "elif 'cat /sdcard/e2e_window.xml' in args:\n"
    f"    sys.stdout.write(open({str(WORK / 'dump.xml')!r}, encoding='utf-8').read())\n"
    "elif 'wm size' in args:\n"
    "    print('Physical size: 720x1600')\n"
    "elif 'default_input_method' in args:\n"
    "    print(os.environ.get('FAKE_IME') or 'com.google.android.inputmethod.latin/.LatinIME')\n"
    "elif 'topResumedActivity' in args:\n"
    "    print('topResumedActivity=ActivityRecord{1 u0 com.example.app/.Main t1}')\n"
    "elif 'date +%s' in args:\n"
    "    print('1700000000')\n"
    "elif sys.argv[3:4] == ['logcat']:\n"
    "    print('10-24 15:47:50.000  1000  1100 I ActivityManager: Start proc 3221:com.example.app/u0a1 for activity')\n"
    "    print('10-24 15:47:51.000  3221  3221 D Flutter: page 10 indexed')\n"
    "    print('10-24 15:47:52.000  2000  2000 I wifi: scan done')\n"
    "    print('10-24 15:47:53.000  2001  2001 E SurfaceFlinger: dropped frame')\n"
    "    print('10-24 15:47:53.500  1000  1100 E lowmemorykiller: Kill 4000 (other.app)')\n"
    "    print('10-24 15:47:54.014  3221  3570 E AndroidRuntime: FATAL EXCEPTION: main')\n"
    "elif sys.argv[3:4] == ['pull']:\n"
    "    open(sys.argv[5], 'wb').write(b'pulled')\n",
    encoding="utf-8",
)
fake_adb.chmod(0o755)
if os.name == "nt":
    # Windows runs only real executables, so hand the fake to this Python.
    _real_run = subprocess.run

    def _run(cmd, *args, **kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == str(fake_adb):
            cmd = [sys.executable, str(fake_adb), *cmd[1:]]
        return _real_run(cmd, *args, **kwargs)

    subprocess.run = _run
    _real_popen = subprocess.Popen

    class _Popen(_real_popen):  # recording() starts screenrecord with Popen
        def __init__(self, cmd, *args, **kwargs):
            if isinstance(cmd, list) and cmd and cmd[0] == str(fake_adb):
                cmd = [sys.executable, str(fake_adb), *cmd[1:]]
            super().__init__(cmd, *args, **kwargs)

    subprocess.Popen = _Popen

for k in ("E2E_APP_ID", "E2E_ANDROID_SERIAL", "WDA", "E2E_IOS_UDID"):
    os.environ.pop(k, None)
os.environ["E2E_ADB"] = str(fake_adb)

import adb_driver
import wda_driver

check("wda session file defaults to a private per-user path",
      str(wda_driver.SID_FILE).startswith(str(Path.home())) and not str(wda_driver.SID_FILE).startswith("/tmp"))
target = WORK / "victim.txt"
target.write_text("keep")
link = WORK / "sid_link"
secret = WORK / "secret.txt"
secret.write_text("AKIA-SECRET-VALUE")
sid_link = WORK / "sid_points_elsewhere"
try:
    link.symlink_to(target)
    sid_link.symlink_to(secret)
    can_symlink = True
except OSError:  # Windows without Developer Mode or admin
    can_symlink = False
    print("skip: symlink checks (this account cannot create symlinks)")
if can_symlink:
    try:
        wda_driver._write_private(link, "S9")
        check("wda session write refuses a symlink", False)
    except OSError:
        check("wda session write refuses a symlink", target.read_text() == "keep")
    check("wda ignores a symlinked session file on read", wda_driver._read_cached_sid(sid_link) == "")

# Windows has no POSIX mode bits: chmod only sets the read-only flag.
POSIX_MODES = os.name != "nt"
loose = WORK / "loose_sid"
loose.write_text("old")
loose.chmod(0o644)
wda_driver._write_private(loose, "S2")
check("wda session write tightens an existing file to 0600",
      (not POSIX_MODES or (loose.stat().st_mode & 0o777) == 0o600) and loose.read_text() == "S2")
bad_sid = WORK / "bad_sid"
bad_sid.write_text("../../etc/passwd")
check("wda ignores a malformed cached session id", wda_driver._read_cached_sid(bad_sid) == "")
good_sid = WORK / "good_sid"
good_sid.write_text("0A1B2C3D-4E5F-6789-ABCD-EF0123456789\n")
check("wda accepts a UUID session id", wda_driver._read_cached_sid(good_sid) == "0A1B2C3D-4E5F-6789-ABCD-EF0123456789")

try:
    adb_driver.AndroidDriver()
    check("android driver requires E2E_APP_ID", False)
except RuntimeError as e:
    check("android driver requires E2E_APP_ID", "E2E_APP_ID" in str(e))

os.environ["E2E_APP_ID"] = "com.example.app"
os.environ["E2E_ANDROID_SERIAL"] = "SER123"
os.environ["E2E_ANDROID_FIXTURE_DIR"] = "/sdcard/Download/e2e_kit"
a = adb_driver.AndroidDriver()
els = a.elements()
texts = [e["text"] for e in els]
check("android parses text and content-desc", "Documents" in texts and "Import" in texts)
doc = next(e for e in els if e["text"] == "Documents")
check("android bounds become x/y/w/h", (doc["x"], doc["y"], doc["w"], doc["h"]) == (40, 100, 260, 60))
check("android find_any skips zero-size nodes", a.find_any(["hidden"]) is None)
check("android find_any finds visible node", a.find_any(["Import"])["id"] == "")
check("android size parses wm size", a.size() == (720, 1600))
check("android foreground package parsed", a.foreground_package() == "com.example.app")
a.stage_fixtures(WORK, ["f.pdf"])
a.launch()
log = LOG.read_text(encoding="utf-8")
check("android every call targets the serial", all(line.startswith("-s SER123 ") for line in log.splitlines()))
check("android fixtures pushed to the configured folder", "push " in log and "/sdcard/Download/e2e_kit/f.pdf" in log)
check("android media scan uses the configured folder", "file:///sdcard/Download/e2e_kit/f.pdf" in log)
check("android launch uses the app id", "monkey -p com.example.app" in log)
try:
    a.type_text("hợp đồng")
    check("android non-ASCII without ADB Keyboard raises", False)
except adb_driver.UnicodeInputUnavailable:
    check("android non-ASCII without ADB Keyboard raises", True)

for bad in ("/sdcard", "/sdcard/Download", "/sdcard/Download/photos", "/sdcard/Download/../DCIM/e2e", "/data/e2e"):
    os.environ["E2E_ANDROID_FIXTURE_DIR"] = bad
    try:
        adb_driver.AndroidDriver()
        check(f"android refuses fixture dir {bad}", False)
    except ValueError:
        check(f"android refuses fixture dir {bad}", True)
for bad_app in ("com.example.app; rm -rf /", "noDots", "com.example app"):
    try:
        adb_driver.AndroidDriver(app_id=bad_app)
        check(f"android refuses app id {bad_app!r}", False)
    except ValueError:
        check(f"android refuses app id {bad_app!r}", True)
os.environ["E2E_ANDROID_FIXTURE_DIR"] = "/sdcard/Download/my e2e"
LOG.write_text("")
q = adb_driver.AndroidDriver()
q.stage_fixtures(WORK, ["a b.pdf"])
q.remove_fixtures()
log = LOG.read_text(encoding="utf-8")
check("android quotes the fixture dir in rm -rf", "rm -rf '/sdcard/Download/my e2e'" in log)
check("android quotes the media-scan uri", "-d 'file:///sdcard/Download/my e2e/a b.pdf'" in log)
try:
    q.stage_fixtures(WORK, ["../x.pdf"])
    check("android refuses a fixture name with a path", False)
except ValueError:
    check("android refuses a fixture name with a path", True)

def device_argv(fragment):
    line = [ln for ln in LOG.read_text(encoding="utf-8").splitlines() if fragment in ln][-1]
    cmd = line.split(" shell ", 1)[1]
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        argv = list(lex)
    except ValueError:
        return None
    for i, tok in enumerate(argv):
        if ("$" in tok or "`" in tok) and not cmd.endswith(shlex.quote(tok)):
            argv[i] = None
    return argv


LOG.write_text("")
os.environ["E2E_ANDROID_FIXTURE_DIR"] = "/sdcard/Download/e2e"
r = adb_driver.AndroidDriver()
for text in ("price&reboot", "a;b|c", "it's $HOME", "R&D `id`"):
    r.type_text(text)
    check(f"android input text reaches the device as one argument: {text!r}",
          device_argv("input text") == ["input", "text", text.replace(" ", "%s")])
os.environ["FAKE_IME"] = "com.android.adbkeyboard/.AdbIME"
for text in ("hợp đồng & co", "x'; reboot; echo '"):
    r.type_text(text)
    check(f"android ADB Keyboard payload stays one argument: {text!r}",
          device_argv("ADB_INPUT_TEXT")[-1] == text and device_argv("ADB_INPUT_TEXT")[-2] == "msg")
del os.environ["FAKE_IME"]
r.restore_ime("com.x/.Ime; reboot")
check("android restore_ime quotes the IME", device_argv("ime set") == ["ime", "set", "com.x/.Ime; reboot"])
r.restore_stay_on("2")
check("android restore_stay_on puts the recorded value back",
      device_argv("stay_on_while_plugged_in") == ["settings", "put", "global", "stay_on_while_plugged_in", "2"])
LOG.write_text("")
r.restore_stay_on("2; reboot")
check("android restore_stay_on ignores a value that is not a number", "stay_on_while_plugged_in" not in LOG.read_text(encoding="utf-8"))

import evidence

EV = WORK / "evidence"
LOG.write_text("")
ev = evidence.Evidence(r, "E3", root=EV)
check("evidence names start at 1", ev.path("png").name == "E3_android_1.png")
(EV / "E3_android_4.png").write_text("")
(EV / "E31_android_9.png").write_text("")
check("evidence numbers continue after the highest file of the case", ev.path("xml").name == "E3_android_5.xml")
tree = ev.tree()
check("android dump_tree keeps the raw uiautomator xml", tree.name == "E3_android_5.xml" and "Documents" in tree.read_text())
mark = r.log_mark()
check("android log_mark reads the phone's clock", mark == "1700000000")
logs = r.device_log(ev, mark)
argv = [ln for ln in LOG.read_text(encoding="utf-8").splitlines() if " logcat " in ln][-1].split()
check("android device_log dumps logcat since the mark",
      argv[2:] == ["logcat", "-d", "-v", "threadtime", "-b", "main,system,crash", "-t", "1700000000.000"])
check("android device_log writes a .log evidence file", logs[0].name == "E3_android_6.log" and "FATAL" in logs[0].read_text())
app_log = logs[0].read_text()
check("android device_log keeps the app's process, its start line, crash and kill errors",
      all(t in app_log for t in ("Start proc 3221", "page 10 indexed", "lowmemorykiller", "FATAL")))
check("android device_log drops other processes' info lines and vendor errors",
      "wifi: scan done" not in app_log and "dropped frame" not in app_log)
full = r.device_log(ev, mark, full=True)
check("android device_log full=True keeps every line", "wifi: scan done" in full[0].read_text())
check("android log_mark offset moves the mark back", r.log_mark(-60) == "1699999940")
try:
    r.device_log(ev, "1; reboot")
    check("android device_log refuses a mark that is not a number", False)
except ValueError:
    check("android device_log refuses a mark that is not a number", True)
failed_files = ev.failure(mark)
check("evidence.failure saves screenshot, tree and log",
      [f.suffix for f in failed_files] == [".png", ".xml", ".log"])
LOG.write_text("")
ev.failure()
argv = [ln for ln in LOG.read_text(encoding="utf-8").splitlines() if " logcat " in ln][-1].split()
check("evidence.failure without a mark takes the last minute", argv[-1] == "1699999940.000")
r_screenshot = r.screenshot
r.screenshot = lambda path: (_ for _ in ()).throw(RuntimeError("device gone"))
failed_files = ev.failure(mark)
r.screenshot = r_screenshot
check("evidence.failure keeps the tree and log when the screenshot fails",
      "device gone" in failed_files[0] and failed_files[1].suffix == ".xml" and failed_files[2].suffix == ".log")
LOG.write_text("")
with r.recording(EV / "E3_android_10.mp4", limit=999) as vid:
    pass
log = LOG.read_text(encoding="utf-8")
check("android recording caps the time limit at 180 s", "screenrecord --bugreport --time-limit 180 /sdcard/e2e_rec.mp4" in log)
check("android recording stops with SIGINT, pulls and removes the file",
      "pkill -INT screenrecord" in log and vid.read_bytes() == b"pulled" and "rm -f /sdcard/e2e_rec.mp4" in log)
check("android visible: inside the screen", r.visible({"x": 40, "y": 100, "w": 260, "h": 60}))
check("android not visible: below the screen", not r.visible({"x": 40, "y": 1580, "w": 260, "h": 60}))
check("android not visible: zero size", not r.visible({"x": 40, "y": 100, "w": 0, "h": 60}))
LOG.write_text("")
r_pull = r.pull_file
r.pull_file = lambda src, dest: (_ for _ in ()).throw(RuntimeError("pull failed"))
try:
    with r.recording(EV / "E3_android_11.mp4"):
        raise AssertionError("the case's own failure")
except AssertionError:
    check("android recording keeps the case's failure when the pull fails", True)
except RuntimeError:
    check("android recording keeps the case's failure when the pull fails", False)
r.pull_file = r_pull
check("android recording removes the phone's file when the pull fails", "rm -f /sdcard/e2e_rec.mp4" in LOG.read_text(encoding="utf-8"))
r._screen = (1600, 720)  # the last dump was landscape
check("android visible: right half of a landscape screen", r.visible({"x": 1000, "y": 100, "w": 260, "h": 60}))
check("android not visible: below a landscape screen", not r.visible({"x": 40, "y": 700, "w": 260, "h": 60}))
del r._screen
check("ios lastModDate in UTC", wda_driver._stamp("2026-10-24T08:00:00.000Z") == 1792828800)
check("ios lastModDate with an offset", wda_driver._stamp("2026-10-24T15:00:00+07:00") == 1792828800)
check("ios lastModDate without an offset is UTC", wda_driver._stamp("2026-10-24T08:00:00") == 1792828800)
try:
    evidence.Evidence(r, "../E1", root=EV)
    check("evidence refuses a case id with a path", False)
except ValueError:
    check("evidence refuses a case id with a path", True)

SOURCE = (
    "Application, 0x1, {{0.0, 0.0}, {390.0, 844.0}}, label: 'App'\n"
    "    Button, 0x2, {{20.0, 40.0}, {60.0, 30.0}}, label: 'Back'\n"
    "    StaticText, 0x3, {{20.0, 200.0}, {200.0, 80.0}}, label: 'e2e_vi.pdf\n"
    "12 pages'\n"
    "    Other, 0x4, {{0.0, 0.0}, {0.0, 0.0}}, label: 'ghost'\n"
    "Path to element:\n"
)
calls = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        calls.append(("GET", self.path, None))
        if self.path.startswith("/source"):
            self._send({"value": SOURCE})
        elif self.path.endswith("/window/size"):
            self._send({"value": {"width": 390, "height": 844}})
        else:
            self._send({"value": None})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"null")
        calls.append(("POST", self.path, body))
        if self.path == "/session":
            self._send({"sessionId": "S1", "value": {}})
        else:
            self._send({"value": None})


srv = HTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
os.environ["WDA"] = f"http://127.0.0.1:{srv.server_address[1]}"
os.environ["E2E_WDA_SID_FILE"] = str(WORK / "sid")
wda_driver.SID_FILE = WORK / "sid"
i = wda_driver.IosDriver()
els = i.elements()
tile = next(e for e in els if e["text"].startswith("e2e_vi.pdf"))
check("ios joins multi-line labels", tile["text"] == "e2e_vi.pdf\n12 pages")
check("ios keeps element type", tile["type"] == "StaticText")
check("ios find_any skips zero-size elements", i.find_any(["ghost"]) is None)
i.back()
taps = [c for c in calls if c[0] == "POST" and c[1].endswith("/wda/tap")]
check("ios back taps the Back label", taps and taps[-1][2] == {"x": 50.0, "y": 55.0})
i.launch()
launches = [c for c in calls if c[1].endswith("/wda/apps/launch")]
check("ios launch uses the app id", launches and launches[-1][2] == {"bundleId": "com.example.app"})
check("ios session id cached", (WORK / "sid").read_text() == "S1")
if POSIX_MODES:
    check("ios session file is owner-only", ((WORK / "sid").stat().st_mode & 0o777) == 0o600)

iev = evidence.Evidence(i, "E4", root=EV)
check("ios dump_tree saves the source", i.dump_tree(iev.path("xml")).read_text().startswith("Application"))
check("ios visible: inside the window", i.visible({"x": 20, "y": 200, "w": 200, "h": 80}))
check("ios not visible: scrolled below the window", not i.visible({"x": 20, "y": 900, "w": 200, "h": 80}))
os.environ["E2E_IOS_UDID"] = "UDID1"
real_run = wda_driver.subprocess.run
ran = []


def fake_devicectl(cmd, **kwargs):
    ran.append(cmd)
    dest = cmd[cmd.index("-j") + 1] if "-j" in cmd else cmd[cmd.index("--destination") + 1]
    if "-j" in cmd:
        files = [
            {"name": "Runner-2026-10-24-150000.ips", "relativePath": "Runner-2026-10-24-150000.ips",
             "metadata": {"lastModDate": "2026-10-24T08:00:00.000Z"}},
            {"name": "Other-2026-10-24-150100.ips", "relativePath": "Other-2026-10-24-150100.ips",
             "metadata": {"lastModDate": "2026-10-24T08:01:00.000Z"}},
            {"name": "Old-2026-10-01-100000.ips", "relativePath": "Old-2026-10-01-100000.ips",
             "metadata": {"lastModDate": "2026-10-01T03:00:00.000Z"}},
            {"name": "Assistant", "relativePath": "Assistant", "metadata": {"lastModDate": "2026-10-24T08:02:00.000Z"}},
        ]
        Path(dest).write_text(json.dumps({"result": {"files": files}}))
    else:
        bundle = os.environ["E2E_APP_ID"] if "Runner" in cmd[cmd.index("--source") + 1] else "com.apple.Other"
        Path(dest).write_text(json.dumps({"bundleID": bundle}) + "\n{}")


wda_driver.subprocess.run = fake_devicectl
since = wda_driver.datetime(2026, 10, 24, 7, 59, tzinfo=wda_driver.timezone.utc).timestamp()
reports = i.device_log(iev, since)
wda_driver.subprocess.run = real_run
check("ios device_log keeps only this app's crash reports since the mark",
      len(reports) == 1 and reports[0].suffix == ".ips" and os.environ["E2E_APP_ID"] in reports[0].read_text())
check("ios device_log copies only reports newer than the mark",
      sum("copy" in c for c in ran) == 2 and not any("Old-" in " ".join(c) for c in ran))
check("ios device_log leaves no listing or foreign report behind",
      sorted(p.suffix for p in EV.glob("E4_*")) == [".ips", ".xml"])

sdk = WORK / "sdk"
(sdk / "platform-tools").mkdir(parents=True)
sdk_adb = sdk / "platform-tools" / ("adb.exe" if os.name == "nt" else "adb")
sdk_adb.write_text("")
sdk_adb.chmod(0o755)
saved = {k: os.environ.pop(k, None) for k in ("E2E_ADB", "ANDROID_HOME", "PATH", "HOME", "USERPROFILE", "LOCALAPPDATA")}
os.environ["PATH"] = str(WORK / "empty_path")
os.environ["HOME"] = os.environ["USERPROFILE"] = str(WORK / "home")
os.environ["ANDROID_HOME"] = str(sdk)
check("android adb comes from ANDROID_HOME", Path(adb_driver._adb_path()) == sdk_adb)
del os.environ["ANDROID_HOME"]
os.environ["LOCALAPPDATA"] = str(WORK / "localappdata")
win_sdk = WORK / "localappdata" / "Android" / "Sdk"
shutil.copytree(sdk, win_sdk)
check("android adb found in Android Studio's Windows default", Path(adb_driver._adb_path()).parent == win_sdk / "platform-tools")
shutil.rmtree(win_sdk)
try:
    adb_driver._adb_path()
    check("android without any adb raises", False)
except RuntimeError as e:
    check("android without any adb raises", "ANDROID_HOME" in str(e))
for k, v in saved.items():
    os.environ.pop(k, None)
    if v is not None:
        os.environ[k] = v
srv.shutdown()
shutil.rmtree(WORK, ignore_errors=True)

print(f"drivers: pass={passed} fail={failed}")
sys.exit(1 if failed else 0)
