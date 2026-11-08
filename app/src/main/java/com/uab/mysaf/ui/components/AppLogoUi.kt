package com.uab.mysaf.ui.components

import androidx.annotation.DrawableRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.R
import com.uab.mysaf.data.ActivityInfo
import com.uab.mysaf.data.AppLogoStore
import com.uab.mysaf.ui.theme.UabGreen

@Composable
fun rememberAppLogoStore(): AppLogoStore {
    val context = LocalContext.current.applicationContext
    return remember(context) { AppLogoStore.get(context) }
}

/** The logo as a rounded green tile, like the launcher icon. Defaults to the user's current logo. */
@Composable
fun AppLogoBadge(
    modifier: Modifier = Modifier,
    size: Dp = 36.dp,
    @DrawableRes logoRes: Int? = null,
) {
    val state by rememberAppLogoStore().state.collectAsState()
    Box(
        modifier
            .size(size)
            .clip(RoundedCornerShape(size * 0.24f))
            .background(UabGreen),
    ) {
        Image(
            painter = painterResource(logoRes ?: state.logoRes),
            contentDescription = null,
            // The artwork follows the 108dp adaptive-icon grid (ring ≈ 55% of it); zoom in slightly.
            modifier = Modifier.fillMaxSize().graphicsLayer { scaleX = 1.1f; scaleY = 1.1f },
        )
    }
}

/**
 * "Make this my sport" card for an activity screen. Picking a sport switches the in-app logo
 * immediately; the switch also puts it on the home screen (applied when the app is left).
 */
@Composable
fun FavouriteSportCard(activity: ActivityInfo) {
    val store = rememberAppLogoStore()
    val state by store.state.collectAsState()
    val isFavourite = state.favouriteId == activity.id

    if (!isFavourite) {
        OutlinedButton(
            onClick = { store.setFavourite(activity.id) },
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(50),
        ) {
            Icon(Icons.Outlined.FavoriteBorder, contentDescription = null, modifier = Modifier.size(18.dp))
            Text(
                stringResource(R.string.logo_make_my_sport),
                modifier = Modifier.padding(start = 8.dp),
                fontWeight = FontWeight.Bold,
            )
        }
        return
    }

    OutlinedSurface {
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                AppLogoBadge(size = 48.dp, logoRes = activity.logoRes)
                Column(Modifier.weight(1f).padding(start = 12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Filled.Favorite,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(16.dp),
                        )
                        Text(
                            stringResource(R.string.logo_is_my_sport),
                            modifier = Modifier.padding(start = 6.dp),
                            fontWeight = FontWeight.Bold,
                            fontSize = 16.sp,
                        )
                    }
                    Text(
                        stringResource(R.string.logo_in_app_note),
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                TextButton(onClick = { store.setFavourite(null) }) {
                    Text(stringResource(R.string.logo_remove))
                }
            }
            HorizontalDivider(
                color = MaterialTheme.colorScheme.outlineVariant,
                modifier = Modifier.padding(vertical = 12.dp),
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f).padding(end = 12.dp)) {
                    Text(stringResource(R.string.logo_home_screen), fontWeight = FontWeight.Bold, fontSize = 15.sp)
                    Text(
                        stringResource(R.string.logo_home_screen_note),
                        fontSize = 13.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Switch(checked = state.useOnHomeScreen, onCheckedChange = store::setUseOnHomeScreen)
            }
        }
    }
}
