package com.uab.mysaf.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun PeriodSelector(
    allPeriod: Boolean,
    onPeriodChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        PeriodOption(
            title = stringResource(R.string.period_term_title),
            subtitle = stringResource(R.string.period_term_subtitle),
            selected = !allPeriod,
            onClick = { onPeriodChange(false) },
            modifier = Modifier.weight(1f),
        )
        PeriodOption(
            title = stringResource(R.string.period_all_title),
            subtitle = stringResource(R.string.period_all_subtitle),
            selected = allPeriod,
            onClick = { onPeriodChange(true) },
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun PeriodOption(
    title: String,
    subtitle: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        onClick = onClick,
        modifier = modifier,
        shape = RoundedCornerShape(15.dp),
        color = if (selected) UabGreen else MaterialTheme.colorScheme.surface,
        contentColor = if (selected) androidx.compose.ui.graphics.Color.White else MaterialTheme.colorScheme.onSurface,
        border = if (selected) null else BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        androidx.compose.foundation.layout.Column(
            modifier = Modifier.padding(vertical = 10.dp, horizontal = 8.dp),
            horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally,
        ) {
            Text(title, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, textAlign = TextAlign.Center)
            Text(subtitle, fontSize = 11.sp, textAlign = TextAlign.Center)
        }
    }
}
