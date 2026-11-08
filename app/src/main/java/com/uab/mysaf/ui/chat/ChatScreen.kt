package com.uab.mysaf.ui.chat

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.union
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.outlined.AddComment
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.IconButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.uab.mysaf.R
import com.uab.mysaf.data.Alternative
import com.uab.mysaf.data.AlternativeKind
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.OccupancyLabel
import com.uab.mysaf.data.chat.RecommendationDto
import com.uab.mysaf.data.chat.SafiaException
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.data.weekdayNameRes
import com.uab.mysaf.ui.components.AppTopBar
import com.uab.mysaf.ui.components.RecommendationCard
import com.uab.mysaf.ui.screens.alternativeUi
import com.uab.mysaf.ui.theme.LoadFull
import com.uab.mysaf.ui.theme.LoadModerate
import com.uab.mysaf.ui.theme.LoadQuiet
import com.uab.mysaf.ui.theme.UabGreen
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.floatOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

@Composable
fun ChatScreen(
    onBack: () -> Unit,
    onOpenMethodology: () -> Unit,
) {
    val context = LocalContext.current.applicationContext
    val viewModel: ChatViewModel = viewModel {
        ChatViewModel(ChatViewModel.repository(context), createSavedStateHandle())
    }
    val ui by viewModel.ui.collectAsState()
    val locale = chatLocale()
    var input by rememberSaveable { mutableStateOf("") }
    val listState = rememberLazyListState()

    fun submit(text: String) {
        if (text.isBlank() || ui.isSending) return
        viewModel.send(text, locale)
        input = ""
    }

    // Keep the newest message (or the typing indicator / error) in view.
    val itemCount = ui.messages.size + (if (ui.isSending || ui.error != null) 1 else 0)
    LaunchedEffect(itemCount) {
        if (itemCount > 0) listState.animateScrollToItem(itemCount - 1)
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.chat_title),
                onBack = onBack,
                actions = {
                    if (ui.messages.isNotEmpty()) {
                        IconButton(onClick = viewModel::newConversation, enabled = !ui.isSending) {
                            Icon(
                                Icons.Outlined.AddComment,
                                contentDescription = stringResource(R.string.chat_new_conversation),
                                tint = UabGreen,
                            )
                        }
                    }
                },
            )
        },
        bottomBar = {
            ChatInputBar(
                value = input,
                onValueChange = { input = it },
                enabled = !ui.isSending,
                onSend = { submit(input) },
            )
        },
    ) { innerPadding ->
        if (ui.messages.isEmpty() && !ui.isSending && ui.error == null) {
            ChatWelcome(
                modifier = Modifier.padding(innerPadding),
                onSuggestion = ::submit,
                onOpenMethodology = onOpenMethodology,
            )
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize().padding(innerPadding),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 14.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(ui.messages, key = { it.id }) { message ->
                    if (message.fromUser) UserBubble(message.text) else AssistantMessage(message)
                }
                if (ui.isSending) {
                    item(key = "typing") { TypingIndicator() }
                } else if (ui.error != null) {
                    item(key = "error") {
                        ChatErrorCard(ui.error!!, onRetry = { viewModel.retry(locale) })
                    }
                }
            }
        }
    }
}

/** App UI language sent to the backend as a tie-breaker; SAFIA replies in the user's language. */
@Composable
private fun chatLocale(): String {
    val language = LocalConfiguration.current.locales[0].language
    return when (language) {
        "en", "es" -> language
        else -> "ca"
    }
}

