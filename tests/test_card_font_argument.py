"""The font the README card scripts take is not in this repo, and nothing said so.

`docs/workflows/press.md` step 2 is where a contributor redraws `docs/featured.png` and `docs/card.jpg`, and
it prints two commands that pass `Fredoka.ttf` as the first argument. No folder of this repo holds that file -
Fredoka is the variable TTF from Google Fonts, which only `tools/readme_stats.py`'s docstring ever said - so
a contributor who installed Pillow as the page asks and then ran the command the page prints got:

    OSError: cannot open resource

with no file name in it and no way to tell whether the font, the argument order or the draw call was wrong.
Before that, running any of the three with no arguments at all died on `IndexError: list index out of range`,
because each one read `sys.argv[1], sys.argv[2]` at the top of the module.

The three scripts now take the font through one guard: it names the path it could not open, says where the
font comes from, and prints the two arguments when there are not two. It runs before the Pillow import, since
the font is the argument the reader brings themselves and a missing one is the likelier failure - so a run
with no Pillow still reports the font first, which is what makes this testable in CI, where Pillow is absent.

`tools/gen_tables.py --font` hands the font to two of these scripts with `check=True`, so a wrong path there
became a `CalledProcessError` traceback around their message; it now refuses the path itself.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PRESS = ROOT / "docs" / "workflows" / "press.md"

# The three scripts that draw the card, with the picture each one writes.
CARD_SCRIPTS = {
    "readme_stats.py": "stats.png",
    "readme_featured.py": "featured.png",
    "readme_card.py": "card.jpg",
}

# What the guard says the reader cannot use, and what a wrong path must not be mistaken for.
NOT_THE_FONT = "requirements-perf.txt"


def shadow_dir(tmp):
    """A PIL package that cannot be imported, so a script behaves as on a venv without Pillow."""
    pkg = Path(tmp) / "PIL"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text('raise ImportError("No module named \'PIL\'")\n', encoding="utf-8")
    return str(tmp)


def run(argv, tmp):
    env = dict(os.environ)
    env["PYTHONPATH"] = shadow_dir(tmp)
    return subprocess.run([sys.executable, *argv], cwd=ROOT, env=env, capture_output=True, text=True)


class FontArgumentTest(unittest.TestCase):
    def test_the_shadow_really_hides_pillow(self):
        # Without this every check below could be reading the Pillow line and proving nothing.
        with tempfile.TemporaryDirectory() as tmp:
            done = run(["-c", "import PIL"], tmp)
        self.assertNotEqual(done.returncode, 0, "the PIL shadow did not take effect")

    def test_a_font_that_is_not_there_is_reported_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, picture in CARD_SCRIPTS.items():
                with self.subTest(script=name):
                    out = Path(tmp) / picture
                    done = run([str(TOOLS / name), "Fredoka.ttf", str(out)], tmp)
                    self.assertNotEqual(done.returncode, 0, f"{name} accepted a font that does not exist")
                    self.assertIn("Fredoka.ttf", done.stderr, f"{name} does not name the font it could not open")
                    self.assertNotIn("Traceback", done.stderr, f"{name} still dies on a bare traceback")
                    self.assertNotIn(NOT_THE_FONT, done.stderr,
                                     f"{name} reports the font only after the Pillow import, so a reader without "
                                     "Pillow never sees it")
                    self.assertFalse(out.exists(), f"{name} wrote {out} before it had a font")

    def test_the_font_is_checked_before_the_pillow_import(self):
        # A path in the message plus no Pillow line in it is only possible if the guard sits first: this
        # reads the two apart in the source, in each script.
        for name in CARD_SCRIPTS:
            with self.subTest(script=name):
                text = (TOOLS / name).read_text(encoding="utf-8")
                guard = text.find("font_and_out(sys.argv)")
                pillow = text.find("from PIL import")
                self.assertGreater(guard, 0, f"{name} does not call the font guard")
                self.assertGreater(pillow, 0, f"{name} no longer imports Pillow, so this check would prove nothing")
                self.assertLess(guard, pillow, f"{name} checks the font after importing Pillow")

    def test_no_arguments_prints_the_two_it_takes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in CARD_SCRIPTS:
                with self.subTest(script=name):
                    done = run([str(TOOLS / name)], tmp)
                    self.assertNotEqual(done.returncode, 0, f"{name} ran with no arguments")
                    self.assertIn("usage:", done.stderr, f"{name} does not print how it is called")
                    self.assertIn(name, done.stderr, f"{name}'s usage line does not name the script")
                    self.assertNotIn("Traceback", done.stderr, f"{name} still dies on a bare traceback")

    def test_one_argument_is_not_enough(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in CARD_SCRIPTS:
                with self.subTest(script=name):
                    done = run([str(TOOLS / name), "Fredoka.ttf"], tmp)
                    self.assertIn("usage:", done.stderr, f"{name} took one argument as a full command")

    def test_a_font_that_exists_gets_past_the_guard(self):
        # The guard must not swallow a path that is there: the next thing that goes wrong is Pillow.
        with tempfile.TemporaryDirectory() as tmp:
            font = Path(tmp) / "Fredoka.ttf"
            font.write_bytes(b"")
            for name, picture in CARD_SCRIPTS.items():
                with self.subTest(script=name):
                    done = run([str(TOOLS / name), str(font), str(Path(tmp) / picture)], tmp)
                    self.assertIn(NOT_THE_FONT, done.stderr, f"{name} rejected a font path that exists")
                    self.assertNotIn("cannot open the font at", done.stderr,
                                     f"{name} still reports the font it was given")


class GenTablesFontTest(unittest.TestCase):
    """gen_tables.py --font runs two of those scripts, so it has to refuse a wrong path itself."""

    def check(self, *args):
        """`gen_tables.py <args> --check` on this tree."""
        return subprocess.run([sys.executable, str(TOOLS / "gen_tables.py"), *args, "--check"],
                              cwd=ROOT, capture_output=True, text=True)

    def test_a_font_that_is_not_there_is_refused_before_anything_is_written(self):
        done = self.check("--font", "Fredoka.ttf")
        self.assertEqual(done.returncode, 2, "gen_tables.py --font accepted a font that does not exist")
        self.assertIn("Fredoka.ttf", done.stderr, "gen_tables.py does not name the font it could not open")
        self.assertNotIn("Traceback", done.stderr, "gen_tables.py died with a traceback")

    def test_an_existing_font_leaves_the_check_verdict_alone(self):
        # The verdict itself is the branch's business, not this suite's: --check exits 0 where the tables
        # are current (main, whose CI job runs it after merging) and 1 on any branch that adds a list
        # folder, which is exactly what docs/workflows/tv-list.md tells a list PR to do - "a maintainer
        # runs tools/gen_tables.py after merging". So what is held here is that handing --font does not
        # change that verdict, and that neither run turns into a refusal or a traceback.
        with tempfile.TemporaryDirectory() as tmp:
            font = Path(tmp) / "Fredoka.ttf"
            font.write_bytes(b"")
            plain = self.check()
            with_font = self.check("--font", str(font))
        self.assertIn(plain.returncode, (0, 1),
                      f"gen_tables.py --check exited {plain.returncode}: {plain.stdout}{plain.stderr}")
        self.assertNotIn("Traceback", plain.stdout + plain.stderr, "gen_tables.py --check died with a traceback")
        self.assertEqual(with_font.returncode, plain.returncode,
                         "handing --font changed what --check says about the tables")


COMMAND = re.compile(r"`(tools/readme_[\w]+\.py [^`]*)`")   # a command: the script and what it is given


class PressRecipeShapeTest(unittest.TestCase):
    """The commands the page prints have to be the two-argument shape the scripts now insist on."""

    def commands(self):
        return COMMAND.findall(PRESS.read_text(encoding="utf-8"))

    def test_the_page_prints_the_redraw_commands(self):
        named = {cmd.split()[0] for cmd in self.commands()}
        self.assertEqual({"tools/readme_featured.py", "tools/readme_card.py"}, named,
                         "press.md no longer prints both redraw commands, so this check would prove nothing")

    def test_each_command_passes_two_arguments_and_writes_a_picture_the_repo_has(self):
        for cmd in self.commands():
            with self.subTest(command=cmd):
                parts = cmd.split()
                self.assertEqual(3, len(parts), f"press.md prints '{cmd}', which is not <script> <font> <picture>")
                self.assertTrue((ROOT / parts[0]).is_file(), f"press.md names {parts[0]}, which is not in the repo")
                self.assertTrue((ROOT / parts[2]).is_file(),
                                f"press.md writes {parts[2]}, which the repo does not ship")

    def test_the_page_says_the_font_is_not_in_the_repo(self):
        # The one fact a reader cannot get from the commands themselves: the font path is theirs to supply.
        text = PRESS.read_text(encoding="utf-8")
        self.assertIn("Google Fonts", text, "press.md prints a font path without saying where the font comes from")
        self.assertIn("not in the repo", text, "press.md prints a font path without saying it is not in the repo")


if __name__ == "__main__":
    unittest.main()
