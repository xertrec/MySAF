package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.Recommendations
import com.uab.mysaf.data.activities
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.ListRowCard
import com.uab.mysaf.ui.components.NotePanel
import com.uab.mysaf.ui.components.RecommendationCard
import com.uab.mysaf.ui.components.RecommendationUi
import com.uab.mysaf.ui.components.ScreenIntro
import com.uab.mysaf.ui.components.capacityText
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import com.uab.mysaf.ui.components.rowColor
import com.uab.mysaf.ui.components.statusText

private class AlternativesData(
    val slot: Map<String, HourAvailability>,
    val recommendations: Recommendations,
)

/** P2 step 5: similar activities and other slots that are usually quieter. */
@Composable
fun AlternativesScreen(
    activityId: String,
    weekday: String,
    hour: Int,
    onBack: () -> Unit,
    onOpenOccupancy: (String) -> Unit,
) {
    val activity = activityById(activityId)
    val dayName = stringResource(weekdayNameRes(weekday))
    val time = stringResource(R.string.time_hour, hour)
    val repository = rememberAvailabilityRepository()
    val data by produceState<AlternativesData?>(null, activityId, weekday, hour) {
        value = AlternativesData(
            slot = loadOrDefault(emptyMap()) { repository.slotForAll(weekday, hour) },
            recommendations = loadOrDefault(Recommendations(null, emptyList())) {
                repository.recommendations(activityId, weekday, hour)
            },
        )
    }

    // Only activities measured the same way (people vs courts) are comparable.
    val similar = activities
        .filter { it.id != activityId && it.isPersonCount == activity.isPersonCount }
        .mapNotNull { info -> data?.slot?.get(info.id)?.takeIf { !it.isClosed }?.let { info to it } }
        .sortedBy { it.second.load }
    val otherSlots = data?.recommendations?.alternatives.orEmpty()
        .filter { it.kind != AlternativeKind.OTHER_ACTIVITY }
    val requested = data?.slot?.get(activityId)

    Scaffold(
        topBar = { AppTopBar(title = stringResource(R.string.alternatives_title), onBack = onBack) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            ScreenIntro(
                title = stringResource(R.string.alternatives_headline),
                body = stringResource(R.string.alternatives_intro, dayName, time),
                modifier = Modifier.padding(bottom = 6.dp),
            )

            if (data == null) {
                Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                }
                return@Column
            }

            if (requested != null) {
                ListRowCard(
                    icon = activity.icon,
                    title = stringResource(activity.nameRes),
                    supporting = stringResource(R.string.alternatives_selected, time, capacityText(activity, requested)),
                    status = statusText(requested),
                    statusColor = rowColor(requested),
                    onClick = { onOpenOccupancy(activityId) },
                )
            }

            SectionTitle(
                stringResource(
                    if (activity.isPersonCount) R.string.alternatives_similar_facilities
                    else R.string.alternatives_similar_sports,
                ),
            )
            if (similar.isEmpty()) {
                Text(stringResource(R.string.alternatives_none), fontSize = 14.sp)
            }
            similar.forEach { (info, row) ->
                ListRowCard(
                    icon = info.icon,
                    title = stringResource(info.nameRes),
                    supporting = capacityText(info, row),
                    status = statusText(row),
                    statusColor = rowColor(row),
                    onClick = { onOpenOccupancy(info.id) },
                )
            }

            if (otherSlots.isNotEmpty()) {
                SectionTitle(stringResource(R.string.alternatives_other_slots, stringResource(activity.nameRes)))
                otherSlots.forEach { RecommendationCard(alternativeUi(it)) }
            }

            NotePanel(
                icon = Icons.Outlined.Info,
                title = stringResource(R.string.alternatives_suggestion_title),
                body = stringResource(R.string.alternatives_suggestion_body),
                modifier = Modifier.padding(top = 10.dp),
            )
        }
    }
}

@Composable
internal fun SectionTitle(text: String) {
    Text(text, modifier = Modifier.padding(top = 8.dp), fontWeight = FontWeight.Bold, fontSize = 17.sp)
}

/** UI model for one [Alternative]; also used by the SAFIA chat. */
@Composable
internal fun alternativeUi(alternative: Alternative): RecommendationUi {
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
