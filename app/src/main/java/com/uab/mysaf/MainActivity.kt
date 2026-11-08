package com.uab.mysaf

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.navigation.compose.rememberNavController
import com.uab.mysaf.data.AppLogoStore
import com.uab.mysaf.data.LauncherIcon
import com.uab.mysaf.ui.navigation.NavGraph
import com.uab.mysaf.ui.navigation.ScreenHome
import com.uab.mysaf.ui.theme.MySAFTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MySAFTheme {
                NavGraph(
                    screenInitial = ScreenHome::class,
                    navController = rememberNavController()
                )
            }
        }
    }

    override fun onStop() {
        super.onStop()
        // Swap the home-screen icon only once the app is in the background, so a launcher
        // refresh never closes it in front of the user.
        if (!isChangingConfigurations) {
            LauncherIcon.apply(this, AppLogoStore.get(this).state.value.launcherId)
        }
    }
}
