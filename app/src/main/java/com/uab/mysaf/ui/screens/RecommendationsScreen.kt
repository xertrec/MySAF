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
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.Alternative
import com.uab.mysaf.data.AlternativeKind
import com.uab.mysaf.data.Recommendations
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.RecommendationCard
import com.uab.mysaf.ui.components.RecommendationUi
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
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
    val activityName = stringResource(activity.nameRes)
    val repository = rememberAvailabilityRepository()
    // null while loading.
    val recommendations by produceState<Recommendations?>(null, activityId, weekday, hour) {
        value = loadOrDefault(Recommendations(requested = null, alternatives = emptyList())) {
            repository.recommendations(activityId, weekday, hour)
        }
    }
    val alreadyQuiet = recommendations?.isAlreadyQuiet == true
    val alternatives = recommendations?.alternatives.orEmpty().map { alternativeUi(it) }

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
                        text = if (alreadyQuiet) {
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

            if (alreadyQuiet) {
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
            } else if (recommendations == null) {
                Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = UabGreen)
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

@Composable
private fun alternativeUi(alternative: Alternative): RecommendationUi {
    val candidate = activityById(alternative.activityId)
    val row = alternative.row
    val time = stringResource(R.string.time_hour, row.hour)
    val (eyebrowRes, title) = when (alternative.kind) {
        AlternativeKind.SAME_DAY ->
            R.string.recommendation_same_activity_same_day to time
        AlternativeKind.OTHER_DAY ->
            R.string.recommendation_same_activity_another_day to stringResource(
                R.string.recommendation_day_time,
                stringResource(weekdayNameRes(alternative.weekday)).replaceFirstChar { it.uppercase() },
                time,
            )
        AlternativeKind.OTHER_ACTIVITY ->
            R.string.recommendation_alternative_activity to stringResource(
                R.string.recommendation_activity_time,
                stringResource(candidate.nameRes),
                time,
            )
    }
    val label = stringResource(occupancyLabel(row).labelRes)
    val unitLabel = pluralStringResource(candidate.unitRes, row.capacity)
    val detail = if (candidate.isPersonCount) {
        stringResource(R.string.recommendation_people_detail, row.occupied, row.capacity, unitLabel, label)
    } else {
        stringResource(
            R.string.recommendation_units_detail,
            (row.capacity - row.occupied).coerceAtLeast(0),
            row.capacity,
            unitLabel,
            label,
        )
    }
    return RecommendationUi(
        eyebrow = stringResource(eyebrowRes),
        title = title,
        detail = detail,
        reduction = alternative.reductionPp,
    )
}
