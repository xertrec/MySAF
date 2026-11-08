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

/**
 * UI-only catalogue (name, icon, unit). Capacity and occupancy come from the Room database
 * (see [AvailabilityRepository]); ids must match the `activity` table.
 */
data class ActivityInfo(
    val id: String,
    @StringRes val nameRes: Int,
    val icon: ImageVector,
    @PluralsRes val unitRes: Int,
    val isPersonCount: Boolean = true,
)

val activities = listOf(
    ActivityInfo("piscina_25m", R.string.activity_pool, Icons.Filled.Pool, R.plurals.unit_people),
    ActivityInfo("sala_fitness", R.string.activity_fitness_room, Icons.Filled.FitnessCenter, R.plurals.unit_people),
    ActivityInfo("padel", R.string.activity_padel, Icons.Filled.SportsTennis, R.plurals.unit_courts, false),
    ActivityInfo("tennis", R.string.activity_tennis, Icons.Filled.SportsTennis, R.plurals.unit_courts, false),
    ActivityInfo("esquaix", R.string.activity_squash, Icons.Filled.SportsTennis, R.plurals.unit_courts, false),
    ActivityInfo("pavello", R.string.activity_sports_hall, Icons.Filled.SportsBasketball, R.plurals.unit_courts, false),
    ActivityInfo("futbol_sala", R.string.activity_futsal, Icons.Filled.SportsSoccer, R.plurals.unit_courts, false),
    ActivityInfo("futbol_7_11", R.string.activity_football, Icons.Filled.SportsSoccer, R.plurals.unit_pitches, false),
    ActivityInfo("barbell", R.string.activity_barbell_area, Icons.Filled.FitnessCenter, R.plurals.unit_people),
    ActivityInfo("callistenia", R.string.activity_calisthenics, Icons.Filled.AccessibilityNew, R.plurals.unit_people),
    ActivityInfo("rocodrom", R.string.activity_climbing_wall, Icons.Filled.Terrain, R.plurals.unit_people),
)

fun activityById(id: String): ActivityInfo = activities.firstOrNull { it.id == id } ?: activities.first()

/** Spaces measured by capacity (people): pool, rooms, climbing wall… */
val facilities: List<ActivityInfo> get() = activities.filter { it.isPersonCount }

/** Sports played on courts or pitches (measured in units). */
val sports: List<ActivityInfo> get() = activities.filterNot { it.isPersonCount }
