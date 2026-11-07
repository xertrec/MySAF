package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.MethodologySection

@Composable
fun MethodologyScreen(onBack: () -> Unit) {
    val limitations = listOf(
        R.string.methodology_limit_1,
        R.string.methodology_limit_2,
        R.string.methodology_limit_3,
        R.string.methodology_limit_4,
        R.string.methodology_limit_5,
        R.string.methodology_limit_6,
        R.string.methodology_limit_7,
    )

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.methodology_title),
                onBack = onBack,
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp, vertical = 10.dp),
        ) {
            Text(
                stringResource(R.string.methodology_intro),
                modifier = Modifier.padding(top = 8.dp),
                fontSize = 14.sp,
                lineHeight = 20.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            MethodologySection(
                title = stringResource(R.string.methodology_sources_title),
                body = stringResource(R.string.methodology_sources_body),
            )
            MethodologySection(
                title = stringResource(R.string.methodology_period_title),
                body = stringResource(R.string.methodology_period_body),
            )
            MethodologySection(
                title = stringResource(R.string.methodology_occupancy_title),
                body = stringResource(R.string.methodology_occupancy_body),
            )
            MethodologySection(
                title = stringResource(R.string.methodology_labels_title),
                body = stringResource(R.string.methodology_labels_body),
            )

            Text(
                stringResource(R.string.methodology_limitations_title),
                modifier = Modifier.padding(top = 14.dp, bottom = 6.dp),
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            limitations.forEach { limitRes ->
                InfoNoteCard(
                    stringResource(limitRes),
                    modifier = Modifier.padding(vertical = 4.dp),
                )
            }
            Text(
                stringResource(R.string.methodology_privacy),
                modifier = Modifier.padding(top = 12.dp, bottom = 22.dp),
                fontSize = 12.sp,
                lineHeight = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
