package com.uab.mysaf.data.chat

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonObject

/*
 * Wire format of the SAFIA backend (backend/app/api/schemas.py).
 * Contract: docs/safia/ANDROID_INTEGRATION.md.
 */

@Serializable
data class ChatRequest(
    val message: String,
    @SerialName("conversation_id") val conversationId: String? = null,
    val locale: String? = null,
    val history: List<HistoryMessage> = emptyList(),
)

@Serializable
data class HistoryMessage(val role: String, val text: String)

@Serializable
data class ChatResponse(
    /** "tool_calls" or "final". */
    val status: String,
    @SerialName("conversation_id") val conversationId: String,
    // status == "tool_calls"
    @SerialName("turn_id") val turnId: String? = null,
    @SerialName("expires_in_s") val expiresInS: Int? = null,
    val round: Int? = null,
    @SerialName("tool_calls") val toolCalls: List<ToolCall> = emptyList(),
    // status == "final"
    val reply: String? = null,
    val language: String? = null,
    val sources: List<Source> = emptyList(),
    val limitations: List<String> = emptyList(),
    val recommendation: RecommendationDto? = null,
    @SerialName("needs_clarification") val needsClarification: Boolean = false,
) {
    val isToolCalls: Boolean get() = status == STATUS_TOOL_CALLS

    companion object {
        const val STATUS_TOOL_CALLS = "tool_calls"
    }
}

@Serializable
data class ToolCall(
    @SerialName("call_id") val callId: String,
    val name: String,
    val arguments: JsonObject = JsonObject(emptyMap()),
)

@Serializable
data class Source(val tool: String, val table: String, val label: String)

@Serializable
data class RecommendationDto(val type: String, val data: JsonObject)

@Serializable
data class ToolResultsRequest(val results: List<ToolResult>)

@Serializable
data class ToolResult(
    @SerialName("call_id") val callId: String,
    val ok: Boolean,
    val output: JsonObject? = null,
    val error: String? = null,
)

@Serializable
data class ErrorEnvelope(val error: ErrorBody)

@Serializable
data class ErrorBody(val code: String, val message: String, val retryable: Boolean = false)

class SafiaException(
    val code: String,
    override val message: String,
    val retryable: Boolean,
) : Exception(message) {
    companion object {
        const val NETWORK = "NETWORK"
        const val TURN_EXPIRED = "TURN_EXPIRED"
        const val TURN_NOT_FOUND = "TURN_NOT_FOUND"
        const val RATE_LIMITED = "RATE_LIMITED"
        const val LLM_NOT_CONFIGURED = "LLM_NOT_CONFIGURED"
    }
}
