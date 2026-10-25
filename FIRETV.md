# Personal Fire TV branch

This fork's `firetv` branch contains local adaptations for an AFTSS/sheldon running Fire OS 7.7.1.7 (Android 9/API 28). It is not an upstream-supported Fire TV installation path.

## Changes relative to the original

Original base: `eb0131a32fd8567086f39002f1782f7c1b078ca6` from https://github.com/Gathin23/cleanyourtv.

All 407 previously pending upstream commits through `575d73f0` have been merged. The resulting APK is a **test candidate, not yet tested on a physical Fire TV**. The original known-device APK remains separately pinned in the private setup repository. See its `TESTING.md` for the later explicitly approved update test.

Follow-up RC2 attempted to use `CLOSE_SYSTEM_DIALOGS/homekey`, but real-device diagnostics proved Fire OS skips our receiver: the actual system broadcast requires Amazon's signature/privileged `com.amazon.permission.ENABLE_KEYGUARD_FLAGS`. A synthetic shell broadcast did not reproduce this restriction. RC2 is withdrawn; the receiver and its tests have been removed, and the RC1 APK has been reinstalled. All upstream changes remain. Additional window-content events were investigated but were delayed along with window-state events and are not subscribed to in the final source.

Known issue: RTL+ -> HOME can briefly expose Amazon Home. During reproductions, system_server's main thread reports an approximately two-second `HdmiControlService$BinderService$4` dispatch stall before accessibility delivery. This is evidence of a system-side delay, not proof that disabling HDMI-CEC will solve it. HDMI-CEC is currently enabled and has not been modified. A temporary CEC-off comparison requires explicit user approval because it may affect TV/device control. Do not reintroduce the blocked receiver or claim this transition is fixed.

The HomeKeyService merge retains both the Fire TV adapter and upstream's power-on, standby opt-in and Android 10+ stock-home handling. Fire TV continues to use its adapter; the upstream launch path is kept for other platforms. New layout/library behavior switches retain their upstream defaults: no silent layout change, no automatic TCL standby workaround. Optional add-ons are available as source but are not bundled or installed with the launcher.

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
