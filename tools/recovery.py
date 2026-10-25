#!/usr/bin/env python3
"""The state a debloat list is about to change, so that undo means undo (#239).

    recovery.py --save <debloat list>                read the TV and write the record
    recovery.py --commands <list> [stock launcher]   print a batch for tools/tv.py --batch that puts
                                                     the recorded states back

`tools/restore.sh` used to enable every package in the list, including ones the owner had already
disabled, and reset Home and the animation scales to fixed values instead of to what was there
before. Both scripts now go through this record: `disable.sh` writes it before the first command
reaches the TV, and `restore.sh` replays it.

Records live in ~/.cleanyourtv/, one per TV and list. The first one wins: a retry after a
half-applied list must not record the broken state as the original. A later run only adds the names
the list gained since then, with their state before this list disabled them.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

# Every name from the TV or from the list ends up inside a command run by the TV's shell, so nothing
# that could carry shell syntax is allowed through.
PACKAGE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+")
HOME_RE = re.compile(r"[A-Za-z_][\w.]*/[\w.$]+")
SCALE_RE = re.compile(r"-?\d+(\.\d+)?")
SETTINGS = ("window_animation_scale", "transition_animation_scale", "animator_duration_scale")
# This project's own launcher. When it already owned Home before debloating, restoring Home to it
# would leave the stock launcher off, so restore goes back to the stock one instead.
CUSTOM_LAUNCHER = "com.gathin.tvhome"
VERSION = 1
# Core Android packages no list may disable: with one of these off, Android itself can stop booting
# (#884: an original Mi TV Stick that lost its permission controller, package installer, ext services,
# module metadata and mainline overlays never came back). The content providers in CORE_OK are the
# exception, since tested lists turn them off and no TV feature uses them. disable.sh and disable.ps1
# carry the same two patterns (tests/test_core_packages.py keeps the three in step).
CORE_RE = re.compile(r"^(android|com\.android\.systemui|com\.android\.shell|com\.android\.phone|com\.android\.settings|com\.android\.tv\.settings|com\.(google\.)?android\.(permissioncontroller|packageinstaller|ext\.services|ext\.shared|modulemetadata)|com\.google\.android\.overlay\.modules.*|com\.android\.providers\..*)$")
CORE_OK = re.compile(r"^com\.android\.providers\.(calendar|contacts|userdictionary|blockednumber)$")


def core_packages(names):
    """The names in a list that must never be disabled, in list order."""
    return [n for n in names if CORE_RE.match(n) and not CORE_OK.match(n)]


def read_list(path):
    """Package names from a debloat list, in file order.

    A BOM and CRLF from a Windows editor are dropped, as is a trailing `# note`; anything that is not
    a bare package name stops the run before the TV is touched.
    """
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    names = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = line.split()[0]
        if not PACKAGE_RE.fullmatch(name):
            raise SystemExit(f"{path}:{number}: not a package name: {name!r}")
        names.append(name)
    if not names:
        raise SystemExit(f"{path}: no package names in this list")
    return names


def record_path(list_path, host):
    """One record per TV and list. The list is identified by its absolute path, so a copy of the
    same file somewhere else gets its own record."""
    tag = re.sub(r"[^A-Za-z0-9.-]", "_", host or "no-host")
    digest = hashlib.sha1(str(Path(list_path).resolve()).encode()).hexdigest()[:8]
    return Path.home() / ".cleanyourtv" / f"recovery-{tag}-{digest}.json"


def is_chooser(home):
    """Whether a Home component is Android's chooser rather than a launcher.

    When Home has no default, HOME resolves to android/com.android.internal.app.ResolverActivity
    (#85). Its package, "android", is not a package name a record can hold, and that is the test
    here: a launcher always has one.
    """
    return bool(home) and not PACKAGE_RE.fullmatch(home.split("/", 1)[0])


def load_record(path):
    try:
        with open(path) as f:
            record = json.load(f)
    except (OSError, ValueError) as e:
        raise SystemExit(f"{path}: not a usable recovery record ({e}).\n"
                         "It is left where it is: move it aside deliberately, a retry must not "
                         "replace the state recorded before the first change.")
    if record.get("version") != VERSION or not isinstance(record.get("packages"), dict):
        raise SystemExit(f"{path}: unknown recovery record format; move it aside deliberately.")
    # Records written before save() left the chooser out hold it as Home, and "android" among the
    # packages with it. Everything else in them is the TV before cleanup, and moving the file aside
    # would lose that: restore would then enable every listed package, and a new disable.sh run would
    # record the TV after cleanup as the original. So the chooser and that one entry are dropped here,
    # which reads the record the way save() writes it now. Any other bad name is still refused below,
    # and save() writes the record back this way only when the list has gained names.
    home = record.get("home")
    if isinstance(home, str) and HOME_RE.fullmatch(home) and is_chooser(home):
        record["packages"].pop(home.split("/", 1)[0], None)
        record["home"] = None
        sys.stderr.write(f"{path}: the recorded Home is Android's chooser ({home}), not a launcher; "
                         "reading it as no Home, so undo resolves the stock launcher.\n")
    # The record is replayed on the TV's shell, so it gets the same checks as the list and the TV's
    # answers did when it was written: a hand-edited or damaged file stops here, before any command.
    for name, state in record["packages"].items():
        if not PACKAGE_RE.fullmatch(name):
            raise SystemExit(f"{path}: not a usable recovery record (not a package name: {name!r}); "
                             "move it aside deliberately.")
        if state not in ("absent", "disabled", "enabled"):
            raise SystemExit(f"{path}: not a usable recovery record (unknown state for {name}: "
                             f"{state!r}); move it aside deliberately.")
    home = record.get("home")
    if home is not None and not (isinstance(home, str) and HOME_RE.fullmatch(home)):
        raise SystemExit(f"{path}: not a usable recovery record (not a Home component: {home!r}); "
                         "move it aside deliberately.")
    if not isinstance(record.get("settings", {}), dict):
        raise SystemExit(f"{path}: not a usable recovery record (settings is not a mapping); "
                         "move it aside deliberately.")
    return record


def write_record(path, record):
    # Written next to its final name first: a crash halfway through must not leave a truncated record
    # that then blocks every retry as "already recorded".
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w") as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def shell(dev, command):
    return (dev.shell(command, read_timeout_s=120.0) or "").strip()


def package_names(answer):
    return {line.split(":", 1)[1].strip() for line in answer.splitlines()
            if line.startswith("package:")}


def query_packages(dev):
    """The packages installed for user 0, and the ones disabled for user 0.

    Every command these tools send acts on user 0: `pm disable-user --user 0`, and `pm enable`,
    which means user 0 when no user is given. Without --user, Android 14's pm answers for every user
    on the TV and merges the answers (AOSP's android11-release still answered for user 0 alone), so
    on a TV with a second user a package that only the other user has disabled shows under -d, and
    one installed only for the other user shows as installed. The Chromecast with Google TV 4K this
    was tried on has such a user, a dormant profile with the id 10. Recorded from the merged answers,
    a package the owner had on for user 0 would be "disabled", and restore would leave it off for
    good. check.py reads the same two sets, so its drift report and its read-back after --fix are
    about user 0 too.
    """
    scope = " --user 0"
    installed = package_names(shell(dev, "pm list packages --user 0"))
    if not installed:
        # A pm that does not take --user prints an error or its usage instead of package lines, and
        # only that falls back to the plain queries. An empty -d --user 0 is no reason to: a TV
        # nothing was disabled on yet answers exactly that, and the merged -d would bring the other
        # user's disabled packages into the record on the very first run.
        scope = ""
        installed = package_names(shell(dev, "pm list packages"))
    if not installed:
        raise SystemExit("the TV returned no packages, so nothing was recorded and nothing will be "
                         "disabled. Check the connection (tools/tv.py --probe) and try again.")
    disabled = package_names(shell(dev, f"pm list packages -d{scope}"))
    return installed, disabled


def query_home(dev):
    answer = shell(dev, "cmd package resolve-activity --brief -a android.intent.action.MAIN -c "
                        "android.intent.category.HOME")
    candidate = answer.splitlines()[-1].strip() if answer else ""
    # Only a component counts: "No activity found" when nothing handles HOME, or the shell's error on
    # firmware older than `cmd`, comes back as None. Android's chooser does pass, though: when Home has
    # no default the last line is android/com.android.internal.app.ResolverActivity (#85). check.py
    # reports that as the Home it found, and save() keeps it out of the record, because the chooser is
    # no launcher to put back and must never be written into a set-home-activity command.
    return candidate if HOME_RE.fullmatch(candidate) else None


def connect():
    # Imported here so --commands works on a machine where adb_shell is not installed: printing the
    # restore batch needs no TV. tv.py itself exits with a readable message when TV_HOST is unset.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import tv
    except ImportError as e:
        raise SystemExit(f"cannot load tools/tv.py ({e}).\nrun: python3 -m venv tools/venv && "
                         "tools/venv/bin/pip install -r tools/requirements.txt")
    return tv.connect()


def package_state(name, installed, disabled):
    return ("absent" if name not in installed
            else "disabled" if name in disabled
            else "enabled")


def save(list_path, host):
    path = record_path(list_path, host)
    if path.exists():
        record = load_record(path)
        packages = read_list(list_path)
        # The list may have been edited since the record was taken. Entries already in the record are
        # never overwritten (a retry must not record the broken state as the original), but names it
        # does not hold yet have not been touched by this list, so their state now is their state
        # before cleanup. Without them, restore would leave those packages disabled for good.
        added = [name for name in packages if name not in record["packages"]]
        print(f"keeping the recovery record from {record.get('created')}: {path}")
        if not added:
            print("nothing was recorded again: it holds the state from before the first run.")
            return 0
        dev = connect()
        try:
            installed, disabled = query_packages(dev)
        finally:
            dev.close()
        for name in added:
            record["packages"][name] = package_state(name, installed, disabled)
        write_record(path, record)
        print(f"added {len(added)} names the list gained since then, entries already recorded "
              f"are unchanged: {', '.join(added)}")
        return 0

    packages = read_list(list_path)
    dev = connect()
    try:
        installed, disabled = query_packages(dev)
        home = query_home(dev)
        scales = {key: shell(dev, f"settings get global {key}") for key in SETTINGS}
    finally:
        dev.close()

    # Android's chooser, android/com.android.internal.app.ResolverActivity, answers HOME when Home has
    # no default. Recorded, it would put "android" among the packages, which is not a package name a
    # record can hold. A Home whose package the record cannot hold is left out instead, and restore
    # then resolves the stock launcher, as it does when nothing answered HOME.
    chooser = home if is_chooser(home) else None
    if chooser:
        home = None

    # The launcher that owns Home may not be in the list, but it is what undo has to put back.
    home_package = home.split("/", 1)[0] if home else None
    targets = packages + ([home_package] if home_package and home_package not in packages else [])
    record = {
        "version": VERSION,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": host,
        "list": str(Path(list_path).resolve()),
        "home": home,
        "settings": scales,
        "packages": {name: package_state(name, installed, disabled) for name in targets},
    }
    write_record(path, record)

    already = sum(1 for state in record["packages"].values() if state == "disabled")
    print(f"recorded {len(record['packages'])} packages on {host} "
          f"({already} already disabled, left alone by undo) -> {path}")
    if chooser:
        print(f"HOME before: {chooser}, Android's chooser (Home has no default), so no Home was "
              "recorded")
    else:
        print(f"HOME before: {home or 'no component answered'}")
    print("undo with tools/restore.sh <same list>; keep this file, it is the only copy.")
    return 0


def restore_commands(list_path, stock, host):
    """The batch that puts the recorded states back, one command per line."""
    packages = read_list(list_path)
    if stock and not PACKAGE_RE.fullmatch(stock):
        raise SystemExit(f"not a package name: {stock!r}")
    path = record_path(list_path, host)
    commands = []

    if not path.exists():
        sys.stderr.write(
            f"no recovery record for this TV and list ({path}).\n"
            "Enabling every listed package and resetting Home and the animation scales to their\n"
            "defaults. Packages that were already disabled before cleanup will be enabled too:\n"
            "check the list before running this.\n")
        for name in packages:
            commands.append(f"pm enable {name}")
        if stock:
            commands.append(f"pm enable {stock}")
        commands.append(f"cmd package set-home-activity --user 0 $(cmd package resolve-activity "
                        f"--brief -a android.intent.action.MAIN -c android.intent.category.HOME "
                        f"{stock or 'com.google.android.tvlauncher'} | tail -n 1)")
        commands.extend(f"settings put global {key} 1.0" for key in SETTINGS)
        commands.append("pm list packages -d")
        return commands

    record = load_record(path)
    states = record["packages"]
    re_enable = [name for name, state in states.items() if state == "enabled"]
    for name in re_enable:
        commands.append(f"pm enable {name}")
    untouched = [(name, state) for name, state in states.items() if state != "enabled"]
    for name, state in untouched:
        sys.stderr.write(f"  leaving {name} alone ({state} when the record was taken)\n")

    # The stock launcher comes back unless the owner had disabled it before cleanup: the list may
    # have disabled it even when it was not the recorded Home (e.g. the custom launcher owned Home).
    fallback = stock or "com.google.android.tvlauncher"
    if states.get(fallback) != "disabled" and fallback not in re_enable:
        commands.append(f"pm enable {fallback}")

    home = record.get("home")
    if home and home.split("/", 1)[0] != CUSTOM_LAUNCHER:
        commands.append(f"cmd package set-home-activity --user 0 {home}")
    else:
        # Nothing handled HOME before cleanup (fresh TV, chooser only), or this project's launcher
        # did, so there is no stock component to replay; ask the TV to resolve the stock launcher the
        # way restore.sh always did.
        commands.append(f"cmd package set-home-activity --user 0 $(cmd package resolve-activity "
                        f"--brief -a android.intent.action.MAIN -c android.intent.category.HOME "
                        f"{fallback} | tail -n 1)")
    for key in SETTINGS:
        value = str(record.get("settings", {}).get(key, "")).strip()
        if value == "null":
            commands.append(f"settings delete global {key}")
        elif SCALE_RE.fullmatch(value):
            commands.append(f"settings put global {key} {value}")
        else:
            sys.stderr.write(f"  skipping {key}: the record holds {value!r}, not a number\n")
    # disable.sh adds names the list gained to the record before disabling them, so a name still
    # missing here was added after the last disable run and never disabled by it: leave it alone.
    edited = [name for name in packages if name not in states]
    if edited:
        sys.stderr.write(f"not in the record, leaving alone: {', '.join(edited)}\n")
    commands.append("pm list packages -d")

    sys.stderr.write(f"restoring the state recorded on {record.get('created')}: "
                     f"re-enabling {len(re_enable)}, leaving {len(untouched)} as they were.\n")
    return commands


def main():
    args = sys.argv[1:]
    host = os.environ.get("TV_HOST", "")
    if len(args) == 2 and args[0] == "--save":
        return save(args[1], host)
    if len(args) in (2, 3) and args[0] == "--commands":
        if not host:
            sys.stderr.write("Set TV_HOST to your TV's IP address, e.g. TV_HOST=192.168.1.50\n")
        stock = args[2] if len(args) == 3 else "com.google.android.tvlauncher"
        for command in restore_commands(args[1], stock, host):
            print(command)
        return 0
    sys.stderr.write("usage: recovery.py --save <debloat list>\n"
                     "       recovery.py --commands <debloat list> [stock launcher package]\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
