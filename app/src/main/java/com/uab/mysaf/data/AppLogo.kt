package com.uab.mysaf.data

import android.content.ComponentName
import android.content.Context
import android.content.SharedPreferences
import android.content.pm.PackageManager
import android.util.Log
import androidx.annotation.DrawableRes
import androidx.core.content.edit
import com.uab.mysaf.R
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Default mySAF logo, used when no favourite sport is set. */
@DrawableRes
val DefaultLogoRes: Int = R.drawable.ic_logo_main

/**
 * The user's favourite sport and whether its logo should also replace the home-screen icon.
 * [favouriteId] is an [ActivityInfo.id] or null for the default mySAF logo.
 */
data class AppLogoState(
    val favouriteId: String? = null,
    val useOnHomeScreen: Boolean = false,
) {
    @get:DrawableRes
    val logoRes: Int get() = favouriteId?.let { activityById(it).logoRes } ?: DefaultLogoRes

    /** Activity id whose launcher alias should be enabled; null = default mySAF icon. */
    val launcherId: String? get() = favouriteId.takeIf { useOnHomeScreen }
}

/** App-wide store for [AppLogoState], backed by SharedPreferences. */
class AppLogoStore private constructor(private val prefs: SharedPreferences) {

    private val _state = MutableStateFlow(read())
    val state: StateFlow<AppLogoState> = _state.asStateFlow()

    fun setFavourite(activityId: String?) = update { it.copy(favouriteId = activityId) }

    fun setUseOnHomeScreen(enabled: Boolean) = update { it.copy(useOnHomeScreen = enabled) }

    private fun update(change: (AppLogoState) -> AppLogoState) {
        val next = change(_state.value)
        prefs.edit {
            putString(KEY_FAVOURITE, next.favouriteId)
            putBoolean(KEY_HOME_SCREEN, next.useOnHomeScreen)
        }
        _state.value = next
    }

    private fun read(): AppLogoState {
        // Ignore ids that no longer exist in the catalogue.
        val id = prefs.getString(KEY_FAVOURITE, null)?.takeIf { saved -> activities.any { it.id == saved } }
        return AppLogoState(id, prefs.getBoolean(KEY_HOME_SCREEN, false))
    }

    companion object {
        private const val PREFS = "app_logo"
        private const val KEY_FAVOURITE = "favourite_activity"
        private const val KEY_HOME_SCREEN = "use_on_home_screen"

        @Volatile
        private var instance: AppLogoStore? = null

        fun get(context: Context): AppLogoStore =
            instance ?: synchronized(this) {
                instance ?: AppLogoStore(
                    context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE),
                ).also { instance = it }
            }
    }
}

/**
 * Swaps the home-screen icon by enabling exactly one `Launcher_<id>` activity-alias from the
 * manifest (`Launcher_main` is the default). Call it while the app is in the background: some
 * launchers restart or close the app when its launcher component changes.
 */
object LauncherIcon {
    private const val MAIN = "main"

    fun apply(context: Context, activityId: String?) {
        val target = activityId ?: MAIN
        val pm = context.packageManager
        val ids = listOf(MAIN) + activities.map { it.id }
        // Enable the new alias before disabling the others, so the app always has a launcher entry.
        val ordered = ids.sortedBy { it != target }
        for (id in ordered) {
            val component = ComponentName(context.packageName, aliasName(id))
            val wanted = if (id == target) {
                PackageManager.COMPONENT_ENABLED_STATE_ENABLED
            } else {
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED
            }
            try {
                if (effectiveState(pm, component, enabledByDefault = id == MAIN) != wanted) {
                    pm.setComponentEnabledSetting(component, wanted, PackageManager.DONT_KILL_APP)
                }
            } catch (e: IllegalArgumentException) {
                Log.e("MySAF", "Launcher alias missing from the manifest: ${component.className}", e)
            }
        }
    }

    private fun effectiveState(pm: PackageManager, component: ComponentName, enabledByDefault: Boolean): Int =
        when (val state = pm.getComponentEnabledSetting(component)) {
            PackageManager.COMPONENT_ENABLED_STATE_DEFAULT ->
                if (enabledByDefault) PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                else PackageManager.COMPONENT_ENABLED_STATE_DISABLED
            else -> state
        }

    /** Must match the `activity-alias` names in AndroidManifest.xml. */
    private fun aliasName(id: String) = "com.uab.mysaf.Launcher_$id"
}
