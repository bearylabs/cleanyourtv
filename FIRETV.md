# Personal Fire TV branch

This fork's `firetv` branch contains local adaptations for an AFTSS/sheldon running Fire OS 7.7.1.7 (Android 9/API 28). It is not an upstream-supported Fire TV installation path.

## Changes relative to the original

Base: `eb0131a32fd8567086f39002f1782f7c1b078ca6` from https://github.com/Gathin23/cleanyourtv.

- Opt-in Amazon Home redirect: reuse our own task, with an alarm fallback and a black accessibility overlay that fails open after four seconds. Stale window events are ignored. Attribution: `launcher/DUMBTV-LICENSE.txt`.
- Fire OS settings fallback to the real Amazon settings activity.
- Top-bar apps honor configured launch actions, including the Amazon Appstore action.
- Device-specific dock packages, eight cosmetically hidden tiles, bottom-only app library and Amazon Home redirect configuration. No extra top-bar apps.

Amazon Home stays enabled. No root, new network permission or target SDK downgrade. Actual Home transitions vary with device load. Build/unit tests do not replace real-remote and playback tests.

## Remotes and upstream updates

- `origin`: https://github.com/bearylabs/cleanyourtv
- `upstream`: https://github.com/Gathin23/cleanyourtv
- `main`: unmodified upstream history; `firetv`: personal changes and reviewed upstream merges.

From a clean `firetv` checkout:

```sh
git fetch upstream
git log --oneline HEAD..upstream/main
git diff HEAD...upstream/main -- launcher/
# Only after reviewing the changes:
git merge --no-ff --no-commit upstream/main
# Resolve conflicts, inspect the staged changes, build and test.
# To abandon an in-progress merge: git merge --abort
# Otherwise commit the merge, then push origin firetv.
```

Use merges rather than rebases for published history. Never reset `firetv` to upstream or use GitHub's fork sync to discard its changes. Updating `main` alone does not update `firetv`. No auto-installation.

Build instructions, the pinned tested revision and private device setup are in the separate private `bearylabs/firetv-setup` repository. Do not run upstream `build-and-install.sh` on this device: its HOME handover is unsupported on Fire OS.

## Releases and signing

Tag `firetv-setup-v1` identifies the first saved source state. Its previously built APK is stored in a release of the private setup repository. Build tools and signing keys are not committed. Preserve the existing debug signing keystore separately: a new key cannot update the installed app without uninstalling it and losing its local data. Do not publish keys or device backups.
