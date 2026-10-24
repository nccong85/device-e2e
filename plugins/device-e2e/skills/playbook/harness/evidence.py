"""Evidence files named as the results check expects: `<root>/<case>_<platform>_<n>.<ext>`.

    ev = Evidence(driver, "E3", root=summary_dir / "evidence")   # next to the summary, where the check looks
    mark = driver.log_mark()          # before the step that may fail
    ...
    ev.shot()                         # <summary dir>/evidence/E3_android_1.png
    ev.tree()                         # evidence/E3_android_2.xml, the UI tree the check read
    ev.failure(mark)                  # screenshot, tree and the device log since the mark

`n` continues after the highest number already in the folder, so a re-run never overwrites the first run's files.
"""
import re
import time
from pathlib import Path

CASE_ID = re.compile(r"[A-Za-z][A-Za-z0-9-]*")


class Evidence:
    def __init__(self, driver, case, root="evidence"):
        if not CASE_ID.fullmatch(case):
            raise ValueError(f"case id {case!r} must be letters, digits and dashes, e.g. E3")
        self.driver = driver
        self.case = case
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, ext):
        prefix = f"{self.case}_{self.driver.platform}_"
        taken = [
            int(m.group(1))
            for p in self.root.iterdir()
            if (m := re.fullmatch(re.escape(prefix) + r"(\d+)\.\w+", p.name))
        ]
        return self.root / f"{prefix}{max(taken, default=0) + 1}.{ext.lstrip('.')}"

    def shot(self):
        return Path(self.driver.screenshot(self.path("png")))

    def tree(self):
        return self.driver.dump_tree(self.path(self.driver.tree_ext))

    def burst(self, count, interval):
        """Screenshots every `interval` seconds: the record of a transition on a phone that cannot film it."""
        shots = []
        for i in range(count):
            if i:
                time.sleep(interval)
            shots.append(self.shot())
        return shots

    def failure(self, since=None):
        """What a FAIL report needs: the screen, the tree, and the device's log or crash reports since `since`
        (a `driver.log_mark()` taken before the step). Without a mark, the last minute."""
        if since is None:
            since = self.driver.log_mark(-60)
        files = []
        for grab in (self.shot, self.tree):
            try:
                files.append(grab())
            except Exception as e:  # the app may be gone; keep collecting
                files.append(f"{grab.__name__} failed: {e}")
        try:
            files.extend(self.driver.device_log(self, since))
        except Exception as e:
            files.append(f"device log failed: {e}")
        return files
