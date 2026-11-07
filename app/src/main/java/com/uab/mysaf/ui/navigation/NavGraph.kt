package com.uab.mysaf.ui.navigation

import android.content.Intent
import androidx.activity.compose.LocalActivity
import androidx.activity.compose.R
import androidx.compose.animation.SharedTransitionLayout
import androidx.compose.animation.core.spring
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleOut
import androidx.compose.foundation.background
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.core.net.toUri
import androidx.navigation.NavController
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.uab.mysaf.ui.main.MainScreen
import kotlin.reflect.KClass

@Composable
fun NavGraph(
    screenInitial: KClass<*>,
    navController: NavHostController,
) {
    NavHost(
        navController = navController,
        startDestination = screenInitial,
    ) {
        composable(ScreenMain::class) {
            MainScreen(navController)
        }
    }
}