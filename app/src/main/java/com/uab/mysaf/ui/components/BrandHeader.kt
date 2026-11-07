package com.uab.mysaf.ui.components

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.ui.theme.UabGreen
import com.uab.mysaf.ui.theme.TextPrimary

@Composable
fun BrandHeader(modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.padding(bottom = 18.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("UAB", color = UabGreen, fontSize = 23.sp, fontWeight = FontWeight.ExtraBold)
        Spacer(Modifier.width(10.dp))
        Text("|", color = TextPrimary.copy(alpha = 0.45f), fontSize = 24.sp)
        Spacer(Modifier.width(10.dp))
        Text("SAF", color = TextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Medium)
    }
}
