"""The Connecting page says which ADB key `tools/tv.py` uses, and what to delete when the TV refuses it.

`tools/tv.py` keeps a key of its own in `tools/adbkey/` and falls back to the stock `~/.android/adbkey`
only while it has not made one (`if not os.path.exists(KEY) and os.path.exists(ADB_KEY)`). So a set that
was first reached with this client is asked again for a key the stock `adb` never registered: #1526 is a
TCL 55C61B whose `tv.py` had made its own key in `tools/adbkey` before the TV approved the stock adb key,
and the set stayed `unauthorized` until that folder was deleted and the next run reused
`~/.android/adbkey`.

The page described the fallback as if it always applied, which is exactly the case it does not cover, and
it gave no way out. Both halves are pinned here: what the code does (a throwaway tree with a stub
adb_shell that records the key handed to the TV, so no adb_shell and no TV are needed) and what the page
says. If the fallback ever becomes unconditional, the source test fails and the bullet has to be rewritten
rather than left describing the old rule.

Run from the repository root: python3 -m unittest discover -s tests -v
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "TROUBLESHOOTING.md"
TVPY = ROOT / "tools" / "tv.py"
SECTION = "## Connecting"

STOCK_PUB = "stock-adb-key"
OWN_PUB = "made-by-tv-py"
GENERATED_PUB = "generated-by-tv.py"

# Enough of adb_shell for tv.py to import; connect() records the key it was handed instead of dialling.
STUB_DEVICE = (
    "import os\n"
    "class AdbDeviceTcp:\n"
    "    def __init__(self, host, port, **kwargs):\n"
    "        self.host, self.port = host, port\n"
    "    def connect(self, rsa_keys=None, **kwargs):\n"
    "        with open(os.environ['KEY_OUT'], 'w') as f:\n"
    "            f.write(rsa_keys[0].pub)\n"
    "    def shell(self, cmd, **kwargs):\n"
    "        return 'x'\n"
    "    def close(self):\n"
    "        pass\n"
)
STUB_SIGNER = (
    "class PythonRSASigner:\n"
    "    def __init__(self, pub, priv):\n"
    "        self.pub, self.priv = pub, priv\n"
)
STUB_KEYGEN = (
    "def keygen(filepath):\n"
    "    with open(filepath, 'wb') as f:\n"
    "        f.write(b'private')\n"
    "    with open(filepath + '.pub', 'wb') as f:\n"
    "        f.write(b'" + GENERATED_PUB + "')\n"
)


def connecting(text=None):
    """The Connecting section of the page, or an empty string when the heading is gone."""
    text = PAGE.read_text(encoding="utf-8") if text is None else text
    start = text.find(SECTION)
    if start == -1:
        return ""
    rest = text[start + len(SECTION):]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def bullets(section):
    """The section's `- ` bullets with their wrapped lines joined onto the first one.

    A bullet continues on the indented lines under it; anything else - a paragraph, the next heading -
    ends it, so prose that mentions a path is not read as a bullet.
    """
    out = []
    continuing = False
    for line in section.splitlines():
        if line.startswith("- "):
            out.append(line[2:].strip())
            continuing = True
        elif continuing and line.startswith("  ") and line.strip():
            out[-1] += " " + line.strip()
        else:
            continuing = False
    return out


class ReaderTest(unittest.TestCase):
    """The two readers above have to see what the page really lays out."""

    def test_wrapped_bullet_is_one_bullet(self):
        said = bullets("## Connecting\n\n- **a** first line\n  second line\n  third\n\n- b\n")
        self.assertEqual(said, ["**a** first line second line third", "b"])

    def test_prose_outside_a_bullet_is_not_a_bullet(self):
        said = bullets("## Connecting\n\nA paragraph naming `tools/adbkey` and `~/.android/adbkey`.\n\n- b\n")
        self.assertEqual(said, ["b"])

    def test_section_stops_at_the_next_heading(self):
        said = connecting("## Connecting\n\n- keep\n\n## Working on the TV\n\n- drop\n")
        self.assertIn("keep", said)
        self.assertNotIn("drop", said)

    def test_a_page_without_the_section_reads_as_empty(self):
        self.assertEqual(connecting("# Nothing here\n\n- drop\n"), "")


class PageTest(unittest.TestCase):
    def test_the_page_still_has_a_connecting_section_to_read(self):
        section = connecting()
        self.assertTrue(section, "docs/TROUBLESHOOTING.md has no '## Connecting' section")
        self.assertGreaterEqual(len(bullets(section)), 10,
                                "the Connecting section read fewer than 10 bullets, so the checks below "
                                "could pass by reading nothing")

    def test_one_bullet_names_the_key_this_client_keeps(self):
        said = [b for b in bullets(connecting()) if "tools/adbkey" in b]
        self.assertEqual(len(said), 1, f"{len(said)} bullets name tools/adbkey: {said}")
        bullet = said[0]
        for needle, why in (
            ("~/.android/adbkey", "the stock key the next run falls back to"),
            ("unauthorized", "what the TV answers while it is not trusted"),
            ("rm -rf tools/adbkey", "the way out"),
            ("rmdir /s /q", "the same on Windows"),
            ("--probe", "the run that picks the stock key up"),
            ("#1526", "the report"),
        ):
            self.assertIn(needle, bullet, f"the tools/adbkey bullet does not name {why} ({needle!r})")


    def test_the_fallback_is_not_described_without_its_condition(self):
        said = [b for b in bullets(connecting()) if "~/.android/adbkey" in b]
        self.assertTrue(said, "nothing in the Connecting section names the stock ~/.android/adbkey")
        for bullet in said:
            self.assertIn("tools/adbkey", bullet,
                          "a bullet promises the stock key without saying that a key of tv.py's own in "
                          "tools/adbkey wins while that folder exists - the case #1526 was stuck in")


class FallbackTest(unittest.TestCase):
    """What tv.py actually hands the TV, run against a copy of the script in a throwaway tree."""

    def probe(self, own_key=False, stock_key=False, stock_pub=True):
        """Run `tv.py --probe` in a tree of its own; return (result, the public key sent to the TV)."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)

        tools = tmp / "tools"
        tools.mkdir(parents=True)
        shutil.copy2(TVPY, tools / "tv.py")

        stub = tmp / "stub" / "adb_shell"
        (stub / "auth").mkdir(parents=True)
        (stub / "__init__.py").write_text("")
        (stub / "adb_device.py").write_text(STUB_DEVICE)
        (stub / "auth" / "__init__.py").write_text("")
        (stub / "auth" / "keygen.py").write_text(STUB_KEYGEN)
        (stub / "auth" / "sign_pythonrsa.py").write_text(STUB_SIGNER)

        home = tmp / "home"
        (home / ".android").mkdir(parents=True)
        if stock_key:
            (home / ".android" / "adbkey").write_text("private")
            if stock_pub:
                (home / ".android" / "adbkey.pub").write_text(STOCK_PUB)
        if own_key:
            (tools / "adbkey").mkdir()
            (tools / "adbkey" / "adbkey").write_text("private")
            (tools / "adbkey" / "adbkey.pub").write_text(OWN_PUB)

        out = tmp / "key-out.txt"
        env = dict(os.environ, TV_HOST="127.0.0.1", HOME=str(home), KEY_OUT=str(out),
                   PYTHONPATH=os.pathsep.join([str(tmp / "stub"), str(tools)]))
        result = subprocess.run([sys.executable, str(tools / "tv.py"), "--probe"],
                                cwd=str(tmp), env=env, capture_output=True, text=True, timeout=120)
        sent = out.read_text().strip() if out.exists() else ""
        return result, sent

    def test_the_stock_key_is_used_while_the_client_has_none(self):
        result, sent = self.probe(stock_key=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sent, STOCK_PUB,
                         "tv.py did not reuse ~/.android/adbkey, so a set that trusts platform-tools' "
                         "key is asked again for this client's")

    def test_a_key_of_its_own_wins_over_the_stock_one(self):
        # The state #1526 was stuck in: the folder already exists, so the stock key is never looked at.
        result, sent = self.probe(own_key=True, stock_key=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sent, OWN_PUB,
                         "tv.py now prefers ~/.android/adbkey over a key of its own: check that the "
                         "Connecting bullet still describes what it does, then rewrite both")

    def test_its_own_key_is_made_beside_the_script(self):
        result, sent = self.probe()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sent, GENERATED_PUB,
                         "tv.py made no key of its own, so the folder the page tells a reader to delete "
                         "would never exist")

    def test_the_fallback_needs_the_public_half_too(self):
        result, sent = self.probe(stock_key=True, stock_pub=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sent, GENERATED_PUB,
                         "tv.py reused a ~/.android/adbkey that has no .pub beside it")


class SourceTest(unittest.TestCase):
    def test_the_fallback_is_still_conditional_on_its_own_key(self):
        source = TVPY.read_text(encoding="utf-8")
        self.assertIn("if not os.path.exists(KEY) and os.path.exists(ADB_KEY)", source,
                      "tv.py's key choice changed: the Connecting bullet's rule has to follow it")
        self.assertIn("KEY = ADB_KEY", source)


if __name__ == "__main__":
    unittest.main()
