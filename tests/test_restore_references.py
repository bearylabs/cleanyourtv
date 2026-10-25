"""Every undo step in the repo names a file that is there: the list, and a folder's own script.

restore.sh takes the same list that disable.sh ran against (#239): recovery.py reads it, checks every
name against the record taken before the change and prints the batch. So the name in a page's undo
step is what an owner types when the TV looks wrong. A name that is not there is refused before a
single command reaches the TV, which is the worst moment to find out.

The same goes for the install and restore scripts three list folders still ship from before the rule
that a list folder holds none (AGENTS.md, "Hard rules"): a page that sends an owner to
`examples/<folder>/restore.sh` names a file the folder has to have, and the TCL 55S470G header
named one that was not there.

And a command that passes the stock launcher but no list names nothing at all: restore.sh takes the
list as its first argument and the stock launcher as its second, so the CVTE T972 page's
`tools/restore.sh ... com.cvte.tv.launcher.highend` was refused before a single package came back,
which the reference pattern above never read because there was no `.txt` in the line.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Same walk as tests/test_markdown_links.py: the tools venv CI builds and a launcher build are not docs.
PRUNE = {".git", "venv", "node_modules", "build", ".gradle", "__pycache__"}
SUFFIXES = (".md", ".txt", ".sh", ".ps1")
# `tools/restore.sh examples/x/debloat.txt com.stock.launcher`, and the PowerShell twin.
REFERENCE = re.compile(r"restore\.(?:sh|ps1)\s+([A-Za-z0-9_./<>-]*\.txt)")
# A helper script inside a list folder, e.g. `examples/epson-ls800/restore.sh`. Three folders still
# ship the install and restore scripts their submission came with (#265); a page or a list header
# that sends an owner to one names a file the folder has to have.
FOLDER_SCRIPT = re.compile(r"(examples/[A-Za-z0-9._-]+/(?:restore|disable|install|build-and-install)\."
                           r"(?:sh|ps1))")
# `tools/restore.sh <list> <stock launcher>`: the list is restore.sh's first argument, the stock
# launcher its second (see its usage line and LIST=${1:?} / STOCK=${2:-...}). Both arguments are
# matched with no `.txt` required in the pattern, so a command that leaves the list out is read too.
PAIR = re.compile(r"tools[/\\]restore\.sh\s+(\S+)\s+(\S+)")
PACKAGE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+")
# A token as a page wraps it: `code`, "quoted", and the punctuation that ends the sentence.
WRAPPER = "`'\",;."


def unwrapped(token):
    """The argument a reader would type, without the backticks, quotes and full stop around it."""
    return token.strip(WRAPPER).rstrip(".")


# Every list a reader can run. A page outside examples/ that needs one names that file too.
LIST_FOLDERS = ROOT / "examples"


def references(text):
    """The list names a line of text hands to restore.sh, placeholders like <your tv> left out."""
    return [name for name in REFERENCE.findall(text) if "<" not in name and ">" not in name]


def walk(root):
    """(relative path, text) for every page, list and script under root, in a stable order."""
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = sorted(d for d in subdirectories if d not in PRUNE)
        for name in sorted(files):
            if not name.endswith(SUFFIXES):
                continue
            path = Path(directory) / name
            yield path.relative_to(root), path.read_text(encoding="utf-8", errors="replace")


def read_references(root):
    """(file, name) for every restore.sh reference under root, as a reader would copy it."""
    found = []
    for path, text in walk(root):
        for target in references(text):
            found.append((path, target))
    return found


def script_references(text):
    """The helper scripts inside a list folder a line names, placeholders left out."""
    return [name for name in FOLDER_SCRIPT.findall(text) if "<" not in name and ">" not in name]


def read_script_references(root):
    """(file, name) for every `examples/<folder>/<script>` reference under root."""
    found = []
    for path, text in walk(root):
        for target in script_references(text):
            found.append((path, target))
    return found


def restore_commands(root):
    """(file, line number, first argument, second argument) for every two-argument tools/restore.sh.

    Only the lines that hand it something package-shaped second are read: those are commands passing
    the stock launcher, and restore.sh's stock launcher is its second argument.
    """
    found = []
    for path, text in walk(root):
        for number, line in enumerate(text.splitlines(), 1):
            for first, second in PAIR.findall(line):
                if PACKAGE.fullmatch(unwrapped(second)):
                    found.append((path, number, first, second))
    return found


def commands_without_a_list(root):
    """(file, line, first argument, second argument) for the ones whose first argument is no list."""
    return [(path, number, first, second) for path, number, first, second in restore_commands(root)
            if not unwrapped(first).endswith(".txt") and "<" not in first]


class RestoreReferencesTest(unittest.TestCase):
    def test_every_reference_names_a_list_that_is_there(self):
        missing = [(str(path), name) for path, name in read_references(ROOT)
                   if not (ROOT / name).is_file()]
        self.assertEqual([], missing,
                         "these lines restore with a list that is not in the repo, so recovery.py "
                         "refuses them and nothing is re-enabled")

    def test_each_list_undo_replays_that_same_list(self):
        # restore.sh replays the list disable.sh ran against, so a list's own undo names that file:
        # 237 of the 238 references in examples/ already do.
        wrong = []
        for path, name in read_references(ROOT):
            own = path.as_posix()
            if own.startswith(LIST_FOLDERS.relative_to(ROOT).as_posix() + "/") and path.name == "debloat.txt" \
                    and name != own:
                wrong.append((own, name))
        self.assertEqual([], wrong, "a list's undo points somewhere else, so it replays another set "
                                    "of packages or nothing at all")

    def test_a_folder_script_a_page_names_is_there(self):
        # examples/epson-ls800, anker-nebula-d2426 and tcl-43c645 ship the install and restore scripts
        # they came with, and their pages name them; the TCL 55S470G header named one its folder does
        # not have, so an owner's first undo command was "No such file".
        missing = [(str(path), name) for path, name in read_script_references(ROOT)
                   if not (ROOT / name).is_file()]
        self.assertEqual([], missing,
                         "these lines hand the owner a script inside a list folder that is not in the "
                         "repo, so the command fails before anything reaches the TV")
        self.assertGreaterEqual(len(read_script_references(ROOT)), 4,
                                "the folders that do ship such a script should be read; the scanner "
                                "found fewer")

    def test_a_restore_that_names_the_launcher_names_the_list(self):
        # The CVTE T972 page sent an owner to `tools/restore.sh ... com.cvte.tv.launcher.highend`: the
        # stock launcher in the list's place, so restore.sh exits on its usage line with "usage:
        # restore.sh <debloat list> [stock launcher package]" and nothing is re-enabled - at the moment
        # the TV looks wrong. 168 of the 169 two-argument commands under this repo pass the list first.
        found = restore_commands(ROOT)
        self.assertGreaterEqual(len(found), 100,
                                "the repo-wide sweep should read every restore command that passes the "
                                "stock launcher; it found fewer, so it cannot fail on one")
        wrong = [(str(path), number, first, second)
                 for path, number, first, second in commands_without_a_list(ROOT)]
        self.assertEqual([], wrong,
                         "these lines hand restore.sh a stock launcher and no list, so it stops on its "
                         "usage line before recovery.py runs and nothing comes back")

    def test_restore_takes_the_list_first_and_the_launcher_second(self):
        # The sweep above is only right while that is the order; if restore.sh swaps or drops an
        # argument, this fails instead of the page being blamed for a script change.
        text = (ROOT / "tools" / "restore.sh").read_text(encoding="utf-8")
        self.assertIn('LIST="${1:', text,
                      "restore.sh no longer takes the list as its first argument, so the rule above "
                      "(and the undo lines it checks) no longer match the script")
        self.assertIn('STOCK="${2:', text,
                      "restore.sh no longer takes the stock launcher as its second argument")

    # ---- the reader itself, so the two tests above cannot pass by reading nothing ---------------

    def write(self, root, path, text):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def test_a_missing_list_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md",
                       "Undo: TV_HOST=<tv ip> tools/restore.sh examples/gone/debloat.txt\n")
            found = read_references(root)
            self.assertEqual([(Path("docs/page.md"), "examples/gone/debloat.txt")], found)
            self.assertFalse((root / found[0][1]).is_file())

    def test_a_list_that_is_there_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "examples/kept/debloat.txt", "com.example.one\n")
            self.write(root, "docs/page.md",
                       "Undo: tools/restore.sh examples/kept/debloat.txt com.example.stock\n")
            found = read_references(root)
            self.assertEqual([(Path("docs/page.md"), "examples/kept/debloat.txt")], found)
            self.assertTrue((root / found[0][1]).is_file())

    def test_the_powershell_twin_is_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md", "Undo: tools\\restore.ps1 examples/x/debloat.txt\n")
            self.assertEqual([(Path("docs/page.md"), "examples/x/debloat.txt")], read_references(root))

    def test_a_placeholder_is_not_a_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "README.md",
                       "TV_HOST=192.168.1.50 tools/restore.sh examples/<your tv>/debloat.txt\n"
                       "Pass the list you ran disable with to `tools/restore.sh`.\n")
            self.assertEqual([], read_references(root))

    def test_a_build_tree_is_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "tools/venv/lib/page.md",
                       "Undo: tools/restore.sh examples/gone/debloat.txt\n")
            self.assertEqual([], read_references(root))

    def test_a_missing_folder_script_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "examples/kept/debloat.txt",
                       "# Undo: TV_HOST=<tv ip> examples/kept/restore.sh\n")
            self.assertEqual([(Path("examples/kept/debloat.txt"), "examples/kept/restore.sh")],
                             read_script_references(root))
            self.assertFalse((root / "examples/kept/restore.sh").is_file())

    def test_a_folder_script_that_is_there_resolves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "examples/kept/restore.sh", "#!/usr/bin/env bash\n")
            self.write(root, "examples/kept/README.md",
                       "TV_HOST=<tv ip> examples/kept/restore.sh   # undo\n")
            found = read_script_references(root)
            self.assertEqual([(Path("examples/kept/README.md"), "examples/kept/restore.sh")], found)
            self.assertTrue((root / found[0][1]).is_file())

    def test_a_placeholder_folder_script_is_not_a_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "README.md",
                       "TV_HOST=<tv ip> examples/<your tv>/restore.sh\n"
                       "A folder with a `restore.sh` of its own is not the rule here.\n")
            self.assertEqual([], read_script_references(root))

    def test_a_launcher_without_a_list_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "examples/cvte/debloat.txt", "com.example.one\n")
            self.write(root, "examples/cvte/README.md",
                       "- Undo with `tools/restore.sh ... com.cvte.tv.launcher.highend`.\n")
            self.assertEqual([(Path("examples/cvte/README.md"), 1, "...",
                               "com.cvte.tv.launcher.highend`.")],
                             commands_without_a_list(root))

    def test_a_launcher_with_its_list_is_quiet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "examples/cvte/debloat.txt", "com.example.one\n")
            self.write(root, "examples/cvte/README.md",
                       "- Undo with `TV_HOST=<tv ip> tools/restore.sh examples/cvte/debloat.txt "
                       "com.cvte.tv.launcher.highend`.\n")
            self.assertEqual([(Path("examples/cvte/README.md"), 1, "examples/cvte/debloat.txt",
                               "com.cvte.tv.launcher.highend`.")],
                             restore_commands(root))
            self.assertEqual([], commands_without_a_list(root))

    def test_a_quoted_list_is_read_as_the_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md",
                       "Undo: tools/restore.sh \"examples/kept/debloat.txt\" com.example.stock\n")
            self.assertEqual([], commands_without_a_list(root))

    def test_a_command_that_passes_only_the_list_is_not_a_pair(self):
        # One argument is the list alone: restore.sh then uses its default stock launcher, which is
        # what 168 lists rely on, so it is not a command that forgot the list.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md", "Undo: tools/restore.sh examples/kept/debloat.txt\n")
            self.assertEqual([], restore_commands(root))

    def test_prose_about_restore_sh_is_not_a_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md",
                       "restore.sh would turn them ON, and `tools/restore.sh` takes the list first.\n")
            self.assertEqual([], restore_commands(root))

    def test_the_powershell_twin_is_a_named_parameter_command(self):
        # restore.ps1 takes -List and -Stock and has no package-shaped bare argument, so none of this
        # is read as a two-argument bash command.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "docs/page.md",
                       "Undo: tools\\restore.ps1 -TvHost 192.168.1.50 -Stock com.example.stock "
                       "-List examples\\kept\\debloat.txt\n")
            self.assertEqual([], restore_commands(root))


if __name__ == "__main__":
    unittest.main()
