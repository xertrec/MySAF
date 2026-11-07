package com.uab.mysaf.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.ui.theme.UabGreen

data class RecommendationUi(
    val eyebrow: String,
    val title: String,
    val detail: String,
    val reduction: Int,
)

@Composable
fun RecommendationCard(
    recommendation: RecommendationUi,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        border = CardDefaults.outlinedCardBorder(),
    ) {
        Row(
            modifier = Modifier.padding(15.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Filled.CalendarMonth, contentDescription = null, tint = UabGreen)
            Column(
                modifier = Modifier.padding(start = 12.dp).weight(1f),
                verticalArrangement = Arrangement.spacedBy(3.dp),
            ) {
                Text(recommendation.eyebrow, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(recommendation.title, fontSize = 17.sp, fontWeight = FontWeight.Bold, color = UabGreen)
                Text(recommendation.detail, fontSize = 12.sp, lineHeight = 16.sp)
            }
            Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Surface(color = UabGreen.copy(alpha = 0.12f), shape = RoundedCornerShape(50)) {
                    Text(
                        stringResource(R.string.recommendation_reduction, recommendation.reduction),
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp),
                        color = UabGreen,
                        fontWeight = FontWeight.Bold,
                        fontSize = 12.sp,
                    )
                }
                Icon(
                    Icons.Filled.ChevronRight,
                    contentDescription = stringResource(R.string.recommendation_view_content_description),
                    tint = UabGreen,
                )
            }
        }
    }
}
