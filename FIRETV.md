# Fire TV branch: AFTSS / sheldon

This public fork's `firetv` branch adapts CleanYourTV for a **Fire TV Stick Lite 2020 (AFTSS / sheldon), Fire OS 7.7.1.7, build PS7717.5741N, Android 9 / API 28**. It is not an upstream-supported Fire TV installation path and is not a general-purpose installer for other models or firmware.

## What changes

- Opt-in Amazon Home redirect in the existing `HomeKeyService`: reuse the launcher's task, with an alarm fallback and a black accessibility overlay that fails open after four seconds. Stale window events are ignored. Attribution: [DUMBTV-LICENSE.txt](launcher/DUMBTV-LICENSE.txt).
- Native settings fallback, including the unusable Fire OS settings trampoline. Only an exact configured component is rejected, not every activity in Amazon's launcher package.
- Top-bar app buttons honor `launch_actions`, like app tiles, retaining the normal entry if the configured action no longer resolves.
- Device-specific dock, eight cosmetically hidden tiles and a bottom-only app library. No extra top-bar apps by default. Hidden apps are not disabled or uninstalled by the launcher.

Amazon Home stays enabled. No root, new network permission or target SDK downgrade. HDMI-CEC stays **ON**. The existing accessibility service observes window changes; it is not a shell helper or a local ADB client. The fork retains upstream power-on/standby options without silently enabling them.

## What has actually been tested

The first saved source is tagged `firetv-setup-v1`. Upstream changes through `575d73f0` were subsequently merged; the RC1 release was installed on the physical stick and restored after later experiments. Its installed APK checksum matched the pinned RC1 release:

```text
a7ff827e7b4fe188769b49ca293f1e8f189c84214a76f5e02289306780ca6290
```

- Ordinary HOME redirect is configured; native settings and the launcher opened in device checks.
- The owner reported **no Amazon Home flash** in real-remote HOME tests from Netflix, Disney+ and Prime Video. These are observations, not guarantees under every load or from every playback state.
- **Known issue, accepted by the owner:** HOME from RTL+ can expose Amazon Home before redirecting. No invisible-transition guarantee.
- No new physical cold-boot, playback/DRM or sleep/wake validation was performed after restoring RC1. A configured service or injected key is not proof of real-remote or boot behavior.
- The later source-only refinement of exact settings-component matching and its new regression tests have not been installed on the stick. The top-bar action selection now has executable JVM policy tests plus UI-wiring regressions. Build/tests do not turn these source changes into a physically validated APK release.

The installed RC1 APK is **not necessarily identical to a fresh build of this branch**. No new APK is automatically installed or promoted merely because its tests pass. Personal configuration, deployment records, release pins and signing keys remain separate; none is required to read or build this public source.

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

Some repository tests need optional dependencies or a POSIX environment; report skips and failures honestly. Java tests exercise action-selection and settings-matching policy without a TV; Python regressions check the UI/resource wiring.

## Configuration and installation boundary

Edit `launcher/app/src/main/res/values/config.xml` for a deliberate local build. The branch sets `stock_home_redirect` to `com.amazon.tv.launcher`, preserves its selected dock and keeps normal upstream behavior switches at their defaults. `settings_stub_components` is a resource-only list of exact unusable settings handlers, not a theme key. Working activities in the same package stay usable; the existing `CTSDummy` fallback is retained. See the [keys table](themes/README.md#keys). This resource is nonvisual firmware compatibility data, not a new UI switch: executable matching tests cover it, and screenshot checks explicitly require it to remain build-only and documented. An unrelated settings screenshot is not substituted for an AFTSS device test; visual theme switches still need real-TV screenshots.

**Do not run upstream `launcher/build-and-install.sh` on this stick:** its default-HOME handover is unsupported on Fire OS. This fork does not publish a general installer or permission-grant recipe. Deployment needs an explicitly selected, inspected device, checksum/signature checks and physical HOME/native-settings checks. Keep Amazon Home enabled and do not copy another person's ADB keys. ADB, if intentionally left enabled, is plaintext on the local network; never expose it to the Internet.

## Rejected experiments and diagnostic limits

During RTL+ reproductions, `system_server` reported approximately two-second `HdmiControlService` main-thread stalls before accessibility window delivery. An explicitly approved temporary CEC-off comparison reduced the additional stall; CEC was then restored to ON. This does not establish a universal cause or justify changing CEC for another owner.

RC2 tried `CLOSE_SYSTEM_DIALOGS/homekey`, but the real broadcast skipped the receiver because it requires Amazon's signature/privileged `com.amazon.permission.ENABLE_KEYGUARD_FLAGS`. A synthetic shell broadcast was misleading. The receiver was removed and RC1 restored. Extra content events were also delayed and are not subscribed to.

A later RTL+-only raw-input shell observer was physically confirmed to cover the transition, but the attempted local ADB companion did not achieve autonomous startup. On-device CNXN connections closed in independent probes while remote-PC CNXN received AUTH normally. A direct accessibility key-filter probe received no HOME callback for the owner's real HOME press. None of these observations proves that every firmware behaves identically.

At the owner's request, **all those experiments were withdrawn**: companion/private data, shell helper and device files, protected-broadcast receiver, temporary native-key diagnostics and experimental setup additions are absent. No new root, privileged grant, SELinux change or firmware bypass was used. Do not present those removed paths as working features or RTL+ as fixed.

## Upstream and maintenance

- Fork: [bearylabs/cleanyourtv, `firetv`](https://github.com/bearylabs/cleanyourtv/tree/firetv)
- Original: [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv)
- Original base: `eb0131a32fd8567086f39002f1782f7c1b078ca6`; reviewed upstream merge through `575d73f0`.

Use reviewed merges for published `firetv` history; do not reset personal changes, force-push or use a fork sync that discards them. Updating another branch does not update this one. No automatic installation.

Upstream keeps Fire OS HOME takeover in showcase forks. General fixes should be submitted separately from device configuration and HOME interception. Public screenshots for a showcase entry must be captured with permission and checked for account/location information; none is fabricated or included here as a new physical test.
