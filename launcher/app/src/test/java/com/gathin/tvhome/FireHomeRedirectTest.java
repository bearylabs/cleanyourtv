package com.gathin.tvhome;

import org.junit.Test;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class FireHomeRedirectTest {
    private static final String CLOSE = "android.intent.action.CLOSE_SYSTEM_DIALOGS";

    @Test public void shortHomeClosesDialogsAndRequestsHome() {
        assertTrue(FireHomeRedirect.isShortHomeSignal(CLOSE, "homekey"));
    }

    @Test public void longHomeAndOtherDialogReasonsAreLeftAlone() {
        for (String reason : new String[]{"assist", "globalactions", "recentapps", "dream", "", null}) {
            assertFalse(FireHomeRedirect.isShortHomeSignal(CLOSE, reason));
        }
    }

    @Test public void otherBroadcastsCannotRequestHome() {
        assertFalse(FireHomeRedirect.isShortHomeSignal("android.intent.action.SCREEN_OFF", "homekey"));
        assertFalse(FireHomeRedirect.isShortHomeSignal(null, "homekey"));
    }
}
