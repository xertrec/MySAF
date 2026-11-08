package com.uab.mysaf.data.chat

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/** Minimal HTTP client for the SAFIA backend. No API key ever lives on the device. */
open class SafiaClient(baseUrl: String) {

    private val base = baseUrl.trimEnd('/') + "/"

    open suspend fun chat(body: ChatRequest): ChatResponse =
        post("v1/chat", json.encodeToString(body))

    open suspend fun toolResults(turnId: String, body: ToolResultsRequest): ChatResponse =
        post("v1/chat/${URLEncoder.encode(turnId, "UTF-8")}/tool-results", json.encodeToString(body))

    private suspend fun post(path: String, payload: String): ChatResponse = withContext(Dispatchers.IO) {
        val connection = try {
            (URL(base + path).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS // the LLM can take a while
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                setRequestProperty("Accept", "application/json")
            }
        } catch (e: IOException) {
            throw networkError()
        }
        try {
            connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code in 200..299) {
                try {
                    json.decodeFromString<ChatResponse>(text)
                } catch (e: SerializationException) {
                    throw SafiaException("BAD_RESPONSE", "Unexpected response from SAFIA", retryable = true)
                } catch (e: IllegalArgumentException) {
                    throw SafiaException("BAD_RESPONSE", "Unexpected response from SAFIA", retryable = true)
                }
            } else {
                val err = runCatching { json.decodeFromString<ErrorEnvelope>(text).error }.getOrNull()
                throw SafiaException(err?.code ?: "HTTP_$code", err?.message ?: "Error $code", err?.retryable ?: true)
            }
        } catch (e: IOException) {
            throw networkError()
        } finally {
            connection.disconnect()
        }
    }

    private fun networkError() =
        SafiaException(SafiaException.NETWORK, "No connection to SAFIA", retryable = true)

    companion object {
        const val CONNECT_TIMEOUT_MS = 10_000
        const val READ_TIMEOUT_MS = 90_000

        val json = Json {
            ignoreUnknownKeys = true
            explicitNulls = false
            encodeDefaults = true
        }
    }
}
