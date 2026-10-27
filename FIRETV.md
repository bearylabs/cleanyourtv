# Fire TV branch: AFTSS / sheldon

This public fork's `firetv` branch adapts CleanYourTV for a **Fire TV Stick Lite 2020 (AFTSS / sheldon), Fire OS 7.7.1.7, build PS7717.5741N, Android 9 / API 28**. It is not an upstream-supported Fire TV installation path and is not a general-purpose installer for other models or firmware.

## What changes

- Opt-in Amazon Home redirect in the existing `HomeKeyService`: reuse the launcher's task, with an alarm fallback and a black accessibility overlay that fails open after four seconds. Stale window events are ignored. Attribution: [DUMBTV-LICENSE.txt](launcher/DUMBTV-LICENSE.txt).
- Native settings use the existing upstream `SystemSettings` fallback, including its CTS-stub detection. No extra vendor-package blacklist or settings compatibility table is needed.
- Top-bar app buttons honor `launch_actions`, like app tiles, retaining the normal entry if the configured action no longer resolves.
- Device-specific dock, eight cosmetically hidden tiles and a bottom-only app library. No extra top-bar apps by default. Hidden apps are not disabled or uninstalled by the launcher.

Amazon Home stays enabled. No root, new network permission or target SDK downgrade. HDMI-CEC stays **ON**. The existing accessibility service observes window changes; it is not a shell helper or a local ADB client. The fork retains upstream power-on/standby options without silently enabling them.

## Current approved release: Launcher 3.1

The owner reported that the new build looks good and works after testing it on one personal stick, then explicitly approved it as the stable personal default and requested deployment to a second stick. The same APK was installed on both, with installed-file SHA256 verified:

```text
029af470f2a9e7c5cbfdc5e7e5ed8c5693c3fbe6479b51cfafbfaf6ce059f567
```

Source: merge `766c5f39`, upstream through `6ffa7fa5`, tag `firetv-upstream-6ffa7fa5-v3.1`, version 3.1 / versionCode 10. All previous Fire TV resource values are preserved; six new entries retain upstream defaults. Build/lint and 274 JVM tests passed; 2035 repository Python tests passed (29 skipped). The original signing certificate was preserved. APKs and personal deployment records are kept separately, not in this public repository.

Targeted ADB checks passed on both sticks: Home renders, native settings open, injected HOME returns, and configuration checks pass. The owner's positive feedback was general, not an itemized physical-test report. A fresh physical HOME/native-settings check on the second stick remains pending; no new reboot, playback/DRM or sleep/wake tests were performed. RTL+ Home flash remains an accepted known issue, not fixed. CEC stays ON and Amazon Home stays enabled. No withdrawn early-HOME experiment was restored. RC1 is now a historical fallback, not the current stable default.

## Historical RC1 checks and diagnosis

The first saved source is tagged `firetv-setup-v1`. Upstream changes through `575d73f0` were subsequently merged; the RC1 release was installed on the physical stick and restored after later experiments. Its installed APK checksum matched the pinned RC1 release:

```text
a7ff827e7b4fe188769b49ca293f1e8f189c84214a76f5e02289306780ca6290
```

- Ordinary HOME redirect is configured; native settings and the launcher opened in device checks.
- The owner reported **no Amazon Home flash** in real-remote HOME tests from Netflix, Disney+ and Prime Video. These are observations, not guarantees under every load or from every playback state.
- **Known issue, accepted by the owner:** HOME from RTL+ can expose Amazon Home before redirecting. No invisible-transition guarantee.
- No new physical cold-boot, playback/DRM or sleep/wake validation was performed after restoring RC1. A configured service or injected key is not proof of real-remote or boot behavior.
- A temporary build was installed for targeted ADB-driven device checks. With Appstore temporarily configured in `top_bar_apps`, selecting its button sent `com.amazon.venezia.ade.FEATURED_LAUNCH` and focused `ADEHomeActivity`. Selecting Settings opened the real `com.amazon.tv.launcher/.ui.MainSettingsActivity`. These were real-device UI checks, **not physical-remote, boot or playback tests**. The separate PR builds based on newer upstream were built/tested offline, not installed.
- An important resolution check ruled out the proposed extra settings rule: unrestricted shell resolution picks `.ui.SettingsActivity`, but adding `android.intent.category.DEFAULT` (corresponding to the default-handler restriction used by `SystemSettings`) picks `.compliance.CTSDummySettingsHandler`. Upstream already handles that CTS stub. The experimental exact-component table, its tests/documentation exception and the earlier broad Amazon-package exclusion were therefore removed from the final source. No speculative settings-fix PR was submitted.
- The original RC1 was then restored and its checksum verified again; the temporary Appstore top-bar button is gone. CEC remains ON, Amazon Home enabled and the ordinary redirect configured. No new APK pin or release promotion.

The installed RC1 APK is **not necessarily identical to a fresh build of this branch**. No new APK is automatically installed or promoted merely because its tests pass. Personal configuration, deployment records, release pins and signing keys remain separate; none is required to read or build this public source.

## Device screenshots

