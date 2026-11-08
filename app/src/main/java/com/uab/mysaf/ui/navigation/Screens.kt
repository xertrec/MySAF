package com.uab.mysaf.ui.navigation

import kotlinx.serialization.Serializable

// Bottom-bar tabs.

@Serializable
data object ScreenHome

@Serializable
data object ScreenRecommend

@Serializable
data object ScreenChat

// Detail screens.

/** P2 step 3: recommendation for one activity and day; [hour] is -1 for "any time". */
@Serializable
data class ScreenRecommendation(
    val activityId: String,
    val epochDay: Long,
    val hour: Int = -1,
)

/** P2 step 4: hourly occupancy chart (Avui / Setmana / Històric). */
@Serializable
data class ScreenOccupancy(
    val activityId: String,
)

/** P2 step 5: similar, quieter options for one weekday and hour. */
@Serializable
data class ScreenAlternatives(
    val activityId: String,
    val weekday: String,
    val hour: Int,
)

/** List of facilities, sports or both. */
@Serializable
data class ScreenCatalog(
    val group: String,
) {
    companion object {
        const val FACILITIES = "facilities"
        const val SPORTS = "sports"
        const val ALL = "all"
    }
}

@Serializable
data object ScreenSchedule

@Serializable
data object ScreenMethodology
