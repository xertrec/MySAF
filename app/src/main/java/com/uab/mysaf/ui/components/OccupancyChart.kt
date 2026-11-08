package com.uab.mysaf.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.foundation.background
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.ActivityInfo
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.occupancyLabel
import kotlin.math.roundToInt

private val AxisWidth = 40.dp
private val ChartHeight = 180.dp

/**
 * Vertical bar chart of the average occupancy per hour. Tapping a bar selects it so the caller
 * can show its capacity ("11/40 persones").
 */
@Composable
fun OccupancyChart(
    rows: List<HourAvailability>,
    selectedHour: Int?,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val gridColor = MaterialTheme.colorScheme.outlineVariant
    val axisColor = MaterialTheme.colorScheme.outline
    Column(modifier = modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().height(ChartHeight)) {
            // Y axis labels, aligned with the four grid lines.
            Column(
                modifier = Modifier.width(AxisWidth).fillMaxHeight(),
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                listOf(100, 75, 50, 25, 0).forEach {
                    Text("$it %", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight()
                    .padding(vertical = 7.dp)
                    .drawBehind {
                        for (i in 0..3) {
                            val y = size.height * i / 4f
                            drawLine(gridColor, Offset(0f, y), Offset(size.width, y), strokeWidth = 1f)
                        }
                        drawLine(axisColor, Offset(0f, 0f), Offset(0f, size.height), strokeWidth = 2f)
                        drawLine(axisColor, Offset(0f, size.height), Offset(size.width, size.height), strokeWidth = 2f)
                    },
            ) {
                Row(Modifier.fillMaxSize().padding(start = 4.dp)) {
                    rows.forEach { row ->
                        Bar(
                            row = row,
                            selected = selectedHour == row.hour,
                            dimmed = selectedHour != null && selectedHour != row.hour,
                            onClick = { onSelect(row.hour) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                }
            }
        }
        // X axis: every other hour.
        Row(Modifier.fillMaxWidth().padding(start = AxisWidth + 4.dp, top = 6.dp)) {
            rows.forEach { row ->
                Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                    if (row.hour % 2 == 0) {
                        Text(
                            "${row.hour}",
                            fontSize = 12.sp,
                            textAlign = TextAlign.Center,
                            maxLines = 1,
                            softWrap = false,
                            fontWeight = if (selectedHour == row.hour) FontWeight.Bold else FontWeight.Normal,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun Bar(
    row: HourAvailability,
    selected: Boolean,
    dimmed: Boolean,
    onClick: () -> Unit,
    modifier: Modifier,
) {
    val unavailable = row.isClosed || row.shiftChange
    val fraction = if (unavailable) 0.02f else row.load.coerceIn(0.02f, 1f)
    val color = rowColor(row).copy(alpha = if (dimmed) 0.35f else 1f)
    val description = stringResource(
        R.string.occupancy_bar_description,
        stringResource(R.string.time_hour, row.hour),
        statusText(row),
    )
    Box(
        modifier = modifier
            .fillMaxHeight()
            .clip(RoundedCornerShape(topStart = 4.dp, topEnd = 4.dp))
            .clickable(enabled = !unavailable, role = Role.Button, onClick = onClick)
            .semantics(mergeDescendants = true) {
                contentDescription = description
                this.selected = selected
            },
        contentAlignment = Alignment.BottomCenter,
    ) {
        if (selected) {
            Box(
                Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.08f)),
            )
        }
        Box(
            Modifier
                .fillMaxWidth(0.68f)
                .fillMaxHeight(fraction)
                .clip(RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                .background(color),
        )
    }
}

/** "Ocupació baixa", "Tancat", "Canvi de torn"… */
@Composable
fun statusText(row: HourAvailability): String = when {
    row.isClosed -> stringResource(R.string.status_closed)
    row.shiftChange -> stringResource(R.string.status_shift_change)
    else -> stringResource(levelTextRes(occupancyLabel(row)))
}

/** "Aforament: 11/40 persones" or "Reservades: 3/4 pistes". */
@Composable
fun capacityText(activity: ActivityInfo, row: HourAvailability): String {
    val unit = pluralStringResource(activity.unitRes, row.capacity)
    return if (activity.isPersonCount) {
        stringResource(R.string.occupancy_capacity_people, row.occupied, row.capacity, unit)
    } else {
        stringResource(R.string.occupancy_capacity_units, row.occupied, row.capacity, unit)
    }
}

fun percentOf(row: HourAvailability): Int = (row.load.coerceIn(0f, 1f) * 100f).roundToInt()
