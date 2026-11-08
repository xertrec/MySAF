package com.uab.mysaf.data

import androidx.annotation.DrawableRes
import androidx.annotation.PluralsRes
import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.vectorResource
import com.uab.mysaf.R

/**
 * UI-only catalogue (name, pictogram, unit). Capacity and occupancy come from the Room database
 * (see [AvailabilityRepository]); ids must match the `activity` table.
 */
data class ActivityInfo(
    val id: String,
    @StringRes val nameRes: Int,
    /** Ring-less pictogram, identical to the one in [logoRes] (generated from docs/brand). */
    @DrawableRes val iconRes: Int,
    @PluralsRes val unitRes: Int,
    val isPersonCount: Boolean = true,
) {
    /** Logo in the mySAF style (see docs/brand), used in the app bar and as launcher icon. */
    @get:DrawableRes
    val logoRes: Int get() = when (id) {
        "piscina_25m" -> R.drawable.ic_logo_piscina_25m
        "sala_fitness" -> R.drawable.ic_logo_sala_fitness
        "padel" -> R.drawable.ic_logo_padel
        "tennis" -> R.drawable.ic_logo_tennis
        "esquaix" -> R.drawable.ic_logo_esquaix
        "pavello" -> R.drawable.ic_logo_pavello
        "futbol_sala" -> R.drawable.ic_logo_futbol_sala
        "futbol_7_11" -> R.drawable.ic_logo_futbol_7_11
        "barbell" -> R.drawable.ic_logo_barbell
        "callistenia" -> R.drawable.ic_logo_callistenia
        "rocodrom" -> R.drawable.ic_logo_rocodrom
        else -> R.drawable.ic_logo_main
    }
}

val activities = listOf(
    ActivityInfo("piscina_25m", R.string.activity_pool, R.drawable.ic_sport_piscina_25m, R.plurals.unit_people),
    ActivityInfo("sala_fitness", R.string.activity_fitness_room, R.drawable.ic_sport_sala_fitness, R.plurals.unit_people),
    ActivityInfo("padel", R.string.activity_padel, R.drawable.ic_sport_padel, R.plurals.unit_courts, false),
    ActivityInfo("tennis", R.string.activity_tennis, R.drawable.ic_sport_tennis, R.plurals.unit_courts, false),
    ActivityInfo("esquaix", R.string.activity_squash, R.drawable.ic_sport_esquaix, R.plurals.unit_courts, false),
    ActivityInfo("pavello", R.string.activity_sports_hall, R.drawable.ic_sport_pavello, R.plurals.unit_courts, false),
    ActivityInfo("futbol_sala", R.string.activity_futsal, R.drawable.ic_sport_futbol_sala, R.plurals.unit_courts, false),
    ActivityInfo("futbol_7_11", R.string.activity_football, R.drawable.ic_sport_futbol_7_11, R.plurals.unit_pitches, false),
    ActivityInfo("barbell", R.string.activity_barbell_area, R.drawable.ic_sport_barbell, R.plurals.unit_people),
    ActivityInfo("callistenia", R.string.activity_calisthenics, R.drawable.ic_sport_callistenia, R.plurals.unit_people),
    ActivityInfo("rocodrom", R.string.activity_climbing_wall, R.drawable.ic_sport_rocodrom, R.plurals.unit_people),
)

/** [ActivityInfo.iconRes] as an [ImageVector], for Material `Icon`s. */
val ActivityInfo.icon: ImageVector
    @Composable get() = ImageVector.vectorResource(iconRes)

fun activityById(id: String): ActivityInfo = activities.firstOrNull { it.id == id } ?: activities.first()

/** Spaces measured by capacity (people): pool, rooms, climbing wall… */
val facilities: List<ActivityInfo> get() = activities.filter { it.isPersonCount }

/** Sports played on courts or pitches (measured in units). */
val sports: List<ActivityInfo> get() = activities.filterNot { it.isPersonCount }
