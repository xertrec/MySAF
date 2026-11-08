package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Eco
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.SwapHoriz
import androidx.compose.material.icons.outlined.TouchApp
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.icon
import com.uab.mysaf.data.ActivityInfo
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.quietRanges
import com.uab.mysaf.data.todayWeekday
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.FavouriteSportCard
import com.uab.mysaf.ui.components.LevelIndicator
import com.uab.mysaf.ui.components.OccupancyChart
import com.uab.mysaf.ui.components.OutlinedSurface
import com.uab.mysaf.ui.components.PrimaryButton
import com.uab.mysaf.ui.components.SegmentOption
import com.uab.mysaf.ui.components.SegmentedToggle
import com.uab.mysaf.ui.components.SoftGreenPanel
import com.uab.mysaf.ui.components.WeekdaySelector
import com.uab.mysaf.ui.components.capacityText
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.percentOf
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import com.uab.mysaf.ui.components.rowColor
import com.uab.mysaf.ui.components.statusText

private const val TAB_TODAY = 0
private const val TAB_WEEK = 1
private const val TAB_HISTORY = 2

/**
 * P2 step 4. Avui = today's weekday (term time); Setmana = any weekday (term time);
 * Històric = any weekday over the whole April–October period.
 */
@Composable
fun OccupancyScreen(
    activityId: String,
    onBack: () -> Unit,
    onOpenMethodology: () -> Unit,
    onFindAlternatives: (activityId: String, weekday: String, hour: Int) -> Unit,
) {
    val activity = activityById(activityId)
    val today = todayWeekday()
    var tab by rememberSaveable { mutableIntStateOf(TAB_TODAY) }
    var pickedDay by rememberSaveable { mutableStateOf(today) }
    var selectedHour by rememberSaveable { mutableStateOf<Int?>(null) }

    val weekday = if (tab == TAB_TODAY) today else pickedDay
    val allPeriod = tab == TAB_HISTORY
    val dayName = stringResource(weekdayNameRes(weekday))

    val repository = rememberAvailabilityRepository()
    val rows by produceState<List<HourAvailability>?>(null, activityId, weekday, allPeriod) {
        value = null
        value = loadOrDefault(emptyList()) { repository.dayAvailability(activityId, weekday, allPeriod) }
    }
    val selectedRow = rows?.firstOrNull { it.hour == selectedHour }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.occupancy_title),
                onBack = onBack,
                actions = {
                    IconButton(onClick = onOpenMethodology) {
                        Icon(Icons.Outlined.Info, contentDescription = stringResource(R.string.action_methodology))
                    }
                },
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    activity.icon,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(28.dp),
                )
                Text(
                    stringResource(activity.nameRes),
                    modifier = Modifier.padding(start = 12.dp),
                    fontWeight = FontWeight.ExtraBold,
                    fontSize = 23.sp,
                )
            }

            FavouriteSportCard(activity)

            SegmentedToggle(
                options = listOf(
                    SegmentOption(stringResource(R.string.tab_today)),
                    SegmentOption(stringResource(R.string.tab_week)),
                    SegmentOption(stringResource(R.string.tab_history)),
                ),
                selectedIndex = tab,
                onSelected = { tab = it; selectedHour = null },
                filled = true,
            )

            if (tab != TAB_TODAY) {
                WeekdaySelector(selected = pickedDay, onSelected = { pickedDay = it; selectedHour = null })
            }

            OutlinedSurface {
                Column(Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.occupancy_chart_title), fontWeight = FontWeight.Bold, fontSize = 17.sp)
                    Text(
                        when (tab) {
                            TAB_TODAY -> stringResource(R.string.occupancy_sub_today, dayName)
                            TAB_WEEK -> stringResource(R.string.occupancy_sub_week, dayName.replaceFirstChar { it.uppercase() })
                            else -> stringResource(R.string.occupancy_sub_history, dayName.replaceFirstChar { it.uppercase() })
                        },
                        fontSize = 14.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 2.dp, bottom = 14.dp),
                    )
                    when {
                        rows == null -> Box(Modifier.fillMaxWidth().height(200.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                        }
                        rows!!.isEmpty() -> Text(stringResource(R.string.activity_no_data), fontSize = 14.sp)
                        else -> OccupancyChart(
                            rows = rows!!,
                            selectedHour = selectedHour,
                            onSelect = { selectedHour = if (selectedHour == it) null else it },
                        )
                    }

                    HorizontalDivider(
                        color = MaterialTheme.colorScheme.outlineVariant,
                        modifier = Modifier.padding(top = 14.dp, bottom = 12.dp),
                    )
                    if (selectedRow != null) {
                        SelectedHourDetail(activity, selectedRow)
                    } else {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Outlined.TouchApp,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(18.dp),
                            )
                            Text(
                                stringResource(R.string.occupancy_tap_hint),
                                modifier = Modifier.padding(start = 8.dp),
                                fontSize = 13.sp,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }

            if (selectedRow != null) {
                PrimaryButton(
                    text = stringResource(
                        R.string.occupancy_find_alternatives,
                        stringResource(R.string.time_hour, selectedRow.hour),
                    ),
                    icon = Icons.Outlined.SwapHoriz,
                    onClick = { onFindAlternatives(activityId, weekday, selectedRow.hour) },
                )
            }

            val ranges = quietRanges(rows.orEmpty())
            if (ranges.isNotEmpty()) {
                SoftGreenPanel {
                    Column(Modifier.padding(16.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Outlined.Eco,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(22.dp),
                            )
                            Text(
                                stringResource(R.string.occupancy_quiet_ranges),
                                modifier = Modifier.padding(start = 10.dp),
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                            )
                        }
                        Text(
                            joinRanges(ranges.map { stringResource(R.string.hour_range, it.first, it.last) }),
                            modifier = Modifier.padding(top = 6.dp, start = 32.dp),
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun SelectedHourDetail(activity: ActivityInfo, row: HourAvailability) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(
                stringResource(R.string.hour_range, row.hour, row.hour + 1),
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
            )
            LevelIndicator(statusText(row), rowColor(row), modifier = Modifier.padding(top = 4.dp))
        }
        Column(horizontalAlignment = Alignment.End) {
            Text(
                capacityText(activity, row),
                fontWeight = FontWeight.ExtraBold,
                fontSize = 17.sp,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                stringResource(R.string.occupancy_percentage, percentOf(row)),
                fontSize = 13.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
    if (row.lowData || row.longBlock) {
        Text(
            stringResource(if (row.lowData) R.string.status_low_data else R.string.activity_long_blocks_note),
            modifier = Modifier.padding(top = 6.dp),
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/** "a", "a i b", "a, b i c". */
@Composable
internal fun joinRanges(parts: List<String>): String = when (parts.size) {
    0 -> ""
    1 -> parts[0]
    else -> stringResource(R.string.ranges_and, parts.dropLast(1).joinToString(", "), parts.last())
}
