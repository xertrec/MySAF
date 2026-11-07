package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.data.activityById
import com.uab.mysaf.data.quieterHour
import com.uab.mysaf.data.sampleAvailability
import com.uab.mysaf.data.weekdayName
import com.uab.mysaf.ui.components.HourlyAvailabilityRow
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.PeriodSelector
import com.uab.mysaf.ui.components.ScreenHeader
import com.uab.mysaf.ui.components.WeekdaySelector
import com.uab.mysaf.ui.theme.UabGreen
import java.time.DayOfWeek
import java.time.LocalDate

private fun todayShortDay(): String = when (LocalDate.now().dayOfWeek) {
    DayOfWeek.MONDAY -> "dl"
    DayOfWeek.TUESDAY -> "dt"
    DayOfWeek.WEDNESDAY -> "dc"
    DayOfWeek.THURSDAY -> "dj"
    DayOfWeek.FRIDAY -> "dv"
    DayOfWeek.SATURDAY -> "ds"
    DayOfWeek.SUNDAY -> "dg"
}

@Composable
fun ActivityScreen(
    activityId: String,
    onBack: () -> Unit,
    onOpenMethodology: () -> Unit,
    onFindAlternatives: (String, String, Int) -> Unit,
) {
    val activity = activityById(activityId)
    var selectedDay by rememberSaveable { mutableStateOf(todayShortDay()) }
    var allPeriod by rememberSaveable { mutableStateOf(false) }
    var selectedHour by rememberSaveable { mutableStateOf<Int?>(null) }
    val rows = sampleAvailability(activity, selectedDay, allPeriod)
    val quietHour = quieterHour(rows)

    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 10.dp),
        ) {
            ScreenHeader(
                title = activity.name,
                onBack = onBack,
                trailing = {
                    androidx.compose.material3.IconButton(onClick = onOpenMethodology) {
                        Icon(Icons.Outlined.Info, contentDescription = "Com ho calculem", tint = UabGreen)
                    }
                },
            )
            PeriodSelector(allPeriod = allPeriod, onPeriodChange = { allPeriod = it; selectedHour = null })
            WeekdaySelector(selected = selectedDay, onSelected = { selectedDay = it; selectedHour = null })

            InfoNoteCard(
                text = "Franja més tranquil·la de ${weekdayName(selectedDay)}: ${quietHour?.let { "%02d:00".format(it) } ?: "—"}",
                modifier = Modifier.padding(top = 14.dp),
            )

            Row(
                modifier = Modifier.fillMaxWidth().padding(top = 19.dp, bottom = 9.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text("Disponibilitat per hores", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            }
            Text(
                weekdayName(selectedDay).replaceFirstChar { it.uppercase() },
                modifier = Modifier.padding(bottom = 8.dp),
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 13.sp,
            )

            Column(
                modifier = Modifier.fillMaxWidth(),
            ) {
                rows.forEachIndexed { index, row ->
                    HourlyAvailabilityRow(
                        row = row,
                        isPersonCount = activity.isPersonCount,
                        unitLabel = activity.countingLabel,
                        selected = selectedHour == row.hour,
                        onClick = { selectedHour = row.hour },
                    )
                    if (index < rows.lastIndex) {
                        androidx.compose.material3.HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.65f))
                    }
                }
            }

            if (rows.any { it.longBlock }) {
                Text(
                    "Algunes franges poden incloure blocs de club o escola.",
                    modifier = Modifier.padding(top = 8.dp),
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Button(
                onClick = { selectedHour?.let { onFindAlternatives(activity.id, selectedDay, it) } },
                enabled = selectedHour != null,
                modifier = Modifier.fillMaxWidth().padding(top = 18.dp, bottom = 12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = UabGreen),
            ) {
                Icon(Icons.Outlined.Schedule, contentDescription = null)
                Text(
                    if (selectedHour == null) "Selecciona una hora" else "Troba alternatives per a les ${"%02d:00".format(selectedHour)}",
                    modifier = Modifier.padding(start = 8.dp),
                    fontWeight = FontWeight.SemiBold,
                )
            }

            Text(
                "Dades d'exemple per a la maqueta. Les xifres definitives es calcularan al dispositiu a partir de daily_counts.json.",
                modifier = Modifier.padding(bottom = 20.dp),
                fontSize = 11.sp,
                lineHeight = 15.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
