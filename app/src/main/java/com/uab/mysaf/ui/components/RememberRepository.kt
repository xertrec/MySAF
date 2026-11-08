package com.uab.mysaf.ui.components

import android.util.Log
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import com.uab.mysaf.data.AvailabilityRepository
import kotlin.coroutines.cancellation.CancellationException

/** Repository backed by the app-wide Room database. */
@Composable
fun rememberAvailabilityRepository(): AvailabilityRepository {
    val context = LocalContext.current.applicationContext
    return remember(context) { AvailabilityRepository.from(context) }
}

/** Runs a database read, falling back to [default] if it fails (cancellation is rethrown). */
suspend fun <T> loadOrDefault(default: T, block: suspend () -> T): T =
    try {
        block()
    } catch (e: CancellationException) {
        throw e
    } catch (e: Exception) {
        Log.e("MySAF", "Could not read availability database", e)
        default
    }
