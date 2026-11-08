package com.uab.mysaf.ui.components

import androidx.annotation.StringRes
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.OccupancyLabel
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.ui.theme.LoadFull
import com.uab.mysaf.ui.theme.LoadModerate
import com.uab.mysaf.ui.theme.LoadQuiet

val CardShape = RoundedCornerShape(16.dp)

/* ---------- Occupancy level helpers ---------- */

fun levelColor(label: OccupancyLabel): Color = when (label) {
    OccupancyLabel.QUIET -> LoadQuiet
    OccupancyLabel.MODERATE -> LoadModerate
    OccupancyLabel.FULL -> LoadFull
}

@StringRes
fun levelTextRes(label: OccupancyLabel): Int = when (label) {
    OccupancyLabel.QUIET -> R.string.occupancy_level_quiet
    OccupancyLabel.MODERATE -> R.string.occupancy_level_moderate
    OccupancyLabel.FULL -> R.string.occupancy_level_full
}

/** Colour for a row: grey when closed or unreliable, otherwise by occupancy level. */
@Composable
fun rowColor(row: HourAvailability): Color =
    if (row.isClosed || row.shiftChange) MaterialTheme.colorScheme.outline
    else levelColor(occupancyLabel(row))

@Composable
fun LevelDot(color: Color, size: Dp = 10.dp) {
    Box(Modifier.size(size).background(color, CircleShape))
}

/** "● Ocupació baixa" */
@Composable
fun LevelIndicator(text: String, color: Color, modifier: Modifier = Modifier, fontSize: Int = 13) {
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        LevelDot(color)
        Text(
            text,
            modifier = Modifier.padding(start = 8.dp),
            fontSize = fontSize.sp,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

/* ---------- Containers ---------- */

/** White card with a hairline border, the base container of the redesign. */
@Composable
fun OutlinedSurface(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    val border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    if (onClick != null) {
        Surface(
            onClick = onClick,
            modifier = modifier.fillMaxWidth(),
            shape = CardShape,
            color = MaterialTheme.colorScheme.surfaceContainerLow,
            border = border,
            shadowElevation = 1.dp,
        ) { content() }
    } else {
        Surface(
            modifier = modifier.fillMaxWidth(),
            shape = CardShape,
            color = MaterialTheme.colorScheme.surfaceContainerLow,
            border = border,
            shadowElevation = 1.dp,
        ) { content() }
    }
}

/** Soft green panel used for highlights, tips and summaries. */
@Composable
fun SoftGreenPanel(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    val color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f)
    if (onClick != null) {
        Surface(onClick = onClick, modifier = modifier.fillMaxWidth(), shape = CardShape, color = color) { content() }
    } else {
        Surface(modifier = modifier.fillMaxWidth(), shape = CardShape, color = color) { content() }
    }
}

/** Round, light green badge holding an icon. */
@Composable
fun IconBadge(icon: ImageVector, size: Dp = 44.dp, iconSize: Dp = 24.dp) {
    Box(
        modifier = Modifier
            .size(size)
            .background(MaterialTheme.colorScheme.primaryContainer, CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(iconSize))
    }
}

/** Row card: badge, title, coloured status line and chevron. */
@Composable
fun ListRowCard(
    icon: ImageVector,
    title: String,
    status: String?,
    statusColor: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    supporting: String? = null,
) {
    OutlinedSurface(modifier = modifier, onClick = onClick) {
        Row(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconBadge(icon)
            Column(modifier = Modifier.padding(start = 14.dp).weight(1f)) {
                Text(title, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                if (supporting != null) {
                    Text(
                        supporting,
                        fontSize = 12.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 1.dp),
                    )
                }
                if (status != null) {
                    LevelIndicator(status, statusColor, modifier = Modifier.padding(top = 4.dp))
                }
            }
            Icon(
                Icons.Filled.ChevronRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}

/** Tip / explanation panel with an info-style icon and optional title. */
@Composable
fun NotePanel(
    icon: ImageVector,
    title: String?,
    body: String,
    modifier: Modifier = Modifier,
) {
    SoftGreenPanel(modifier = modifier) {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
                if (title != null) {
                    Text(
                        title,
                        modifier = Modifier.padding(start = 10.dp),
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                    )
                }
            }
            Text(
                body,
                modifier = Modifier.padding(top = 8.dp),
                fontSize = 14.sp,
                lineHeight = 20.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f),
            )
        }
    }
}

/* ---------- Inputs ---------- */

data class SegmentOption(val label: String, val icon: ImageVector? = null)

/**
 * Segmented control. [filled] draws the grey track of the Ocupació tabs; otherwise each
 * option is an outlined pill as in the recommendation form.
 */
@Composable
fun SegmentedToggle(
    options: List<SegmentOption>,
    selectedIndex: Int,
    onSelected: (Int) -> Unit,
    modifier: Modifier = Modifier,
    filled: Boolean = false,
) {
    val track = if (filled) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(track, RoundedCornerShape(14.dp))
            .padding(if (filled) 4.dp else 0.dp),
        horizontalArrangement = Arrangement.spacedBy(if (filled) 0.dp else 8.dp),
    ) {
        options.forEachIndexed { index, option ->
            val selected = index == selectedIndex
            Surface(
                onClick = { onSelected(index) },
                modifier = Modifier.weight(1f).height(if (filled) 38.dp else 46.dp),
                shape = RoundedCornerShape(if (filled) 11.dp else 12.dp),
                color = when {
                    selected -> MaterialTheme.colorScheme.primary
                    filled -> Color.Transparent
                    else -> MaterialTheme.colorScheme.surface
                },
                contentColor = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                border = if (!filled && !selected) BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant) else null,
            ) {
                Row(
                    modifier = Modifier.fillMaxSize(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (option.icon != null) {
                        Icon(option.icon, contentDescription = null, modifier = Modifier.size(20.dp))
                    }
                    Text(
                        option.label,
                        modifier = Modifier.padding(start = if (option.icon != null) 8.dp else 0.dp),
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                        fontSize = 15.sp,
                        textAlign = TextAlign.Center,
                    )
                }
            }
        }
    }
}

