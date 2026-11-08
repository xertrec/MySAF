package com.uab.mysaf.ui.navigation

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Chat
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.outlined.AutoFixHigh
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.foundation.layout.Column
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import androidx.navigation.NavDestination
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.toRoute
import com.uab.mysaf.R
import com.uab.mysaf.ui.chat.ChatScreen
import com.uab.mysaf.ui.screens.AlternativesScreen
import com.uab.mysaf.ui.screens.CatalogScreen
import com.uab.mysaf.ui.screens.HomeScreen
import com.uab.mysaf.ui.screens.MethodologyScreen
import com.uab.mysaf.ui.screens.OccupancyScreen
import com.uab.mysaf.ui.screens.RecommendScreen
import com.uab.mysaf.ui.screens.RecommendationScreen
import com.uab.mysaf.ui.screens.ScheduleScreen
import kotlin.reflect.KClass

private data class Tab(
    val route: Any,
    val routeClass: KClass<*>,
    val labelRes: Int,
    val icon: ImageVector,
    val selectedIcon: ImageVector,
)

private val tabs = listOf(
    Tab(ScreenHome, ScreenHome::class, R.string.nav_home, Icons.Outlined.Home, Icons.Filled.Home),
    Tab(ScreenRecommend, ScreenRecommend::class, R.string.nav_recommendations, Icons.Outlined.AutoFixHigh, Icons.Filled.AutoFixHigh),
    Tab(ScreenChat, ScreenChat::class, R.string.nav_safia, Icons.AutoMirrored.Outlined.Chat, Icons.AutoMirrored.Filled.Chat),
)

private fun NavDestination?.isTab(tab: Tab): Boolean =
    this?.hierarchy?.any { it.hasRoute(tab.routeClass) } == true

@Composable
fun NavGraph(
    screenInitial: KClass<*>,
    navController: NavHostController,
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val destination = backStackEntry?.destination
    val showBottomBar = tabs.any { destination.isTab(it) }

    fun openTab(route: Any) {
        navController.navigate(route) {
            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    Scaffold(
        // Each screen draws its own top bar and handles system insets.
        contentWindowInsets = WindowInsets(0),
        bottomBar = {
            if (showBottomBar) {
                Column {
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                    NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                        tabs.forEach { tab ->
                            val selected = destination.isTab(tab)
                            NavigationBarItem(
                                selected = selected,
                                onClick = { openTab(tab.route) },
                                icon = {
                                    Icon(if (selected) tab.selectedIcon else tab.icon, contentDescription = null)
                                },
                                label = {
                                    Text(
                                        stringResource(tab.labelRes),
                                        fontSize = 12.sp,
                                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                                    )
                                },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = MaterialTheme.colorScheme.primary,
                                    selectedTextColor = MaterialTheme.colorScheme.primary,
                                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                                ),
                            )
                        }
                    }
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = screenInitial,
            modifier = Modifier.padding(innerPadding).consumeWindowInsets(innerPadding),
        ) {
            composable<ScreenHome> {
                HomeScreen(
                    onOpenChat = { openTab(ScreenChat) },
                    onOpenRecommendations = { openTab(ScreenRecommend) },
                    onOpenCatalog = { group -> navController.navigate(ScreenCatalog(group)) },
                    onOpenSchedule = { navController.navigate(ScreenSchedule) },
                    onOpenMethodology = { navController.navigate(ScreenMethodology) },
                )
            }

            composable<ScreenRecommend> {
                RecommendScreen(
                    onSubmit = { activityId, epochDay, hour ->
                        navController.navigate(ScreenRecommendation(activityId, epochDay, hour ?: -1))
                    },
                    onOpenMethodology = { navController.navigate(ScreenMethodology) },
                )
            }

            composable<ScreenChat> {
                ChatScreen(
                    onBack = null,
                    onOpenMethodology = { navController.navigate(ScreenMethodology) },
                )
            }

            composable<ScreenRecommendation> { entry ->
                val route = entry.toRoute<ScreenRecommendation>()
                RecommendationScreen(
                    activityId = route.activityId,
                    epochDay = route.epochDay,
                    hour = route.hour.takeIf { it >= 0 },
                    onBack = { navController.popBackStack() },
                    onOpenOccupancy = { navController.navigate(ScreenOccupancy(it)) },
                    onOpenAlternatives = { id, weekday, hour ->
                        navController.navigate(ScreenAlternatives(id, weekday, hour))
                    },
                )
            }

            composable<ScreenOccupancy> { entry ->
                val route = entry.toRoute<ScreenOccupancy>()
                OccupancyScreen(
                    activityId = route.activityId,
                    onBack = { navController.popBackStack() },
                    onOpenMethodology = { navController.navigate(ScreenMethodology) },
                    onFindAlternatives = { id, weekday, hour ->
                        navController.navigate(ScreenAlternatives(id, weekday, hour))
                    },
                )
            }

            composable<ScreenAlternatives> { entry ->
                val route = entry.toRoute<ScreenAlternatives>()
                AlternativesScreen(
                    activityId = route.activityId,
                    weekday = route.weekday,
                    hour = route.hour,
                    onBack = { navController.popBackStack() },
                    onOpenOccupancy = { navController.navigate(ScreenOccupancy(it)) },
                )
            }

            composable<ScreenCatalog> { entry ->
                val route = entry.toRoute<ScreenCatalog>()
                CatalogScreen(
                    group = route.group,
                    onBack = { navController.popBackStack() },
                    onOpenOccupancy = { navController.navigate(ScreenOccupancy(it)) },
                )
            }

            composable<ScreenSchedule> {
                ScheduleScreen(onBack = { navController.popBackStack() })
            }

            composable<ScreenMethodology> {
                MethodologyScreen(onBack = { navController.popBackStack() })
            }
        }
    }
}
