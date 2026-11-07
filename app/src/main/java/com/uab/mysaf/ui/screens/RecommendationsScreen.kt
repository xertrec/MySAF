package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.OccupancyLabel
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.sampleAvailability
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.RecommendationCard
import com.uab.mysaf.ui.components.RecommendationUi
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
    val day = stringResource(weekdayNameRes(weekday))
    val selectedTime = stringResource(R.string.time_hour, hour)
    val requestedLoad = sampleAvailability(activity, weekday, allPeriod = false)
        .firstOrNull { it.hour == hour }
        ?.let { it.occupied.toFloat() / it.capacity.coerceAtLeast(1) }
    val fitnessActivity = activityById("sala_fitness")
    val activityName = stringResource(activity.nameRes)

    val rawAlternatives = listOf(
        Triple(
            RecommendationUi(
                eyebrow = stringResource(R.string.recommendation_same_activity_today),
                title = stringResource(R.string.recommendation_today_time),
                detail = "",
                reduction = 0,
            ),
            activity,
            0.37f,
        ),
        Triple(
            RecommendationUi(
                eyebrow = stringResource(R.string.recommendation_same_activity_another_day),
                title = stringResource(R.string.recommendation_tuesday_time, selectedTime),
                detail = "",
                reduction = 0,
            ),
            activity,
            0.73f,
        ),
        Triple(
            RecommendationUi(
                eyebrow = stringResource(R.string.recommendation_alternative_activity),
                title = stringResource(R.string.recommendation_fitness_time, selectedTime),
                detail = "",
                reduction = 0,
            ),
            fitnessActivity,
            0.70f,
        ),
    )

    val alternatives = rawAlternatives.mapNotNull { (candidate, candidateActivity, targetLoad) ->
        val reduction = (((requestedLoad ?: 0f) - targetLoad) * 100).toInt()
        if (reduction < 10) return@mapNotNull null

        val occupied = (candidateActivity.capacity * targetLoad).toInt().coerceIn(0, candidateActivity.capacity)
        val occupancyLabelRes = when {
            targetLoad < 0.5f -> OccupancyLabel.QUIET.labelRes
            targetLoad < 0.8f -> OccupancyLabel.MODERATE.labelRes
            else -> OccupancyLabel.FULL.labelRes
        }
        val label = stringResource(occupancyLabelRes)
        val unitLabel = pluralStringResource(candidateActivity.unitRes, candidateActivity.capacity)
        val detail = if (candidateActivity.isPersonCount) {
            stringResource(
                R.string.recommendation_people_detail,
                occupied,
                candidateActivity.capacity,
                unitLabel,
                label,
            )
        } else {
            stringResource(
                R.string.recommendation_units_detail,
                candidateActivity.capacity - occupied,
                candidateActivity.capacity,
                unitLabel,
                label,
            )
        }
        candidate.copy(detail = detail, reduction = reduction)
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = activityName,
                onBack = onBack,
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                color = UabGreen.copy(alpha = 0.10f),
            ) {
                Column(modifier = Modifier.padding(17.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = UabGreen)
                        Text(
                            stringResource(R.string.recommendations_title),
                            modifier = Modifier.padding(start = 9.dp),
                            fontWeight = FontWeight.Bold,
                            fontSize = 17.sp,
                        )
                    }
                    Text(
                        text = if (requestedLoad != null && requestedLoad < 0.5f) {
                            stringResource(R.string.recommendations_already_quiet, day, selectedTime)
                        } else {
                            stringResource(R.string.recommendations_lower_load, day, selectedTime)
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
                        stringResource(R.string.recommendations_good_time),
                        modifier = Modifier.padding(16.dp),
                        color = UabGreen,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            } else if (alternatives.isEmpty()) {
                Text(stringResource(R.string.recommendations_none), fontSize = 14.sp)
            } else {
                alternatives.forEach { recommendation ->
                    RecommendationCard(recommendation = recommendation)
                }
            }

            InfoNoteCard(
                stringResource(R.string.recommendations_historical_note),
                modifier = Modifier.padding(top = 2.dp),
            )
            TextButton(
                onClick = onOpenMethodology,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            ) {
                Text(stringResource(R.string.action_methodology), color = UabGreen)
            }
            Text(
                stringResource(R.string.recommendations_demo_note),
                modifier = Modifier.padding(bottom = 18.dp),
                fontSize = 11.sp,
                lineHeight = 15.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