[Restored RC1 Home](https://github.com/bearylabs/cleanyourtv/releases/download/firetv-device-check-images-2026-10-25/rc1-home.jpg) and [temporary top-bar action test](https://github.com/bearylabs/cleanyourtv/releases/download/firetv-device-check-images-2026-10-25/top-bar-action-test.jpg) are actual device captures, resized to 1280x720 with metadata stripped and checked for account/network/location information. The latter deliberately shows an extra Appstore button **only for testing**, not this fork's default configuration. They are published as screenshot-only pre-release assets, not committed device dumps, APKs or a new launcher release.

## Build and test from this public repository

Requirements: Git, **JDK 17**, Android SDK command-line tools, platform 34 and build-tools 34.0.0. Python 3 is needed for repository tests. Set `JAVA_HOME` and `ANDROID_HOME` to your installations and put their tools on `PATH`.

```sh
git clone --branch firetv https://github.com/bearylabs/cleanyourtv.git
cd cleanyourtv
sdkmanager "platforms;android-34" "build-tools;34.0.0"
cd launcher
./gradlew --no-daemon testReleaseUnitTest lintRelease assembleRelease
```

Output: `launcher/app/build/outputs/apk/release/app-release.apk` relative to the repository root. These commands **build only**: no ADB connection, installation, debloat or reboot. No private repository or device data is needed. The first build downloads Gradle/dependencies.

The release build uses Gradle's debug signing configuration. A first-time builder uses their own key; an existing installation must keep using **its original signing key** and signing configuration/`ANDROID_USER_HOME`. Never generate a replacement key to update an existing installation, publish a private key, or uninstall on signature mismatch. Independently signed builds cannot update each other.

Offline repository checks, from the repository root:

```sh
python3 -m unittest discover -s tests -v
git diff --check
```

Some repository tests need optional dependencies or a POSIX environment; report skips and failures honestly. Java tests exercise action-selection policy without a TV; Python regressions check its UI wiring and the fork's resources. The speculative settings-matching extension has been removed.

## Configuration and installation boundary

Edit `launcher/app/src/main/res/values/config.xml` for a deliberate local build. The branch sets `stock_home_redirect` to `com.amazon.tv.launcher`, preserves its selected dock and keeps normal upstream behavior switches at their defaults. Settings routing is upstream's existing `SystemSettings` implementation and `settings_fallback_components`; no extra vendor exclusion or `settings_stub_components` key remains. See the [keys table](themes/README.md#keys). The optional `top_bar_apps` list stays empty in this fork's default configuration; the generic action-selection fix does not add a button or affect ordinary HOME behavior.

**Do not run upstream `launcher/build-and-install.sh` on this stick:** its default-HOME handover is unsupported on Fire OS. This fork does not publish a general installer or permission-grant recipe. Deployment needs an explicitly selected, inspected device, checksum/signature checks and physical HOME/native-settings checks. Keep Amazon Home enabled and do not copy another person's ADB keys. ADB, if intentionally left enabled, is plaintext on the local network; never expose it to the Internet.

## Rejected experiments and diagnostic limits

During RTL+ reproductions, `system_server` reported approximately two-second `HdmiControlService` main-thread stalls before accessibility window delivery. An explicitly approved temporary CEC-off comparison reduced the additional stall; CEC was then restored to ON. This does not establish a universal cause or justify changing CEC for another owner.

RC2 tried `CLOSE_SYSTEM_DIALOGS/homekey`, but the real broadcast skipped the receiver because it requires Amazon's signature/privileged `com.amazon.permission.ENABLE_KEYGUARD_FLAGS`. A synthetic shell broadcast was misleading. The receiver was removed and RC1 restored. Extra content events were also delayed and are not subscribed to.

A later RTL+-only raw-input shell observer was physically confirmed to cover the transition, but the attempted local ADB companion did not achieve autonomous startup. On-device CNXN connections closed in independent probes while remote-PC CNXN received AUTH normally. A direct accessibility key-filter probe received no HOME callback for the owner's real HOME press. None of these observations proves that every firmware behaves identically.

At the owner's request, **all those experiments were withdrawn**: companion/private data, shell helper and device files, protected-broadcast receiver, temporary native-key diagnostics and experimental setup additions are absent. No new root, privileged grant, SELinux change or firmware bypass was used. Do not present those removed paths as working features or RTL+ as fixed.

## Upstream and maintenance

- Fork: [bearylabs/cleanyourtv, `firetv`](https://github.com/bearylabs/cleanyourtv/tree/firetv)
- Original: [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv)
- Original base: `eb0131a32fd8567086f39002f1782f7c1b078ca6`; latest source merge through `6ffa7fa5` (Launcher 3.1).
- The 3.1 merge preserves all existing Fire TV resource values. Its six new configuration entries retain upstream defaults; additional power-on and long-HOME interception remain off. The approved APK is 547,025 bytes and uses the original signing certificate. See the current release section above for device evidence and remaining physical-test limits. No RTL+ fix, reboot, playback or sleep/wake success is claimed.

Use reviewed merges for published `firetv` history; do not reset personal changes, force-push or use a fork sync that discards them. Updating another branch does not update this one. No automatic installation.

Upstream keeps Fire OS HOME takeover in showcase forks. General fixes should be submitted separately from device configuration and HOME interception. The linked public screenshots were captured with the owner's permission and privacy-checked. They illustrate the stated configurations only; screenshots do not prove boot, playback or physical-remote behavior.
