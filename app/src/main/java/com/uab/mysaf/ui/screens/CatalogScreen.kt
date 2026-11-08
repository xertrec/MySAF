package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.pluralStringResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.icon
import com.uab.mysaf.data.ActivityInfo
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.facilities
import com.uab.mysaf.data.sports
import com.uab.mysaf.data.todayWeekday
import com.uab.mysaf.ui.components.ListRowCard
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.loadOrDefault
import com.uab.mysaf.ui.components.rememberAvailabilityRepository
import com.uab.mysaf.ui.components.rowColor
import com.uab.mysaf.ui.components.statusText
import com.uab.mysaf.ui.navigation.ScreenCatalog
import java.time.LocalTime

/** Instal·lacions, Esports or both (Ocupació), each with its usual occupancy right now. */
@Composable
fun CatalogScreen(
    group: String,
    onBack: () -> Unit,
    onOpenOccupancy: (String) -> Unit,
) {
    val titleRes = when (group) {
        ScreenCatalog.FACILITIES -> R.string.home_tile_facilities
        ScreenCatalog.SPORTS -> R.string.home_tile_sports
        else -> R.string.home_tile_occupancy
    }
    val introRes = when (group) {
        ScreenCatalog.FACILITIES -> R.string.catalog_intro_facilities
        ScreenCatalog.SPORTS -> R.string.catalog_intro_sports
        else -> R.string.catalog_intro_occupancy
    }
    val repository = rememberAvailabilityRepository()
    val now by produceState<Map<String, HourAvailability>>(emptyMap()) {
        value = loadOrDefault(emptyMap()) { repository.slotForAll(todayWeekday(), LocalTime.now().hour) }
    }

    Scaffold(
        topBar = { AppTopBar(title = stringResource(titleRes), onBack = onBack) },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 18.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                stringResource(introRes),
                fontSize = 15.sp,
                lineHeight = 21.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 4.dp),
            )
            when (group) {
                ScreenCatalog.FACILITIES -> CatalogItems(facilities, now, onOpenOccupancy)
                ScreenCatalog.SPORTS -> CatalogItems(sports, now, onOpenOccupancy)
                else -> {
                    SectionTitle(stringResource(R.string.home_tile_facilities))
                    CatalogItems(facilities, now, onOpenOccupancy)
                    SectionTitle(stringResource(R.string.home_tile_sports))
                    CatalogItems(sports, now, onOpenOccupancy)
                }
            }
        }
    }
}

@Composable
private fun CatalogItems(
    items: List<ActivityInfo>,
    now: Map<String, HourAvailability>,
    onOpen: (String) -> Unit,
) {
    items.forEach { activity ->
        val row = now[activity.id]
        val status = when {
            row == null -> stringResource(R.string.catalog_now_unknown)
            row.isClosed -> stringResource(R.string.catalog_now_closed)
            else -> stringResource(R.string.catalog_now, statusText(row))
        }
        val capacity = row?.capacity
        ListRowCard(
            icon = activity.icon,
            title = stringResource(activity.nameRes),
            supporting = capacity?.let { "$it ${pluralStringResource(activity.unitRes, it)}" },
            status = status,
            statusColor = if (row == null) MaterialTheme.colorScheme.outline else rowColor(row),
            onClick = { onOpen(activity.id) },
        )
    }
}
