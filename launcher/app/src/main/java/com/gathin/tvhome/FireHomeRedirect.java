package com.gathin.tvhome;

import android.accessibilityservice.AccessibilityService;
import android.app.ActivityOptions;
import android.app.ActivityManager;
import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.View;
import android.view.ViewTreeObserver;
import android.view.WindowManager;

/**
 * Local Fire OS adapter: bring our existing task forward, or use an alarm for
 * first launch. A non-interactive accessibility overlay hides Amazon's home.
 * Based on the approach in humblemuzzu/dumbtv Guard.java (MIT); see DUMBTV-LICENSE.txt.
 * Requires alarm_manager_constants min_futurity=0 on this Fire OS 7 device.
 * Does not intercept media, read screen contents, disable Amazon Home or run a poller.
 */
final class FireHomeRedirect {
    private static FireHomeRedirect active;
    private static long lastHomeFocus;
    private final AccessibilityService service;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final WindowManager windows;
    private final AlarmManager alarms;
    private final PendingIntent target;
    private View cover;
    private long lastRequest;
    private boolean waitingForDraw;
    private final Runnable timeout = this::hide;
    private final Runnable dispatch = this::launch;
    private final Runnable homeRequest = this::request;
    private final BroadcastReceiver homePress = new BroadcastReceiver() {
        @Override public void onReceive(Context context, Intent intent) {
            if (!isShortHomeSignal(intent.getAction(), intent.getStringExtra("reason"))) return;
            // Fire OS consumes HOME before accessibility sees a key. Its close-dialogs
            // broadcast arrives before Amazon's window event (several seconds late after RTL+).
            // Let the firmware enqueue Home first so moveToFront cannot race ahead of it.
            android.util.Log.i("FireHomeRedirect", "system HOME signal");
            handler.removeCallbacks(homeRequest);
            handler.postDelayed(homeRequest, 150);
        }
    };
    private boolean homePressRegistered;

    FireHomeRedirect(AccessibilityService service) {
        this.service = service;
        windows = service.getSystemService(WindowManager.class);
        alarms = service.getSystemService(AlarmManager.class);
        Intent home = new Intent(service, MainActivity.class)
                .setAction(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED
                        | Intent.FLAG_ACTIVITY_NO_ANIMATION);
        target = PendingIntent.getActivity(service, 7421, home,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE,
                ActivityOptions.makeCustomAnimation(service, 0, 0).toBundle());
        View view = new View(service);
        view.setBackgroundColor(Color.BLACK);
        view.setVisibility(View.GONE);
        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                        | WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.OPAQUE);
        params.windowAnimations = 0;
        windows.addView(view, params);
        cover = view;
        active = this;
        try {
            IntentFilter filter = new IntentFilter(Intent.ACTION_CLOSE_SYSTEM_DIALOGS);
            // The flags overload exists since API 26 (our minSdk); pre-33 systems
            // ignore the newer export bit. Newer systems restrict delivery to this app/system.
            service.registerReceiver(homePress, filter, Context.RECEIVER_NOT_EXPORTED);
            homePressRegistered = true;
        } catch (SecurityException unavailable) {
            // Vendor restrictions must not break the existing accessibility-window fallback.
            android.util.Log.w("FireHomeRedirect", "HOME signal unavailable", unavailable);
        }
    }

    /** Only a short HOME press, never Back, recents, global actions or a long HOME press. */
    static boolean isShortHomeSignal(String action, String reason) {
        return Intent.ACTION_CLOSE_SYSTEM_DIALOGS.equals(action) && "homekey".equals(reason);
    }

    void request() {
        long now = SystemClock.uptimeMillis();
        if (now - lastRequest < 600) return;
        lastRequest = now;
        android.util.Log.i("FireHomeRedirect", "cover requested");
        handler.removeCallbacks(timeout);
        handler.postDelayed(timeout, 4000); // Fail open, allowing for this 1 GB stick under load.
        if (cover.getVisibility() == View.VISIBLE) {
            launch();
            return;
        }
        waitingForDraw = true;
        cover.getViewTreeObserver().addOnPreDrawListener(new ViewTreeObserver.OnPreDrawListener() {
            @Override public boolean onPreDraw() {
                if (cover != null && cover.getViewTreeObserver().isAlive()) {
                    cover.getViewTreeObserver().removeOnPreDrawListener(this);
                }
                if (waitingForDraw) launch();
                return true;
            }
        });
        cover.setVisibility(View.VISIBLE);
        handler.postDelayed(dispatch, 120); // Also handle a missing first-draw callback.
    }

    private void launch() {
        waitingForDraw = false;
        handler.removeCallbacks(dispatch);
        // Reusing our own live task avoids an activity launch entirely and is faster
        // on this Fire OS 7 build than the alarm path (also used by dumbtv's Keeper).
        ActivityManager manager = service.getSystemService(ActivityManager.class);
        try {
            for (ActivityManager.AppTask task : manager.getAppTasks()) {
                ActivityManager.RecentTaskInfo info = task.getTaskInfo();
                if (info.baseActivity != null && info.topActivity != null
                        && MainActivity.class.getName().equals(info.baseActivity.getClassName())
                        && MainActivity.class.getName().equals(info.topActivity.getClassName())) {
                    task.moveToFront();
                    android.util.Log.i("FireHomeRedirect", "moved existing home task");
                    return;
                }
            }
        } catch (SecurityException | IllegalArgumentException unavailable) {
            android.util.Log.w("FireHomeRedirect", "task move unavailable", unavailable);
        }
        android.util.Log.i("FireHomeRedirect", "dispatch alarm");
        alarms.setExact(AlarmManager.ELAPSED_REALTIME, SystemClock.elapsedRealtime(), target);
    }

    private void hide() {
        waitingForDraw = false;
        handler.removeCallbacks(dispatch);
        handler.removeCallbacks(timeout);
        alarms.cancel(target);
        if (cover != null) cover.setVisibility(View.GONE);
    }

    /** The launcher owns focus now; reveal its first frame rather than Amazon's. */
    static boolean wasShownAfter(long eventTime) {
        return eventTime <= lastHomeFocus;
    }

    static void shown() {
        lastHomeFocus = SystemClock.uptimeMillis();
        if (active != null) {
            android.util.Log.i("FireHomeRedirect", "home focused");
            active.hide();
        }
    }

    /** Do not pull the user back if another app or a settings window opened meanwhile. */
    void cancel() {
        handler.removeCallbacks(homeRequest);
        hide();
    }

    void destroy() {
        handler.removeCallbacks(homeRequest);
        if (homePressRegistered) {
            service.unregisterReceiver(homePress);
            homePressRegistered = false;
        }
        hide();
        if (cover != null) {
            windows.removeView(cover);
            cover = null;
        }
        if (active == this) active = null;
    }
}
