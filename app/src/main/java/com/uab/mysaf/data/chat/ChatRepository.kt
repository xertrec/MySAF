package com.uab.mysaf.data.chat

/**
 * Runs one user message to completion: the backend may ask for several rounds of tool calls,
 * which are executed locally on the Room database before the final reply arrives.
 */
class ChatRepository(
    private val client: SafiaClient,
    private val executor: SafiaToolExecutor,
) {

    suspend fun send(
        message: String,
        conversationId: String?,
        locale: String,
        history: List<HistoryMessage> = emptyList(),
    ): ChatResponse {
        var response = client.chat(ChatRequest(message, conversationId, locale, history.takeLast(MAX_HISTORY)))
        var rounds = 0
        while (response.isToolCalls) {
            val turnId = response.turnId
                ?: throw SafiaException("BAD_RESPONSE", "Missing turn id", retryable = true)
            if (++rounds > MAX_ROUNDS) {
                throw SafiaException("TOO_MANY_ROUNDS", "Too many tool rounds", retryable = true)
            }
            val results = response.toolCalls.map { executor.execute(it) } // never throws
            response = client.toolResults(turnId, ToolResultsRequest(results))
        }
        return response
    }

    companion object {
        const val MAX_HISTORY = 10

        /** The backend caps rounds itself; this only guards against a misbehaving server. */
        const val MAX_ROUNDS = 6
    }
}
