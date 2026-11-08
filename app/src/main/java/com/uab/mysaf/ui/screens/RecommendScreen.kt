package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.DirectionsRun
import androidx.compose.material.icons.outlined.CalendarToday
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.Stadium
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.OpeningHours
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.facilities
import com.uab.mysaf.data.sports
import com.uab.mysaf.data.weekdayCode
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.DropdownField
import com.uab.mysaf.ui.components.PrimaryButton
import com.uab.mysaf.ui.components.ScreenIntro
import com.uab.mysaf.ui.components.SegmentOption
import com.uab.mysaf.ui.components.SegmentedToggle
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/** P2 steps 1–2: pick facility or sport, date and (optionally) a time slot. */
@Composable
fun RecommendScreen(
    onSubmit: (activityId: String, epochDay: Long, hour: Int?) -> Unit,
    onOpenMethodology: () -> Unit,
) {
    var typeIndex by rememberSaveable { mutableIntStateOf(0) }
    var facilityId by rememberSaveable { mutableStateOf(facilities.first { it.id == "sala_fitness" }.id) }
    var sportId by rememberSaveable { mutableStateOf(sports.first().id) }
    val today = LocalDate.now().toEpochDay()
    var epochDay by rememberSaveable { mutableLongStateOf(today) }
    // -1 = any time.
    var hour by rememberSaveable { mutableIntStateOf(-1) }

    val repository = rememberAvailabilityRepository()
    val openingHours by produceState<List<OpeningHours>>(emptyList()) {
        value = loadOrDefault(emptyList()) { repository.openingHours() }
    }
    val weekday = weekdayCode(LocalDate.ofEpochDay(epochDay).dayOfWeek)
    val dayHours = openingHours.firstOrNull { it.weekday == weekday }
        ?.let { (it.openMin / 60) until ((it.closeMin + 59) / 60) }
        ?.toList()
        ?: (7..20).toList()
    val hourOptions = listOf(-1) + dayHours
    // A slot chosen for another day may fall outside today's opening hours.
    val selectedHour = if (hour in hourOptions) hour else -1

    val group = if (typeIndex == 0) facilities else sports
    val activityId = if (typeIndex == 0) facilityId else sportId

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.nav_recommendations),
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
                .padding(horizontal = 16.dp, vertical = 20.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            ScreenIntro(
                title = stringResource(R.string.recommend_headline),
                body = stringResource(R.string.recommend_intro),
            )

            Column {
                Text(
                    stringResource(R.string.recommend_type),
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                    modifier = Modifier.padding(bottom = 8.dp),
                )
                SegmentedToggle(
                    options = listOf(
                        SegmentOption(stringResource(R.string.recommend_type_facility), Icons.Outlined.Stadium),
                        SegmentOption(stringResource(R.string.recommend_type_sport), Icons.AutoMirrored.Outlined.DirectionsRun),
                    ),
                    selectedIndex = typeIndex,
                    onSelected = { typeIndex = it },
                )
            }

            DropdownField(
                label = stringResource(if (typeIndex == 0) R.string.recommend_type_facility else R.string.recommend_type_sport),
                leadingIcon = Icons.Outlined.Stadium,
                options = group.map { it.id },
                selected = activityId,
                optionLabel = { stringResource(activityById(it).nameRes) },
                optionIcon = { activityById(it).icon },
                onSelected = { if (typeIndex == 0) facilityId = it else sportId = it },
            )

            DropdownField(
                label = stringResource(R.string.recommend_date),
                leadingIcon = Icons.Outlined.CalendarToday,
                options = (0L..6L).map { today + it },
                selected = epochDay,
                optionLabel = { dateLabel(it, today) },
                onSelected = { epochDay = it },
            )

            DropdownField(
                label = stringResource(R.string.recommend_slot),
                leadingIcon = Icons.Outlined.Schedule,
                options = hourOptions,
                selected = selectedHour,
                optionLabel = {
                    if (it < 0) stringResource(R.string.recommend_any_hour)
                    else stringResource(R.string.hour_range, it, it + 1)
                },
                onSelected = { hour = it },
            )

            PrimaryButton(
                text = stringResource(R.string.recommend_submit),
                onClick = { onSubmit(activityId, epochDay, selectedHour.takeIf { it >= 0 }) },
                modifier = Modifier.padding(top = 12.dp),
            )
        }
    }
}

/** "Avui, 8 nov", "Demà, 9 nov", "dt., 10 nov"… in the app language. */
@Composable
internal fun dateLabel(epochDay: Long, today: Long): String {
    val locale = androidx.compose.ui.platform.LocalConfiguration.current.locales[0] ?: Locale.getDefault()
    val date = LocalDate.ofEpochDay(epochDay)
    val short = date.format(DateTimeFormatter.ofPattern("d MMM", locale)).trimEnd('.')
    return when (epochDay - today) {
        0L -> stringResource(R.string.date_today, short)
        1L -> stringResource(R.string.date_tomorrow, short)
        else -> date.format(DateTimeFormatter.ofPattern("EEEE, d MMM", locale)).trimEnd('.')
            .replaceFirstChar { it.uppercase() }
    }
}
