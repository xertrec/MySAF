package com.uab.mysaf.data

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.filled.Pool
import androidx.compose.material.icons.filled.SportsBasketball
import androidx.compose.material.icons.filled.SportsSoccer
import androidx.compose.material.icons.filled.SportsTennis
import androidx.compose.material.icons.filled.Terrain
import androidx.compose.ui.graphics.vector.ImageVector

/** UI catalogue. Real availability metadata will be loaded from daily_counts.json later. */
data class ActivityInfo(
    val id: String,
    val name: String,
    val icon: ImageVector,
    val capacity: Int,
    val countingLabel: String,
    val isPersonCount: Boolean = true,
)

val activities = listOf(
    ActivityInfo("piscina_25m", "Piscina", Icons.Filled.Pool, 120, "persones"),
    ActivityInfo("sala_fitness", "Sala fitness", Icons.Filled.FitnessCenter, 120, "persones"),
    ActivityInfo("padel", "Pàdel", Icons.Filled.SportsTennis, 4, "pistes", false),
    ActivityInfo("tennis", "Tennis", Icons.Filled.SportsTennis, 5, "pistes", false),
    ActivityInfo("esquaix", "Esquaix", Icons.Filled.SportsTennis, 3, "pistes", false),
    ActivityInfo("pavello", "Pavelló", Icons.Filled.SportsBasketball, 4, "pistes", false),
    ActivityInfo("futbol_sala", "Futbol sala", Icons.Filled.SportsSoccer, 2, "pistes", false),
    ActivityInfo("futbol_7_11", "Futbol 7/11", Icons.Filled.SportsSoccer, 2, "camps", false),
    ActivityInfo("barbell", "Espai barbell", Icons.Filled.FitnessCenter, 24, "persones"),
    ActivityInfo("callistenia", "Cal·listènia", Icons.Filled.AccessibilityNew, 20, "persones"),
    ActivityInfo("rocodrom", "Rocòdrom", Icons.Filled.Terrain, 18, "persones"),
)

fun activityById(id: String): ActivityInfo = activities.firstOrNull { it.id == id } ?: activities.first()
