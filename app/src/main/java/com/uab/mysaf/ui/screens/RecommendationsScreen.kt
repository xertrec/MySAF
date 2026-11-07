package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.sampleAvailability
import com.uab.mysaf.data.weekdayName
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.RecommendationCard
import com.uab.mysaf.ui.components.RecommendationUi
import com.uab.mysaf.ui.components.ScreenHeader
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun RecommendationsScreen(
    activityId: String,
    weekday: String,
    hour: Int,
    onBack: () -> Unit,
    onOpenMethodology: () -> Unit,
) {
    val activity = activityById(activityId)
    val day = weekdayName(weekday)
    val selectedTime = "%02d:00".format(hour)
    val requestedLoad = sampleAvailability(activity, weekday, allPeriod = false)
        .firstOrNull { it.hour == hour }
        ?.let { it.occupied.toFloat() / it.capacity.coerceAtLeast(1) }
    val fitnessActivity = activityById("sala_fitness")
    val alternatives = listOf(
        Triple(RecommendationUi("Mateixa activitat, avui", "14:00", "", 0), activity, 0.37f),
        Triple(RecommendationUi("Mateixa activitat, un altre dia", "Dimarts a les $selectedTime", "", 0), activity, 0.73f),
        Triple(RecommendationUi("Activitat alternativa", "Sala fitness · $selectedTime", "", 0), fitnessActivity, 0.70f),
    ).mapNotNull { (candidate, candidateActivity, targetLoad) ->
        val reduction = (((requestedLoad ?: 0f) - targetLoad) * 100).toInt()
        if (reduction < 10) return@mapNotNull null
        val occupied = (candidateActivity.capacity * targetLoad).toInt().coerceIn(0, candidateActivity.capacity)
        val label = when {
            targetLoad < 0.5f -> "Tranquil"
            targetLoad < 0.8f -> "Moderat"
            else -> "Ple"
        }
        val detail = if (candidateActivity.isPersonCount) {
            "≈ $occupied de ${candidateActivity.capacity} ${candidateActivity.countingLabel} · $label"
        } else {
            "≈ ${candidateActivity.capacity - occupied} de ${candidateActivity.capacity} ${candidateActivity.countingLabel} lliures · $label"
        }
        candidate.copy(detail = detail, reduction = reduction)
    }

    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            ScreenHeader(title = activity.name, onBack = onBack)
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                color = UabGreen.copy(alpha = 0.10f),
            ) {
                Column(modifier = Modifier.padding(17.dp)) {
                    androidx.compose.foundation.layout.Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = UabGreen)
                        Text("Alternatives més tranquil·les", modifier = Modifier.padding(start = 9.dp), fontWeight = FontWeight.Bold, fontSize = 17.sp)
                    }
                    Text(
                        if (requestedLoad != null && requestedLoad < 0.5f) {
                            "Per $day a les $selectedTime, ja has triat una franja habitualment tranquil·la."
                        } else {
                            "Per $day a les $selectedTime, aquestes opcions tenen una ocupació estimada més baixa."
                        },
                        modifier = Modifier.padding(top = 10.dp),
                        fontSize = 13.sp,
                        lineHeight = 19.sp,
                    )
                }
            }

            if (requestedLoad != null && requestedLoad < 0.5f) {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = UabGreen.copy(alpha = 0.10f),
                ) {
                    Text(
                        "Bon moment! Aquesta franja ja acostuma a ser tranquil·la.",
                        modifier = Modifier.padding(16.dp),
                        color = UabGreen,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            } else if (alternatives.isEmpty()) {
                Text("No hem trobat alternatives prou més tranquil·les per a aquesta hora.", fontSize = 14.sp)
            } else {
                alternatives.forEach { recommendation ->
                    RecommendationCard(recommendation = recommendation)
                }
            }

            InfoNoteCard(
                "Dades: mitjanes històriques del període lectiu (abril–juny i setembre–octubre de 2026). Es compten reserves; no és una ocupació en temps real.",
                modifier = Modifier.padding(top = 2.dp),
            )
            androidx.compose.material3.TextButton(onClick = onOpenMethodology, modifier = Modifier.align(Alignment.CenterHorizontally)) {
                Text("Com ho calculem", color = UabGreen)
            }
            Text(
                "Recomanacions de demostració: es connectaran al motor local i aplicaran el llindar de 10 punts percentuals.",
                modifier = Modifier.padding(bottom = 18.dp),
                fontSize = 11.sp,
                lineHeight = 15.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
