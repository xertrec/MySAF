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
import androidx.compose.ui.unit.dp
import com.uab.mysaf.ui.theme.UabGreen

private val weekdays = listOf("dl", "dt", "dc", "dj", "dv", "ds", "dg")

@Composable
fun WeekdaySelector(
    selected: String,
    onSelected: (String) -> Unit,
) {
    Row(
        modifier = Modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        weekdays.forEach { day ->
            FilterChip(
                selected = selected == day,
                onClick = { onSelected(day) },
                label = { Text(day) },
                shape = RoundedCornerShape(12.dp),
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = UabGreen,
                    selectedLabelColor = androidx.compose.ui.graphics.Color.White,
                ),
            )
        }
    }
}