@Composable
private fun ChatWelcome(
    modifier: Modifier,
    onSuggestion: (String) -> Unit,
    onOpenMethodology: () -> Unit,
) {
    val suggestions = listOf(
        stringResource(R.string.chat_suggestion_1),
        stringResource(R.string.chat_suggestion_2),
        stringResource(R.string.chat_suggestion_3),
        stringResource(R.string.chat_suggestion_4),
    )
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(11.dp),
    ) {
        item {
            Column {
                SafiaAvatar(size = 48)
                Text(
                    stringResource(R.string.chat_headline),
                    modifier = Modifier.padding(top = 14.dp),
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.ExtraBold,
                    color = MaterialTheme.colorScheme.onBackground,
                )
                Text(
                    stringResource(R.string.chat_intro),
                    modifier = Modifier.padding(top = 8.dp),
                    fontSize = 15.sp,
                    lineHeight = 22.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    stringResource(R.string.chat_suggestions_heading),
                    modifier = Modifier.padding(top = 26.dp, bottom = 2.dp),
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
        items(suggestions) { suggestion ->
            Card(
                onClick = { onSuggestion(suggestion) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                border = CardDefaults.outlinedCardBorder(),
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 15.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        suggestion,
                        modifier = Modifier.weight(1f),
                        fontSize = 14.sp,
                        lineHeight = 19.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = null,
                        tint = UabGreen,
                        modifier = Modifier.padding(start = 10.dp),
                    )
                }
            }
        }
        item {
            Surface(
                modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
                color = UabGreen.copy(alpha = 0.09f),
                shape = RoundedCornerShape(16.dp),
            ) {
                Column(Modifier.padding(14.dp)) {
                    Row(verticalAlignment = Alignment.Top) {
                        Icon(
                            Icons.Outlined.Info,
                            contentDescription = stringResource(R.string.content_description_info),
                            tint = UabGreen,
                        )
                        Text(
                            stringResource(R.string.chat_disclaimer),
                            modifier = Modifier.padding(start = 10.dp),
                            style = MaterialTheme.typography.bodySmall,
                            lineHeight = 17.sp,
                        )
                    }
                    TextButton(onClick = onOpenMethodology, modifier = Modifier.align(Alignment.End)) {
                        Text(stringResource(R.string.action_methodology), color = UabGreen)
                    }
                }
            }
        }
    }
}

@Composable
private fun SafiaAvatar(size: Int = 32) {
    Box(
        modifier = Modifier
            .size(size.dp)
            .background(UabGreen.copy(alpha = 0.12f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            Icons.Filled.AutoAwesome,
            contentDescription = null,
            tint = UabGreen,
            modifier = Modifier.size((size * 0.55f).dp),
        )
    }
}

@Composable
private fun UserBubble(text: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
        Surface(
            modifier = Modifier.widthIn(max = 300.dp).padding(start = 48.dp),
            color = UabGreen,
            contentColor = Color.White,
            shape = RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 4.dp),
        ) {
            Text(
                text,
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                fontSize = 15.sp,
                lineHeight = 21.sp,
            )
        }
    }
}

