package com.uab.mysaf.data

import androidx.annotation.PluralsRes
import androidx.annotation.StringRes
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.Pool
import androidx.compose.material.icons.filled.SportsBasketball
import androidx.compose.material.icons.filled.SportsSoccer
import androidx.compose.material.icons.filled.SportsTennis
import androidx.compose.material.icons.filled.Terrain
import androidx.compose.ui.graphics.vector.ImageVector
import com.uab.mysaf.R

/** UI catalogue. Real availability metadata will be loaded from daily_counts.json later. */
data class ActivityInfo(
    val id: String,
    @StringRes val nameRes: Int,
    val icon: ImageVector,
    val capacity: Int,
    @PluralsRes val unitRes: Int,
    val isPersonCount: Boolean = true,
)

val activities = listOf(
    ActivityInfo("piscina_25m", R.string.activity_pool, Icons.Filled.Pool, 120, R.plurals.unit_people),
    ActivityInfo("sala_fitness", R.string.activity_fitness_room, Icons.Filled.FitnessCenter, 120, R.plurals.unit_people),
    ActivityInfo("padel", R.string.activity_padel, Icons.Filled.SportsTennis, 4, R.plurals.unit_courts, false),
    ActivityInfo("tennis", R.string.activity_tennis, Icons.Filled.SportsTennis, 5, R.plurals.unit_courts, false),
    ActivityInfo("esquaix", R.string.activity_squash, Icons.Filled.SportsTennis, 3, R.plurals.unit_courts, false),
    ActivityInfo("pavello", R.string.activity_sports_hall, Icons.Filled.SportsBasketball, 4, R.plurals.unit_courts, false),
    ActivityInfo("futbol_sala", R.string.activity_futsal, Icons.Filled.SportsSoccer, 2, R.plurals.unit_courts, false),
    ActivityInfo("futbol_7_11", R.string.activity_football, Icons.Filled.SportsSoccer, 2, R.plurals.unit_pitches, false),
    ActivityInfo("barbell", R.string.activity_barbell_area, Icons.Filled.FitnessCenter, 24, R.plurals.unit_people),
    ActivityInfo("callistenia", R.string.activity_calisthenics, Icons.Filled.AccessibilityNew, 20, R.plurals.unit_people),
    ActivityInfo("rocodrom", R.string.activity_climbing_wall, Icons.Filled.Terrain, 18, R.plurals.unit_people),
)

fun activityById(id: String): ActivityInfo = activities.firstOrNull { it.id == id } ?: activities.first()
