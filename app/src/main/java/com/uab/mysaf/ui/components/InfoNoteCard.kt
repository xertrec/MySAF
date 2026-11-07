package com.uab.mysaf.ui.components

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun InfoNoteCard(
    text: String,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier.fillMaxWidth(),
        color = UabGreen.copy(alpha = 0.09f),
        shape = RoundedCornerShape(16.dp),
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Icon(Icons.Outlined.Info, contentDescription = "Informació", tint = UabGreen)
            Text(
                text,
                modifier = Modifier.padding(start = 10.dp),
                style = MaterialTheme.typography.bodySmall,
                lineHeight = 17.sp,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}
