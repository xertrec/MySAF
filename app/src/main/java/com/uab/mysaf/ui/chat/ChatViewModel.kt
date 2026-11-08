package com.uab.mysaf.ui.chat

import android.content.Context
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uab.mysaf.R
import com.uab.mysaf.data.AvailabilityRepository
import com.uab.mysaf.data.chat.ChatRepository
import com.uab.mysaf.data.chat.ChatResponse
import com.uab.mysaf.data.chat.HistoryMessage
import com.uab.mysaf.data.chat.RecommendationDto
import com.uab.mysaf.data.chat.SafiaClient
import com.uab.mysaf.data.chat.SafiaException
import com.uab.mysaf.data.chat.SafiaToolExecutor
import com.uab.mysaf.data.db.MySafDatabase
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatMessageUi(
    val id: Long,
    val fromUser: Boolean,
    val text: String,
    val sources: List<String> = emptyList(),
    val limitations: List<String> = emptyList(),
    val recommendation: RecommendationDto? = null,
)

data class ChatUiState(
    val messages: List<ChatMessageUi> = emptyList(),
    val isSending: Boolean = false,
    val error: SafiaException? = null,
    val lastFailedText: String? = null,
)

class ChatViewModel(
    private val repo: ChatRepository,
    private val state: SavedStateHandle,
) : ViewModel() {

    private val _ui = MutableStateFlow(ChatUiState())
    val ui: StateFlow<ChatUiState> = _ui.asStateFlow()

    private var nextId = 0L

    /** null means a new conversation; survives process death. */
    private var conversationId: String?
        get() = state[KEY_CONVERSATION_ID]
        set(value) {
            state[KEY_CONVERSATION_ID] = value
        }

    fun send(text: String, locale: String) {
        val message = text.trim()
        if (message.isEmpty() || _ui.value.isSending) return
        val history = _ui.value.messages.toHistory()
        _ui.update {
            it.copy(
                messages = it.messages + ChatMessageUi(nextId++, fromUser = true, text = message),
                isSending = true,
                error = null,
                lastFailedText = null,
            )
        }
        launchSend(message, locale, history)
    }

    /** Resends the message that failed; it is already shown in the list. */
    fun retry(locale: String) {
        val message = _ui.value.lastFailedText ?: return
        if (_ui.value.isSending) return
        val history = _ui.value.messages.dropLast(1).toHistory()
        _ui.update { it.copy(isSending = true, error = null) }
        launchSend(message, locale, history)
    }

    /**
     * Replaces one of the user's own messages with [text] and resends it: everything from that
     * message onwards is discarded and a fresh server conversation is seeded with the earlier history.
     */
    fun editAndResend(messageId: Long, text: String, locale: String) {
        val message = text.trim()
        if (message.isEmpty() || _ui.value.isSending) return
        val index = _ui.value.messages.indexOfFirst { it.id == messageId && it.fromUser }
        if (index < 0) return send(message, locale)
        val kept = _ui.value.messages.take(index)
        conversationId = null // the server copy still holds the old turns
        _ui.update {
            it.copy(
                messages = kept + ChatMessageUi(nextId++, fromUser = true, text = message),
                isSending = true,
                error = null,
                lastFailedText = null,
            )
        }
        launchSend(message, locale, kept.toHistory())
    }

    fun newConversation() {
        if (_ui.value.isSending) return
        conversationId = null
        _ui.value = ChatUiState()
    }

    private fun launchSend(message: String, locale: String, history: List<HistoryMessage>) {
        viewModelScope.launch {
            try {
                val response = sendWithRetry(message, locale, history)
                conversationId = response.conversationId
                _ui.update {
                    it.copy(
                        isSending = false,
                        messages = it.messages + ChatMessageUi(
                            id = nextId++,
                            fromUser = false,
                            text = response.reply.orEmpty(),
                            sources = response.sources.map { s -> s.label }.distinct(),
                            limitations = response.limitations.distinct(),
                            recommendation = response.recommendation,
                        ),
                    )
                }
            } catch (e: SafiaException) {
                _ui.update { it.copy(isSending = false, error = e, lastFailedText = message) }
            }
        }
    }

    private suspend fun sendWithRetry(
        message: String,
        locale: String,
        history: List<HistoryMessage>,
    ): ChatResponse = try {
        repo.send(message, conversationId, locale, history)
    } catch (e: SafiaException) {
        // The pending turn was lost (server restart or timeout): resend once.
        if (e.code == SafiaException.TURN_EXPIRED || e.code == SafiaException.TURN_NOT_FOUND) {
            repo.send(message, conversationId, locale, history)
        } else {
            throw e
        }
    }

    private fun List<ChatMessageUi>.toHistory(): List<HistoryMessage> =
        filter { it.text.isNotBlank() }
            .takeLast(ChatRepository.MAX_HISTORY)
            .map { HistoryMessage(if (it.fromUser) "user" else "assistant", it.text.take(4000)) }

    companion object {
        private const val KEY_CONVERSATION_ID = "conversation_id"

        fun repository(context: Context): ChatRepository {
            val app = context.applicationContext
            val dao = MySafDatabase.getInstance(app).availabilityDao()
            return ChatRepository(
                client = SafiaClient(app.getString(R.string.safia_base_url)),
                executor = SafiaToolExecutor(AvailabilityRepository(dao), dao),
            )
        }
    }
}
