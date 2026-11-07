package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.data.activities
import com.uab.mysaf.ui.components.ActivityTile
import com.uab.mysaf.ui.components.BrandHeader
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun HomeScreen(
    onActivitySelected: (String) -> Unit,
    onOpenMethodology: () -> Unit,
) {
    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
        ) {
            BrandHeader()
            Text(
                "Quin és el teu moment?",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onBackground,
            )
            Text(
                "Consulta quan acostuma a haver-hi menys ocupació i troba el millor moment per fer esport.",
                modifier = Modifier.padding(top = 8.dp),
                fontSize = 15.sp,
                lineHeight = 22.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Què vols fer?",
                modifier = Modifier.padding(top = 26.dp, bottom = 13.dp),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
            )

            activities.chunked(2).forEach { pair ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    pair.forEach { activity ->
                        ActivityTile(
                            name = activity.name,
                            icon = activity.icon,
                            onClick = { onActivitySelected(activity.id) },
                            modifier = Modifier.weight(1f),
                        )
                    }
                    if (pair.size == 1) Spacer(Modifier.weight(1f))
                }
                Spacer(Modifier.height(11.dp))
            }

            Card(
                onClick = onOpenMethodology,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 18.dp),
                colors = CardDefaults.cardColors(containerColor = UabGreen.copy(alpha = 0.09f)),
                elevation = CardDefaults.cardElevation(defaultElevation = 0.dp),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 17.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(Icons.Outlined.Info, contentDescription = null, tint = UabGreen)
                    Text("Com ho calculem", modifier = Modifier.padding(start = 12.dp).weight(1f), fontWeight = FontWeight.SemiBold)
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Obrir metodologia", tint = UabGreen)
                }
            }
        }
    }
}