/** Labelled dropdown field: "Data" + [📅 Avui, 7 nov ⌄]. */
@Composable
fun <T> DropdownField(
    label: String,
    leadingIcon: ImageVector,
    options: List<T>,
    selected: T,
    optionLabel: @Composable (T) -> String,
    onSelected: (T) -> Unit,
    modifier: Modifier = Modifier,
    optionIcon: ((T) -> ImageVector?)? = null,
) {
    var expanded by remember { mutableStateOf(false) }
    Column(modifier = modifier.fillMaxWidth()) {
        Text(label, fontWeight = FontWeight.Bold, fontSize = 15.sp, modifier = Modifier.padding(bottom = 8.dp))
        Box {
            Surface(
                onClick = { expanded = true },
                modifier = Modifier.fillMaxWidth().height(52.dp),
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 14.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Icon(
                        optionIcon?.invoke(selected) ?: leadingIcon,
                        contentDescription = null,
                        modifier = Modifier.size(22.dp),
                    )
                    Text(
                        optionLabel(selected),
                        modifier = Modifier.padding(start = 14.dp).weight(1f),
                        fontSize = 16.sp,
                    )
                    Icon(Icons.Filled.KeyboardArrowDown, contentDescription = null)
                }
            }
            DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                options.forEach { option ->
                    val itemIcon = optionIcon?.invoke(option)
                    DropdownMenuItem(
                        text = { Text(optionLabel(option)) },
                        leadingIcon = if (itemIcon != null) {
                            { Icon(itemIcon, contentDescription = null, tint = MaterialTheme.colorScheme.primary) }
                        } else {
                            null
                        },
                        onClick = {
                            onSelected(option)
                            expanded = false
                        },
                    )
                }
            }
        }
    }
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    icon: ImageVector? = null,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().height(54.dp),
        shape = RoundedCornerShape(50),
        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
        contentPadding = PaddingValues(horizontal = 20.dp),
    ) {
        if (icon != null) {
            Icon(icon, contentDescription = null, modifier = Modifier.size(20.dp))
        }
        Text(
            text,
            modifier = Modifier.padding(start = if (icon != null) 8.dp else 0.dp),
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp,
        )
    }
}

/** Big screen headline + supporting paragraph ("Què vols fer?"). */
@Composable
fun ScreenIntro(title: String, body: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(title, fontSize = 26.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 32.sp)
        Text(
            body,
            modifier = Modifier.padding(top = 8.dp),
            fontSize = 15.sp,
            lineHeight = 21.sp,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
