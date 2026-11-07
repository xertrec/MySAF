package com.uab.mysaf.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF79D69A),
    onPrimary = Color(0xFF00391D),
    secondary = Color(0xFFACD4B8),
    background = Color(0xFF101713),
    onBackground = Color(0xFFE5ECE6),
    surface = Color(0xFF18211B),
    onSurface = Color(0xFFE5ECE6),
    surfaceVariant = Color(0xFF29362E),
    outlineVariant = Color(0xFF3A4B3F),
)

private val LightColorScheme = lightColorScheme(
    primary = UabGreen,
    onPrimary = Color.White,
    primaryContainer = UabGreenLight,
    onPrimaryContainer = UabGreenDark,
    secondary = Color(0xFF4E765B),
    background = AppBackground,
    onBackground = TextPrimary,
    surface = Color.White,
    onSurface = TextPrimary,
    surfaceVariant = Color(0xFFE8EEE9),
    onSurfaceVariant = Color(0xFF526057),
    outline = Color(0xFF8D9A91),
    outlineVariant = Color(0xFFD5DDD7),
)

@Composable
fun MySAFTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme,
        typography = Typography,
        content = content,
    )
}
