package com.uab.mysaf.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.uab.mysaf.ui.components.InfoNoteCard
import com.uab.mysaf.ui.components.MethodologySection
import com.uab.mysaf.ui.components.ScreenHeader

@Composable
fun MethodologyScreen(onBack: () -> Unit) {
    Scaffold { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 18.dp, vertical = 10.dp),
        ) {
            ScreenHeader(title = "Com ho calculem", onBack = onBack)
            Text(
                "Una estimació basada en l'històric de reserves del SAF. Tots els càlculs es fan localment al dispositiu.",
                modifier = Modifier.padding(top = 8.dp),
                fontSize = 14.sp,
                lineHeight = 20.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            MethodologySection(
                title = "Fonts de dades",
                body = "Llibre de dades del SAF: fulls «Espais», «Horari general» i «Reserves». Les dades es processen prèviament i l'app només rep comptatges agregats per activitat, dia i franja horària.",
            )
            MethodologySection(
                title = "Període de referència",
                body = "Per defecte s'utilitzen abril, maig, juny, setembre i octubre de 2026 (període lectiu). També es pot consultar tot el període d'abril a octubre.",
            )
            MethodologySection(
                title = "Com calculem l'ocupació",
                body = "Sales i piscines: mitjana de persones amb una reserva que coincideix amb la franja, dividida per l'aforament. Pistes i camps: mitjana d'unitats reservades dividida pel nombre d'unitats disponibles. Les reserves llargues compten com a ocupades i es poden marcar com a blocs de club o escola.",
            )
            MethodologySection(
                title = "Etiquetes",
                body = "Tranquil: menys del 50%. Moderat: del 50% a menys del 80%. Ple: 80% o més. Una alternativa només es proposa quan és almenys 10 punts percentuals més tranquil·la que la franja seleccionada.",
            )

            Text("Límits de les dades", modifier = Modifier.padding(top = 14.dp, bottom = 6.dp), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            val limitations = listOf(
                "Mostra l'ocupació habitual (mitjana històrica), no en temps real.",
                "Compta reserves, no persones que realment hi han anat.",
                "Període per defecte: abril–juny i setembre–octubre de 2026; juliol i agost tenen molta menys activitat.",
                "Les pistes es compten com a ocupades o lliures; les sales i piscines, en persones.",
                "Les dades no tenen identificadors: l'app no sap qui ets ni et personalitza.",
                "Les franges amb menys de 8 dies observats es marquen com a «poques dades».",
                "Els canvis de torn de la sala fitness (10 h i 15 h) no tenen dades.",
            )
            limitations.forEach { limit ->
                InfoNoteCard(limit, modifier = Modifier.padding(vertical = 4.dp))
            }
            Text(
                "Privacitat: aquesta aplicació no necessita connexió a Internet, no incorpora analítica i no envia dades fora del dispositiu.",
                modifier = Modifier.padding(top = 12.dp, bottom = 22.dp),
                fontSize = 12.sp,
                lineHeight = 18.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
