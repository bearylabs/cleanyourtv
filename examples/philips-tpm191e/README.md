# Philips 50PUS8505: single-session TPM191E notes

Checked on a Philips 50PUS8505, TP Vision TPM191E (`PH9M_EA_5599`), Android TV 12 / API 31, firmware `STT2.230526.001`. It shares the platform and firmware family of this folder's existing [`debloat.txt`](debloat.txt), but this was not a test of that full list.

## What was checked

- Disabled an owner-selected subset of 13 packages from the existing list: Philips analytics, usage logging, demo and promotion/store packages; the Sticker and Fitness Buddy preloads; and Google feedback/setup-only packages. Nothing was uninstalled.
- After one reboot, all 13 selected packages remained disabled.
- Installed the repository launcher, then disabled the stock launcher. Home resolved to `com.gathin.tvhome/.MainActivity` after installation and was focused during the navigation checks.
- The physical remote's Sources and Settings buttons continued to open Philips' internal menus. The launcher's Inputs menu reported HDMI and YPbPr, with Live TV configured as `org.droidtv.playtv`; no separate AV input was reported.

This is a single-session report, not a several-day debloat test. The full `debloat.txt` was not applied to this model. Streaming-app playback, broadcast/HDMI playback, USB-drive playback, app-shortcut remapping and long-press volume repeat were not validated here. Keep the existing list's package choices commented out unless they match your own use.

## Philips 55OLED854/12: single-session notes

Checked on a Philips 55OLED854/12 (OLED, Poland), same TP Vision TPM191E board and firmware as the
lead unit above (`STT2.230526.001`). Details and package names are in `debloat.txt`'s "Fourth unit"
note; this section covers the launcher side.

- Installed the repository launcher, then disabled the stock launcher, same order as the 50PUS8505
  unit. Home resolved to `com.gathin.tvhome/.MainActivity` and stayed focused there.
- The Sources drawer (Inputs pill) listed USB, Network, a connected recording drive, a Switch on
  HDMI 1, an Xbox on HDMI 2, HDMI 3, HDMI 4 and YPbPr, each correctly named from HDMI-CEC where a
  device reported one. `org.droidtv.eum` was disabled briefly, then re-enabled on reading the
  philips-50pus8517 notes, without testing the drawer while it was off -- so this unit confirms the
  drawer works with `eum` enabled, not that disabling it actually breaks it here too; that part of
  the other board's finding was taken on trust, the same caution applied to `nettvbrowser`,
  `menudataapp` and `nettvregistration` (see `debloat.txt`).
- The remote's Settings button stopped responding once the stock launcher was disabled, same
  category of issue as the TCL G09 in `docs/TROUBLESHOOTING.md`. Found with `adb shell
  getevent -lt` while pressing the button: this remote sends `KEY_OPTION` with no `MSC_SCAN`, so
  the framework reports
  scancode 357 directly. Mapping it with `config.xml`'s `settings_key_scancodes` and
  `-HomeKeyService` fixed the button, but enabling `HomeKeyService`'s key filtering broke Volume
  Up/Down's hold-to-repeat, the same trade-off the TCL G09 notes describe. The owner chose to keep
  volume repeat, so this unit ships with `key_filter` false: the Settings button does nothing, and
  Settings is reached from the launcher's own on-screen button instead.
- `app_library` and `library_button` were used to curate Home down to the owner's chosen apps (4
  dock + 4 grid) with everything else (including the Play Store's own tile and `org.droidtv.eum`'s
  "How-to videos" tile) moved to the Library screen instead of `hidden_apps` removing them
  outright. Note for anyone trying the same thing: `app_library`/`library_apps` only *add* apps
  that would not otherwise show (ordinary non-TV apps); they do not hide anything. Hiding an
  already-visible tile from the main grid still needs `hidden_apps`.
- The OLED screensaver (see `debloat.txt`) showed up more than once during the session, each time
  after a few minutes of screenshots taken a step at a time rather than genuine idling; it is real
  OLED housekeeping, not something triggered by the debloat or the launcher.
- A fresh reboot was done once, before the launcher install, to confirm the debloat list's
  persistence and run the idle-log check; the launcher, the Settings-button mapping and
  `com.google.android.tvrecommendations` (disabled after the launcher took Home) have not yet been
  through a reboot on this unit.
