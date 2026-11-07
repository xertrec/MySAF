package com.uab.mysaf

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.navigation.compose.rememberNavController
import com.uab.mysaf.ui.navigation.NavGraph
import com.uab.mysaf.ui.navigation.ScreenMain
import com.uab.mysaf.ui.theme.MySAFTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MySAFTheme {
                NavGraph(
                    screenInitial = ScreenMain::class,
                    navController = rememberNavController()
                )
            }
        }
    }
}