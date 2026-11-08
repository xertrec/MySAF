package com.uab.mysaf.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.OpeningHours
import com.uab.mysaf.data.todayWeekday
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.LevelIndicator
import com.uab.mysaf.ui.components.NotePanel
import com.uab.mysaf.ui.components.OutlinedSurface
import com.uab.mysaf.ui.components.ScreenIntro
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import com.uab.mysaf.ui.theme.LoadFull
import com.uab.mysaf.ui.theme.LoadQuiet
import java.time.LocalTime

/** General SAF opening hours, with today highlighted and an open/closed indicator. */
@Composable
fun ScheduleScreen(onBack: () -> Unit) {
    val repository = rememberAvailabilityRepository()
    val hours by produceState<List<OpeningHours>?>(null) {
        value = loadOrDefault(emptyList()) { repository.openingHours() }
    }
    val today = todayWeekday()
    val nowMin = LocalTime.now().let { it.hour * 60 + it.minute }
    val todayHours = hours?.firstOrNull { it.weekday == today }

    Scaffold(
        topBar = { AppTopBar(title = stringResource(R.string.home_tile_schedule), onBack = onBack) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            ScreenIntro(
                title = stringResource(R.string.schedule_headline),
                body = stringResource(R.string.schedule_intro),
            )

            if (todayHours != null) {
                val open = todayHours.isOpenAt(nowMin)
                LevelIndicator(
                    text = if (open) {
                        stringResource(R.string.schedule_open_now, minutesText(todayHours.closeMin))
                    } else {
                        stringResource(R.string.schedule_closed_now)
                    },
                    color = if (open) LoadQuiet else LoadFull,
                    fontSize = 15,
                )
            }

            OutlinedSurface {
                Column(Modifier.padding(horizontal = 8.dp, vertical = 6.dp)) {
                    if (hours == null) {
                        Box(Modifier.fillMaxWidth().padding(24.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                        }
                    }
                    hours.orEmpty().forEachIndexed { index, day ->
                        if (index > 0) {
                            HorizontalDivider(
                                color = MaterialTheme.colorScheme.outlineVariant,
                                modifier = Modifier.padding(horizontal = 8.dp),
                            )
                        }
                        val isToday = day.weekday == today
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                                .background(
                                    if (isToday) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerLow,
                                    RoundedCornerShape(10.dp),
                                )
                                .padding(horizontal = 10.dp, vertical = 12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                stringResource(weekdayNameRes(day.weekday)).replaceFirstChar { it.uppercase() },
                                modifier = Modifier.weight(1f),
                                fontWeight = if (isToday) FontWeight.Bold else FontWeight.Medium,
                                fontSize = 16.sp,
                            )
                            if (isToday) {
                                Text(
                                    stringResource(R.string.schedule_today),
                                    modifier = Modifier.padding(end = 12.dp),
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                            Text(
                                stringResource(R.string.schedule_range, minutesText(day.openMin), minutesText(day.closeMin)),
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp,
                            )
                        }
                    }
                }
            }

            NotePanel(
                icon = Icons.Outlined.Info,
                title = null,
                body = stringResource(R.string.schedule_note),
            )
        }
    }
}

@Composable
private fun minutesText(minutes: Int): String = stringResource(R.string.time_hm, minutes / 60, minutes % 60)
