package com.uab.mysaf.ui.components

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.uab.mysaf.R
import com.uab.mysaf.ui.theme.UabGreen

private val weekdays = listOf(
    "dl" to R.string.weekday_monday_short,
    "dt" to R.string.weekday_tuesday_short,
    "dc" to R.string.weekday_wednesday_short,
    "dj" to R.string.weekday_thursday_short,
    "dv" to R.string.weekday_friday_short,
    "ds" to R.string.weekday_saturday_short,
    "dg" to R.string.weekday_sunday_short,
)

@Composable
fun WeekdaySelector(
    selected: String,
    onSelected: (String) -> Unit,
) {
    Row(
        modifier = Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        weekdays.forEach { (dayCode, labelRes) ->
            FilterChip(
                selected = selected == dayCode,
                onClick = { onSelected(dayCode) },
                label = { Text(stringResource(labelRes)) },
                shape = RoundedCornerShape(12.dp),
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = UabGreen,
                    selectedLabelColor = Color.White,
                ),
            )
        }
    }
}
