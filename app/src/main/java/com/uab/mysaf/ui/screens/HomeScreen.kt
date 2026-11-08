package com.uab.mysaf.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.FitnessCenter
import androidx.compose.material.icons.outlined.BarChart
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.SportsTennis
import androidx.compose.material.icons.outlined.Stadium
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.ui.components.BrandTopBar
import com.uab.mysaf.ui.components.CardShape
import com.uab.mysaf.ui.components.OutlinedSurface
import com.uab.mysaf.ui.components.SoftGreenPanel
import com.uab.mysaf.ui.navigation.ScreenCatalog
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun HomeScreen(
    onOpenChat: () -> Unit,
    onOpenRecommendations: () -> Unit,
    onOpenCatalog: (String) -> Unit,
    onOpenSchedule: () -> Unit,
    onOpenMethodology: () -> Unit,
) {
    Scaffold(
        topBar = {
            BrandTopBar {
                IconButton(onClick = onOpenMethodology) {
                    Icon(Icons.Outlined.Info, contentDescription = stringResource(R.string.action_methodology))
                }
            }
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            SafiaCard(onClick = onOpenChat)
            RecommendationsCard(onClick = onOpenRecommendations)

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ShortcutTile(
                    icon = Icons.Outlined.Stadium,
                    label = stringResource(R.string.home_tile_facilities),
                    onClick = { onOpenCatalog(ScreenCatalog.FACILITIES) },
                    modifier = Modifier.weight(1f),
                )
                ShortcutTile(
                    icon = Icons.Outlined.SportsTennis,
                    label = stringResource(R.string.home_tile_sports),
                    onClick = { onOpenCatalog(ScreenCatalog.SPORTS) },
                    modifier = Modifier.weight(1f),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                ShortcutTile(
                    icon = Icons.Outlined.Schedule,
                    label = stringResource(R.string.home_tile_schedule),
                    onClick = onOpenSchedule,
                    modifier = Modifier.weight(1f),
                )
                ShortcutTile(
                    icon = Icons.Outlined.BarChart,
                    label = stringResource(R.string.home_tile_occupancy),
                    onClick = { onOpenCatalog(ScreenCatalog.ALL) },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

/** Dark green entry point to the SAFIA assistant. */
@Composable
private fun SafiaCard(onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = CardShape,
        color = UabGreen,
        contentColor = Color.White,
        shadowElevation = 2.dp,
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(54.dp).background(Color.White.copy(alpha = 0.16f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = Color.White, modifier = Modifier.size(28.dp))
            }
            Column(modifier = Modifier.padding(start = 16.dp).weight(1f)) {
                Text(stringResource(R.string.home_chat_title), fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Text(
                    stringResource(R.string.home_chat_subtitle),
                    modifier = Modifier.padding(top = 4.dp),
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                    color = Color.White.copy(alpha = 0.88f),
                )
            }
            Icon(
                Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = stringResource(R.string.home_chat_open),
                tint = Color.White,
                modifier = Modifier.padding(start = 8.dp),
            )
        }
    }
}

/** Light green entry point to the recommendation engine. */
@Composable
private fun RecommendationsCard(onClick: () -> Unit) {
    SoftGreenPanel(onClick = onClick) {
        Row(
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(54.dp)
                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.12f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    Icons.Filled.FitnessCenter,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(28.dp),
                )
            }
            Column(modifier = Modifier.padding(start = 16.dp).weight(1f)) {
                Text(stringResource(R.string.home_reco_title), fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Text(
                    stringResource(R.string.home_reco_subtitle),
                    modifier = Modifier.padding(top = 4.dp),
                    fontSize = 13.sp,
                    lineHeight = 18.sp,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f),
                )
            }
            Icon(
                Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(start = 8.dp),
            )
        }
    }
}

@Composable
private fun ShortcutTile(
    icon: ImageVector,
    label: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    OutlinedSurface(modifier = modifier.height(96.dp), onClick = onClick) {
        Column(
            modifier = Modifier.fillMaxSize().padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(30.dp))
            Text(
                label,
                modifier = Modifier.padding(top = 8.dp),
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp,
                textAlign = TextAlign.Center,
            )
        }
    }
}
