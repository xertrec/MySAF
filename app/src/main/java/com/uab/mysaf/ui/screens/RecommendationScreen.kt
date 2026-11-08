package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.outlined.BarChart
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material.icons.outlined.WorkspacePremium
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.OccupancyLabel
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.busiestHour
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.data.quietestHours
import com.uab.mysaf.data.weekdayCode
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.LevelIndicator
import com.uab.mysaf.ui.components.OutlinedSurface
import com.uab.mysaf.ui.components.SoftGreenPanel
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import com.uab.mysaf.ui.components.rowColor
import com.uab.mysaf.ui.components.statusText
import java.time.LocalDate

/** P2 step 3: the recommended facility, its best slots and why. */
@Composable
fun RecommendationScreen(
    activityId: String,
    epochDay: Long,
    hour: Int?,
    onBack: () -> Unit,
    onOpenOccupancy: (String) -> Unit,
    onOpenAlternatives: (activityId: String, weekday: String, hour: Int) -> Unit,
) {
    val activity = activityById(activityId)
    val weekday = weekdayCode(LocalDate.ofEpochDay(epochDay).dayOfWeek)
    val dayName = stringResource(weekdayNameRes(weekday))
    val repository = rememberAvailabilityRepository()
    val rows by produceState<List<HourAvailability>?>(null, activityId, weekday) {
        value = loadOrDefault(emptyList()) { repository.dayAvailability(activityId, weekday, allPeriod = false) }
    }
    val best = quietestHours(rows.orEmpty(), 3).sortedBy { it.hour }
    val requested = hour?.let { h -> rows?.firstOrNull { it.hour == h } }
    val alternativesHour = hour ?: busiestHour(rows.orEmpty())

    Scaffold(
        topBar = { AppTopBar(title = stringResource(R.string.result_title), onBack = onBack) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            activity.noteRes?.let { InfoNoteCard(stringResource(it)) }
            // Hero
            SoftGreenPanel {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 20.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(
                        Icons.Outlined.WorkspacePremium,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(40.dp),
                    )
                    Text(
                        stringResource(R.string.result_eyebrow),
                        modifier = Modifier.padding(top = 8.dp),
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 15.sp,
                    )
                    Text(
                        stringResource(activity.nameRes),
                        modifier = Modifier.padding(top = 4.dp),
                        fontWeight = FontWeight.ExtraBold,
                        fontSize = 25.sp,
                        textAlign = TextAlign.Center,
                    )
                    val subtitle = when {
                        hour == null -> stringResource(R.string.result_subtitle_any, dayName)
                        requested != null && occupancyLabel(requested) == OccupancyLabel.QUIET ->
                            stringResource(R.string.result_subtitle_quiet)
                        else -> stringResource(R.string.result_subtitle_busy)
                    }
                    Text(
                        subtitle,
                        modifier = Modifier.padding(top = 6.dp),
                        fontSize = 15.sp,
                        lineHeight = 21.sp,
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                    )
                    if (hour != null && requested != null) {
                        Text(
                            stringResource(
                                R.string.result_selected_slot,
                                stringResource(R.string.hour_range, hour, hour + 1),
                            ),
                            modifier = Modifier.padding(top = 12.dp),
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 14.sp,
                        )
                        LevelIndicator(
                            statusText(requested),
                            rowColor(requested),
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                }
            }

            // Best slots
            OutlinedSurface {
                Column(Modifier.padding(16.dp)) {
                    CardHeader(Icons.Outlined.BarChart, stringResource(R.string.result_best_slots))
                    when {
                        rows == null -> Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                        }
                        best.isEmpty() -> Text(
                            stringResource(R.string.result_no_data),
                            modifier = Modifier.padding(top = 12.dp),
                            fontSize = 14.sp,
                        )
                        else -> best.forEachIndexed { index, row ->
                            if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Text(
                                    stringResource(R.string.hour_range, row.hour, row.hour + 1),
                                    modifier = Modifier.weight(1f),
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 16.sp,
                                )
                                LevelIndicator(statusText(row), rowColor(row))
                            }
                        }
                    }
                }
            }

            // Why
            OutlinedSurface {
                Column(Modifier.padding(16.dp)) {
                    CardHeader(Icons.Outlined.Info, stringResource(R.string.result_why))
                    Text(
                        stringResource(R.string.result_why_body, dayName),
                        modifier = Modifier.padding(top = 8.dp),
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            LinkRow(
                icon = Icons.Outlined.BarChart,
                text = stringResource(R.string.result_view_occupancy),
                onClick = { onOpenOccupancy(activityId) },
            )
            if (alternativesHour != null) {
                LinkRow(
                    icon = Icons.Outlined.SwapHoriz,
                    text = stringResource(R.string.result_view_alternatives),
                    onClick = { onOpenAlternatives(activityId, weekday, alternativesHour) },
                )
            }
        }
    }
}

@Composable
internal fun CardHeader(icon: ImageVector, title: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(22.dp))
        Text(title, modifier = Modifier.padding(start = 10.dp), fontWeight = FontWeight.Bold, fontSize = 17.sp)
    }
}

@Composable
internal fun LinkRow(icon: ImageVector, text: String, onClick: () -> Unit) {
    OutlinedSurface(onClick = onClick) {
        Row(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
            Text(
                text,
                modifier = Modifier.padding(start = 12.dp).weight(1f),
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
            )
            Icon(Icons.Filled.ChevronRight, contentDescription = null)
        }
    }
}
