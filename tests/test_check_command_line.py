"""tools/check.py reads its command line before it reads a list or a TV.

README.md hands an owner a weekly job that runs `check.py <list>` and says "it prints what drifted and
exits 1 when anything did", so on that page exit 1 means "your TV drifted". A command line that cannot
run must therefore not come back as 1: `check.py --help` - the first thing a reader types at a script
they do not know - was taken as a list named `--help` and ended in a FileNotFoundError traceback with
exit 1, and a flag typed where the launcher package goes reached set-home-activity as a package name.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_drift_check import FAKE_TV  # noqa: E402  (the simulated TV check.py already runs against)

ROOT = Path(__file__).resolve().parents[1]
STOCK = "com.google.android.tvlauncher"
CUSTOM = "com.gathin.tvhome"


def collapsed(text):
    return " ".join(text.split())


class CheckCommandLineTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.repo = self.base / "repo"
        tools = self.repo / "tools"
        tools.mkdir(parents=True)
        for name in ("check.py", "recovery.py"):
            shutil.copy2(ROOT / "tools" / name, tools / name)
        (tools / "tv.py").write_text(FAKE_TV)

        self.home = self.base / "home"
        self.home.mkdir()
        self.state_path = self.base / "tv-state.json"
        self.list_path = self.base / "debloat.txt"
        self.list_path.write_text("# My TV\ncom.example.music\ncom.example.store\n" + STOCK + "\n")

    def tv(self, **overrides):
        state = {
            "installed": ["com.example.music", "com.example.store", STOCK, CUSTOM],
            "disabled": ["com.example.music", "com.example.store", STOCK],
            "home": f"{CUSTOM}/.MainActivity",
            "home_activities": [f"{CUSTOM}/.MainActivity", f"{STOCK}/.MainActivity"],
            "pinned": [],
            "commands": [],
            "unreachable": False,
            "wifi": "",
            "input_drivers": [],
        }
        state.update(overrides)
        self.state_path.write_text(json.dumps(state))

    def run_check(self, *args):
        env = dict(os.environ, TV_HOST="192.168.1.50", HOME=str(self.home),
                   FAKE_TV_STATE=str(self.state_path))
        return subprocess.run(
            [sys.executable, str(self.repo / "tools" / "check.py"), *args],
            cwd=self.repo, env=env, capture_output=True, text=True, timeout=120,
        )

    def sent(self):
        with open(self.state_path) as f:
            return json.load(f)["commands"]

    def assert_untouched(self, result):
        """Nothing reached the TV, and the run did not die on an exception."""
        self.assertEqual(self.sent(), [])
        self.assertNotIn("Traceback", result.stderr)

    def test_help_prints_the_usage_and_leaves_the_tv_alone(self):
        self.tv()
        result = self.run_check("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: check.py <debloat list> [launcher package]", result.stdout)
        self.assertIn("check.py --fix <debloat list> [launcher package]", result.stdout)
        self.assertIn("check.py --help", result.stdout)
        self.assertEqual(result.stderr, "")
        self.assert_untouched(result)

    def test_help_exits_zero_rather_than_the_drift_code(self):
        # The whole point: 1 is what a weekly job reports as "the TV drifted".
        self.tv()
        self.assertNotEqual(self.run_check("--help").returncode, 1)

    def test_short_help_is_the_same_note(self):
        self.tv()
        long, short = self.run_check("--help"), self.run_check("-h")
        self.assertEqual(short.returncode, 0, short.stderr)
        self.assertEqual(short.stdout, long.stdout)
        self.assert_untouched(short)

    def test_help_wins_over_the_fix_flag(self):
        self.tv()
        result = self.run_check("--fix", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: check.py", result.stdout)
        self.assert_untouched(result)

    def test_help_after_the_list_still_prints_the_note(self):
        self.tv()
        result = self.run_check(str(self.list_path), "-h")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: check.py", result.stdout)
        self.assert_untouched(result)

    def test_unknown_flag_is_refused_by_name(self):
        self.tv()
        result = self.run_check("--fx")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no such flag: --fx", result.stderr)
        self.assertIn("usage: check.py", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assert_untouched(result)

    def test_unknown_flag_where_the_launcher_goes_never_reaches_the_tv(self):
        # Second position used to be taken as the launcher package: --fix would have run a
        # set-home-activity for a package called --fx.
        self.tv(disabled=["com.example.music", "com.example.store"])
        result = self.run_check("--fix", str(self.list_path), "--fx")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no such flag: --fx", result.stderr)
        self.assert_untouched(result)

    def test_a_single_dash_word_is_refused_too(self):
        self.tv()
        result = self.run_check(str(self.list_path), "-x")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no such flag: -x", result.stderr)
        self.assert_untouched(result)

    def test_a_list_that_is_not_there_is_named_not_traced(self):
        self.tv()
        missing = self.base / "typo.txt"
        result = self.run_check(str(missing))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("could not read", result.stderr)
        self.assertIn("typo.txt", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.sent(), [])

    def test_a_directory_is_refused_like_a_missing_file(self):
        self.tv()
        result = self.run_check(str(self.base))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("could not read", result.stderr)
        self.assertIn("Is a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.sent(), [])

    def test_no_argument_still_exits_2_with_the_usage(self):
        self.tv()
        result = self.run_check()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("usage: check.py", result.stderr)
        self.assert_untouched(result)

    def test_the_fix_flag_still_reaches_the_tv(self):
        # The guard must not have eaten --fix: one package came back, --fix disables it again.
        self.tv(disabled=[STOCK])
        result = self.run_check("--fix", str(self.list_path))
        self.assertEqual(result.returncode, 0, result.stderr)
        sent = self.sent()
        self.assertIn("pm disable-user --user 0 com.example.music", sent)
        self.assertIn("pm disable-user --user 0 com.example.store", sent)

    def test_the_usage_says_what_the_docstring_says(self):
        # One text, two places: the note a reader gets from --help is the one at the top of the file.
        source = (ROOT / "tools" / "check.py").read_text()
        docstring, usage = source.split('"""', 2)[1], source.split("USAGE = (", 1)[1]
        for fragment in ("check.py <debloat list> [launcher package]",
                         "check.py --fix <debloat list> [launcher package]"):
            self.assertIn(fragment, collapsed(docstring))
            self.assertIn(fragment, collapsed(usage))


if __name__ == "__main__":
    unittest.main()
