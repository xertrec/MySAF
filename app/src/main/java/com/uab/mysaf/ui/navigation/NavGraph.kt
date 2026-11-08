package com.uab.mysaf.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.toRoute
import com.uab.mysaf.ui.chat.ChatScreen
import com.uab.mysaf.ui.screens.ActivityScreen
import com.uab.mysaf.ui.screens.HomeScreen
import com.uab.mysaf.ui.screens.MethodologyScreen
import com.uab.mysaf.ui.screens.RecommendationsScreen
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
        composable<ScreenHome> {
            HomeScreen(
                onActivitySelected = { activityId ->
                    navController.navigate(ScreenActivity(activityId))
                },
                onOpenMethodology = {
                    navController.navigate(ScreenMethodology)
                },
                onOpenChat = {
                    navController.navigate(ScreenChat)
                },
            )
        }

        composable<ScreenChat> {
            ChatScreen(
                onBack = { navController.popBackStack() },
                onOpenMethodology = {
                    navController.navigate(ScreenMethodology)
                },
            )
        }

        composable<ScreenActivity> { backStackEntry ->
            val route = backStackEntry.toRoute<ScreenActivity>()
            ActivityScreen(
                activityId = route.activityId,
                onBack = { navController.popBackStack() },
                onOpenMethodology = {
                    navController.navigate(ScreenMethodology)
                },
                onFindAlternatives = { activityId, weekday, hour ->
                    navController.navigate(
                        ScreenRecommendations(
                            activityId = activityId,
                            weekday = weekday,
                            hour = hour,
                        ),
                    )
                },
            )
        }

        composable<ScreenRecommendations> { backStackEntry ->
            val route = backStackEntry.toRoute<ScreenRecommendations>()
            RecommendationsScreen(
                activityId = route.activityId,
                weekday = route.weekday,
                hour = route.hour,
                onBack = { navController.popBackStack() },
                onOpenMethodology = {
                    navController.navigate(ScreenMethodology)
                },
            )
        }

        composable<ScreenMethodology> {
            MethodologyScreen(
                onBack = { navController.popBackStack() },
            )
        }
    }
}
