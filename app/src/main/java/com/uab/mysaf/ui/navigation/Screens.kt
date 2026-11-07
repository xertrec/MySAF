package com.uab.mysaf.ui.navigation

import kotlinx.serialization.Serializable

@Serializable
data object ScreenHome

@Serializable
data class ScreenActivity(
    val activityId: String,
)

@Serializable
data class ScreenRecommendations(
    val activityId: String,
    val weekday: String,
    val hour: Int,
)

@Serializable
data object ScreenMethodology
