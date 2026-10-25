# Unusable native-settings handlers

Some firmware resolves a standard `android.settings.*` intent to an activity that opens nothing useful.
This is compatibility data, not a visual theme switch. Configure it at build time in
`launcher/app/src/main/res/values/config.xml`:

```xml
<string-array name="settings_stub_components" translatable="false">
    <item>com.amazon.tv.launcher/.ui.SettingsActivity</item>
</string-array>
```

`settings_stub_components` contains **exact package/activity pairs**. A leading dot in the activity is
expanded to the package name. On the observed AFTSS Fire OS 7.7.1.7 build, that SettingsActivity
returned Home instead of opening the real settings menu. The working
`com.amazon.tv.launcher/.ui.MainSettingsActivity` is not rejected. Do not list an entire vendor package
or infer that all its settings pages are broken. Other firmware may need a different list or none.

A matching standard handler uses the existing `settings_fallback_components` list, in order. The
existing `CTSDummy` compliance-stub detection remains independent of this list. With no usable vendor
fallback, the standard intent is retained; this does not guarantee that it opens a working screen.
Fallback packages must remain visible through the manifest's `<queries>` on Android 11+.

This resource is not read from a theme's JSON. Changing it needs a new, correctly signed build;
there is no runtime setting, permission grant, polling or background service. Exact matching has JVM
regression tests; resource wiring has Python tests. The screenshot checks explicitly recognize this
nonvisual build-only table and enforce that it stays documented and unavailable to themes. An
unrelated UI photo is not evidence that component matching works on a particular TV. Visual theme
switches still need real-TV screenshots.

A new matching rule or implementation still needs real-device validation before being described as
tested on that firmware. A passing policy test does not establish physical HOME, settings, boot or
sleep/wake behavior. Do not replace a working installation just to run these offline checks.
