package com.gathin.tvhome;

import org.junit.Test;
import static org.junit.Assert.*;

public class SystemSettingsTest {
    private static final String PKG = "com.amazon.tv.launcher";
    private static final String[] STUBS = {PKG + "/.ui.SettingsActivity"};

    @Test public void configuredShortComponentMatchesItsExactActivity() {
        assertTrue(SystemSettings.isStub(PKG, PKG + ".ui.SettingsActivity", STUBS));
    }

    @Test public void fullyQualifiedComponentAlsoMatches() {
        assertTrue(SystemSettings.isStub(PKG, PKG + ".ui.SettingsActivity",
                new String[]{PKG + "/" + PKG + ".ui.SettingsActivity"}));
    }

    @Test public void workingActivityInSamePackageIsNotRejected() {
        assertFalse(SystemSettings.isStub(PKG, PKG + ".ui.MainSettingsActivity", STUBS));
        assertFalse(SystemSettings.isStub(PKG, PKG + ".ui.NetworkSettingsActivity", STUBS));
    }

    @Test public void anotherVendorAndSimilarlyNamedClassRemainUsable() {
        assertFalse(SystemSettings.isStub("other.vendor", PKG + ".ui.SettingsActivity", STUBS));
        assertFalse(SystemSettings.isStub(PKG, PKG + ".ui.SettingsActivityExtra", STUBS));
        assertFalse(SystemSettings.isStub("com.android.tv.settings", "com.android.tv.settings.Main", STUBS));
    }

    @Test public void emptyListDoesNotApplyFireOsPolicy() {
        assertFalse(SystemSettings.isStub(PKG, PKG + ".ui.SettingsActivity", new String[0]));
    }

    @Test public void complianceStubStillTriggersFallback() {
        assertTrue(SystemSettings.isStub("vendor", "vendor.CTSDummySettingsHandler", new String[0]));
    }

    @Test public void malformedConfigurationDoesNotRejectWorkingSettings() {
        assertFalse(SystemSettings.isStub(PKG, PKG + ".ui.MainSettingsActivity",
                new String[]{null, "", "missing-slash", "/.Bad", "package/"}));
    }

    @Test public void missingActivityNameIsUnusable() {
        assertTrue(SystemSettings.isStub(PKG, null, STUBS));
    }
}