@Composable
private fun AssistantMessage(message: ChatMessageUi) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        SafiaAvatar()
        Column(
            modifier = Modifier.padding(start = 10.dp, end = 24.dp).weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shape = RoundedCornerShape(topStart = 4.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 18.dp),
                border = CardDefaults.outlinedCardBorder(),
                shadowElevation = 1.dp,
            ) {
                Column(Modifier.padding(horizontal = 14.dp, vertical = 11.dp)) {
                    Text(
                        message.text,
                        fontSize = 15.sp,
                        lineHeight = 21.sp,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    val notes = message.limitations.mapNotNull { limitationRes(it) }.distinct()
                    if (message.sources.isNotEmpty() || notes.isNotEmpty()) {
                        HorizontalDivider(
                            modifier = Modifier.padding(top = 10.dp, bottom = 8.dp),
                            color = MaterialTheme.colorScheme.outlineVariant,
                        )
                    }
                    message.sources.forEach { label ->
                        Text(
                            stringResource(R.string.chat_source, label),
                            fontSize = 11.sp,
                            lineHeight = 15.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = UabGreen,
                        )
                    }
                    notes.forEach { res ->
                        Text(
                            "· " + stringResource(res),
                            modifier = Modifier.padding(top = 3.dp),
                            fontSize = 11.sp,
                            lineHeight = 15.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
            message.recommendation?.let { RecommendationBlock(it) }
        }
    }
}

/** Renders the P2 output attached to a reply with the same cards as the rest of the app. */
@Composable
private fun RecommendationBlock(recommendation: RecommendationDto) {
    when (recommendation.type) {
        "alternatives" -> {
            val alternatives = parseAlternatives(recommendation.data)
            alternatives.forEach { RecommendationCard(alternativeUi(it)) }
        }
        "quieter_slots" -> {
            val slots = parseSlots(recommendation.data)
            if (slots.isEmpty()) return
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                slots.forEach { (weekday, row) -> QuietSlotRow(weekday, row) }
            }
        }
    }
}

@Composable
private fun QuietSlotRow(weekday: String, row: HourAvailability) {
    val label = occupancyLabel(row)
    val color = when (label) {
        OccupancyLabel.QUIET -> LoadQuiet
        OccupancyLabel.MODERATE -> LoadModerate
        OccupancyLabel.FULL -> LoadFull
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        color = UabGreen.copy(alpha = 0.07f),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(Modifier.size(10.dp).background(color, CircleShape))
            Text(
                stringResource(
                    R.string.recommendation_day_time,
                    stringResource(weekdayNameRes(weekday)).replaceFirstChar { it.uppercase() },
                    stringResource(R.string.time_hour, row.hour),
                ),
                modifier = Modifier.padding(start = 10.dp).weight(1f),
                fontWeight = FontWeight.SemiBold,
                fontSize = 14.sp,
            )
            Text(
                stringResource(R.string.chat_slot_detail, stringResource(label.labelRes), (row.load * 100).toInt()),
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun TypingIndicator() {
    Row(verticalAlignment = Alignment.CenterVertically) {
        SafiaAvatar()
        Surface(
            modifier = Modifier.padding(start = 10.dp),
            color = MaterialTheme.colorScheme.surface,
            shape = RoundedCornerShape(topStart = 4.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 18.dp),
            border = CardDefaults.outlinedCardBorder(),
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                val transition = rememberInfiniteTransition(label = "typing")
                repeat(3) { index ->
                    val alpha by transition.animateFloat(
                        initialValue = 0.25f,
                        targetValue = 1f,
                        animationSpec = infiniteRepeatable(
                            animation = tween(durationMillis = 500, delayMillis = index * 150),
                            repeatMode = RepeatMode.Reverse,
                        ),
                        label = "dot$index",
                    )
                    Box(Modifier.size(7.dp).alpha(alpha).background(UabGreen, CircleShape))
                }
                Text(
                    stringResource(R.string.chat_thinking),
                    modifier = Modifier.padding(start = 6.dp),
                    fontSize = 13.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun ChatErrorCard(error: SafiaException, onRetry: () -> Unit) {
    val text = when (error.code) {
        SafiaException.NETWORK -> R.string.chat_error_network
        SafiaException.RATE_LIMITED -> R.string.chat_error_rate_limited
        SafiaException.LLM_NOT_CONFIGURED -> R.string.chat_error_not_configured
        else -> R.string.chat_error_generic
    }
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = LoadFull.copy(alpha = 0.10f),
        shape = RoundedCornerShape(16.dp),
    ) {
        Column(Modifier.padding(14.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Icon(Icons.Outlined.ErrorOutline, contentDescription = null, tint = LoadFull)
                Text(
                    stringResource(text),
                    modifier = Modifier.padding(start = 10.dp),
                    style = MaterialTheme.typography.bodySmall,
                    lineHeight = 17.sp,
                )
            }
            if (error.retryable) {
                TextButton(onClick = onRetry, modifier = Modifier.align(Alignment.End)) {
                    Text(stringResource(R.string.chat_retry), color = UabGreen, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun ChatInputBar(
    value: String,
    onValueChange: (String) -> Unit,
    enabled: Boolean,
    onSend: () -> Unit,
) {
    Surface(color = MaterialTheme.colorScheme.surface, shadowElevation = 6.dp) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(WindowInsets.navigationBars.union(WindowInsets.ime))
                .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = value,
                onValueChange = { if (it.length <= MAX_MESSAGE_LENGTH) onValueChange(it) },
                modifier = Modifier.weight(1f),
                placeholder = { Text(stringResource(R.string.chat_input_placeholder)) },
                shape = RoundedCornerShape(24.dp),
                maxLines = 4,
                keyboardOptions = KeyboardOptions(
                    capitalization = KeyboardCapitalization.Sentences,
                    imeAction = ImeAction.Send,
                ),
                keyboardActions = KeyboardActions(onSend = { if (enabled) onSend() }),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = UabGreen,
                    cursorColor = UabGreen,
                    unfocusedBorderColor = MaterialTheme.colorScheme.outlineVariant,
                ),
            )
            Spacer(Modifier.size(8.dp))
            FilledIconButton(
                onClick = onSend,
                enabled = enabled && value.isNotBlank(),
                modifier = Modifier.size(48.dp),
                colors = IconButtonDefaults.filledIconButtonColors(
                    containerColor = UabGreen,
                    contentColor = Color.White,
                ),
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = stringResource(R.string.chat_send))
            }
        }
    }
}

private const val MAX_MESSAGE_LENGTH = 2000

private fun limitationRes(code: String): Int? = when (code) {
    "historical_only" -> R.string.methodology_limit_1
    "bookings_not_attendance" -> R.string.methodology_limit_2
    "low_data" -> R.string.methodology_limit_6
    "shift_change_hours" -> R.string.methodology_limit_7
    "long_block" -> R.string.activity_long_blocks_note
    "provisional_capacity" -> R.string.chat_limit_provisional_capacity
    "general_hours_only" -> R.string.chat_limit_general_hours_only
    "unvalidated_metric" -> R.string.chat_limit_unvalidated_metric
    "data_unavailable" -> R.string.chat_limit_data_unavailable
    "unverified_figures", "unverified_figures_removed" -> R.string.chat_limit_unverified_figures
    else -> null
}

// --- Parsing of the presented P2 output (backend/app/tools/results.py `present`) ---

private fun JsonObject.str(key: String): String? =
    (get(key) as? JsonPrimitive)?.takeIf { it.isString }?.content

private fun JsonObject.hourRow(): HourAvailability? {
    val hour = get("hour")?.jsonPrimitive?.intOrNull ?: return null
    val capacity = get("capacity")?.jsonPrimitive?.intOrNull ?: return null
    val occupied = get("occupied")?.jsonPrimitive?.intOrNull ?: 0
    fun flag(k: String) = (get(k) as? JsonPrimitive)?.booleanOrNull == true
    return HourAvailability(
        hour = hour,
        occupied = occupied,
        capacity = capacity,
        isClosed = flag("is_closed"),
        shiftChange = flag("shift_change"),
        lowData = flag("low_data"),
        longBlock = flag("long_block"),
        load = get("load")?.jsonPrimitive?.floatOrNull ?: (occupied.toFloat() / capacity.coerceAtLeast(1)),
    )
}

private fun parseAlternatives(data: JsonObject): List<Alternative> =
    runCatching {
        data["alternatives"]?.jsonArray.orEmpty().mapNotNull { element ->
            val o = element.jsonObject
            val kind = o.str("kind")?.let { k -> AlternativeKind.entries.firstOrNull { it.name == k } }
                ?: return@mapNotNull null
            val activityId = o.str("activity_id") ?: return@mapNotNull null
            val weekday = o.str("weekday") ?: return@mapNotNull null
            val row = o.hourRow() ?: return@mapNotNull null
            Alternative(kind, activityId, weekday, row, o["reduction_pp"]?.jsonPrimitive?.intOrNull ?: 0)
        }
    }.getOrDefault(emptyList())

private fun parseSlots(data: JsonObject): List<Pair<String, HourAvailability>> =
    runCatching {
        data["slots"]?.jsonArray.orEmpty().mapNotNull { element ->
            val o = element.jsonObject
            val weekday = o.str("weekday") ?: return@mapNotNull null
            val row = o.hourRow() ?: return@mapNotNull null
            weekday to row
        }
    }.getOrDefault(emptyList())
