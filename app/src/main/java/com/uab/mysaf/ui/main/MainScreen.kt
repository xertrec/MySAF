package com.uab.mysaf.ui.main

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Chat
import androidx.compose.material.icons.automirrored.outlined.Chat
import androidx.compose.material.icons.filled.House
import androidx.compose.material.icons.outlined.House
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavController

@Composable
fun MainScreen(
    navController: NavController
) {
    var currentScreen by remember { mutableStateOf(Screens.MAIN) }
    Scaffold(
        modifier = Modifier.fillMaxSize(),
        bottomBar = {
            NavigationBar(
                modifier = Modifier.fillMaxWidth()
            ) {
                NavigationBarItem(
                    selected = currentScreen == Screens.MAIN,
                    onClick = {
                        currentScreen = Screens.MAIN
                    },
                    icon = {
                        Icon(
                            imageVector = if (currentScreen == Screens.MAIN) Icons.Filled.House
                            else Icons.Outlined.House,
                            contentDescription = null
                        )
                    }
                )
                NavigationBarItem(
                    selected = currentScreen == Screens.CHAT,
                    onClick = {
                        currentScreen = Screens.CHAT
                    },
                    icon = {
                        Icon(
                            imageVector = if (currentScreen == Screens.CHAT) Icons.AutoMirrored.Filled.Chat
                            else Icons.AutoMirrored.Outlined.Chat,
                            contentDescription = null
                        )
                    }
                )
            }
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier.padding(innerPadding)
        ) { }
    }
}

private enum class Screens {
    MAIN,
    CHAT;
}