package com.uab.mysaf.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.OccupancyLabel
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.ui.theme.LoadFull
import com.uab.mysaf.ui.theme.LoadModerate
import com.uab.mysaf.ui.theme.LoadQuiet

@Composable
fun HourlyAvailabilityRow(
    row: HourAvailability,
    isPersonCount: Boolean,
    unitRes: Int,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val ratio = (row.occupied.toFloat() / row.capacity.coerceAtLeast(1)).coerceIn(0f, 1f)
    val label = occupancyLabel(row)
    val specialStatus = when {
        row.isClosed -> stringResource(R.string.status_closed)
        row.shiftChange -> stringResource(R.string.status_shift_change)
        row.lowData -> stringResource(R.string.status_low_data)
        else -> stringResource(label.labelRes)
    }
    val loadColor = when {
        row.isClosed || row.shiftChange -> MaterialTheme.colorScheme.onSurfaceVariant
        row.lowData -> LoadModerate
        else -> when (label) {
            OccupancyLabel.QUIET -> LoadQuiet
            OccupancyLabel.MODERATE -> LoadModerate
            OccupancyLabel.FULL -> LoadFull
        }
    }
    val unitLabel = pluralStringResource(unitRes, row.capacity)
    val metric = when {
        row.isClosed || row.shiftChange -> ""
        isPersonCount -> stringResource(R.string.activity_metric_occupied, row.occupied, row.capacity, unitLabel)
        else -> stringResource(R.string.activity_metric_available, row.capacity - row.occupied, row.capacity, unitLabel)
    }
    val hourLabel = stringResource(R.string.time_hour, row.hour)
    val accessibilityMetric = if (metric.isBlank()) "" else stringResource(R.string.activity_accessibility_metric, metric)
    val accessibleText = stringResource(R.string.activity_accessibility_description, hourLabel, specialStatus, accessibilityMetric)

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .semantics { contentDescription = accessibleText }
            .clickable(enabled = !row.isClosed && !row.shiftChange, onClick = onClick),
        color = if (selected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.45f) else MaterialTheme.colorScheme.surface,
        border = if (selected) BorderStroke(1.dp, MaterialTheme.colorScheme.primary) else null,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 11.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(hourLabel, modifier = Modifier.width(48.dp), fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                if (!row.isClosed && !row.shiftChange) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(9.dp)
                            .clip(RoundedCornerShape(20.dp))
                            .background(MaterialTheme.colorScheme.surfaceVariant),
                    ) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth(ratio)
                                .height(9.dp)
                                .clip(RoundedCornerShape(20.dp))
                                .background(loadColor),
                        )
                    }
                }
                Text(specialStatus, color = loadColor, fontSize = 11.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.width(9.dp))
            Text(
                metric,
                modifier = Modifier.width(102.dp),
                fontSize = 10.sp,
                lineHeight = 13.sp,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}
