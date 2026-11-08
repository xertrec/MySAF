# SAFIA — Android integration contract

For the Android developer. The backend is implemented and tested against this contract; the app can be
built against it without backend changes. Machine-readable tool contract:
[`contracts/tools.schema.json`](../../contracts/tools.schema.json) (also served at `GET /v1/tools`).

## 1. Overview

```
ChatScreen ──► ChatViewModel ──► ChatRepository ──► SafiaApi (Retrofit) ──► FastAPI ──► Ornith
                                      │
                                      └──► SafiaToolExecutor ──► AvailabilityRepository / AvailabilityDao (Room)
                                                                  └──► P2: findAlternatives, quieterHour
```

One user message can take several HTTP calls:

1. `POST /v1/chat` with the message.
2. If the response has `"status": "tool_calls"`, run every call locally with `SafiaToolExecutor`.
3. `POST /v1/chat/{turn_id}/tool-results` with one result per `call_id`.
4. Repeat 2–3 while the status is `tool_calls` (at most 3 rounds), then show the `"final"` reply.

The ViewModel shows a single loading state for the whole loop. No API key is ever on the device.

## 2. Endpoints

Base URL: `http://10.0.2.2:8000/` (emulator) or `http://<PC LAN IP>:8000/` (phone on the same Wi-Fi,
server started with `--host 0.0.0.0`). Plain HTTP for local testing needs cleartext enabled in a
**debug-only** network security config.

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/v1/chat` | `ChatRequest` | `ChatResponse` (`tool_calls` or `final`) |
| `POST` | `/v1/chat/{turn_id}/tool-results` | `ToolResultsRequest` | `ChatResponse` |
| `GET` | `/health` | – | `{"status":"ok","model":"ornith","llm_configured":true}` |
| `GET` | `/v1/tools` | – | Tool schemas |

### 2.1 `POST /v1/chat`

```json
{
  "message": "I els caps de setmana?",
  "conversation_id": "conv_0d9bc722303a472a9db44469817822d2",
  "locale": "ca"
}
```

| Field | Required | Notes |
|---|---|---|
| `message` | yes | 1–2000 characters. |
| `conversation_id` | no | Omit on the first message. Afterwards always send the id from the last response. Pattern `^[A-Za-z0-9_-]{8,64}$`. |
| `locale` | no | `ca`, `es` or `en` (the app UI language). Only a tie-breaker; SAFIA answers in the user's language. |
| `history` | no | `[{"role":"user"\|"assistant","text":"…"}]`, max 40. Only used when the server no longer knows the conversation (e.g. after a restart). Sending the last few messages every time is harmless. |
| `context` | no | Echo of the last returned `context`; same rule as `history`. |

### 2.2 Response: tool calls needed

```json
{
  "status": "tool_calls",
  "conversation_id": "conv_0d9bc722303a472a9db44469817822d2",
  "turn_id": "turn_00738363f18d4b53a719d60f5aca3e8e",
  "expires_in_s": 300,
  "round": 1,
  "tool_calls": [
    {"call_id": "call_a1", "name": "find_quieter_slots",
     "arguments": {"activity_id": "sala_fitness", "weekdays": ["ds", "dg"], "period": "lectiu", "limit": 3}}
  ]
}
```

- Arguments are already validated by the backend (known tool, enum values, ranges). Defaults are filled in
  (`period`, `limit`). Optional arguments may be absent.
- There can be several calls; answer **all** of them in one request. Order doesn't matter, ids do.
- `turn_id` stays the same across rounds of one message.

### 2.3 `POST /v1/chat/{turn_id}/tool-results`

```json
{
  "results": [
    {"call_id": "call_a1", "ok": true, "output": { "...": "see section 4" }},
    {"call_id": "call_a2", "ok": false, "error": "DB_UNAVAILABLE"}
  ]
}
```

Use `ok: false` (with a short `error` code) when the local call throws. SAFIA then says it can't verify
that data. Don't omit the call.

### 2.4 Response: final answer

```json
{
  "status": "final",
  "conversation_id": "conv_0d9bc722303a472a9db44469817822d2",
  "reply": "Els caps de setmana, les franges més tranquil·les són dissabte a les 14:00 (18 %) i diumenge a les 09:00 (27 %).",
  "language": "ca",
  "sources": [{"tool": "find_quieter_slots", "table": "hourly_availability",
               "label": "Motor de recomanacions (P2) sobre l'ocupació històrica"}],
  "limitations": ["historical_only", "bookings_not_attendance"],
  "recommendation": {"type": "quieter_slots", "data": { "...": "presented P2 output" }},
  "needs_clarification": false,
  "context": {"activity_id": "sala_fitness", "weekdays": ["ds", "dg"], "hour": null, "period": "lectiu"}
}
```

- `reply`: show as the assistant bubble.
- `sources`: optional "Font: …" line under the bubble (labels are in Catalan).
- `limitations`: codes for optional chips/notes. Possible values: `historical_only`, `bookings_not_attendance`,
  `provisional_capacity`, `general_hours_only`, `unvalidated_metric`, `low_data`, `long_block`,
  `shift_change_hours`, `data_unavailable`, `unverified_figures`, `unverified_figures_removed`.
  Map them to `strings.xml` texts (most already exist as `methodology_limit_*`).
- `recommendation`: present when P2 ran. `type = "alternatives"` (from `recommend_alternatives`) can be
  rendered with the existing `RecommendationCard`; `data.alternatives[]` has `kind`, `activity_id`,
  `weekday`, `hour`, `load_pct`, `reduction_pp`.
- `needs_clarification`: SAFIA asked a question; keep the input focused.

### 2.5 Errors

Every non-2xx response has the same envelope:

```json
{"error": {"code": "LLM_TIMEOUT", "message": "The language model took too long to answer.",
           "retryable": true, "details": {}}}
```

| HTTP | `code` | App behaviour |
|---|---|---|
| 422 | `BAD_REQUEST` | Bug in the request; log `details.errors`. |
| 422 | `INVALID_TOOL_RESULT` | Tool results don't match: `details` lists `missing` / `unknown` / `duplicated` call ids or invalid `calls`. The turn stays open; fix and resend. This is an executor bug. |
| 404 | `TURN_NOT_FOUND` | Turn unknown (server restarted or a newer message replaced it). Resend the user message. |
| 410 | `TURN_EXPIRED` | Results came after `expires_in_s`. Resend the user message. |
| 429 | `RATE_LIMITED` | Show "try again shortly"; retry button. |
| 502 | `LLM_UNAVAILABLE`, `LLM_AUTH` | Show a generic error; retry button for `retryable`. |
| 503 | `LLM_NOT_CONFIGURED` | Backend has no key (setup problem). |
| 504 | `LLM_TIMEOUT` | Retryable. |
| 500 | `INTERNAL` | Retryable. |

Sending a new message while a turn is waiting for tool results cancels that turn on the server.

## 3. Tools Android must execute

All map onto code that already exists, except where marked **NEW**. Use `period == "all"` →
`allPeriod = true`.

| Tool | Arguments | Kotlin implementation |
|---|---|---|
| `list_activities` | – | `dao.activities()` |
| `get_opening_hours` | `weekdays?` | `dao.openingHours()`, filtered to `weekdays` if present |
| `get_facility_info` | `activity_id` | `dao.activity(id)` (`null` → `"activity": null`) |
| `get_hourly_occupancy` | `activity_id`, `weekdays`, `hour_from?`, `hour_to?`, `period` | `repository.dayAvailability(id, wd, allPeriod)` per weekday, filtered by hour |
| `find_quieter_slots` (P2) | `activity_id`, `weekdays`, `period`, `limit` | Per weekday: `dayAvailability(...)`, then **NEW** helper `quietestHours(rows, limit)` = `rows.filter { it.isUsable }.sortedBy { it.load }.take(limit)`; put it next to `quieterHour` in `Availability.kt` so it stays part of P2 |
| `recommend_alternatives` (P2) | `activity_id`, `weekday`, `hour`, `period` | `repository.recommendations(id, weekday, hour, allPeriod)` plus **NEW** `no_result_reason` (below) |
| `get_dataset_info` | – | `dao.datasetInfo(key)` for each known key, or **NEW** `@Query("SELECT * FROM dataset_info") suspend fun allDatasetInfo(): List<DatasetInfoEntity>` |

`no_result_reason` for `recommend_alternatives`:

| Condition | Value |
|---|---|
| `dao.activity(id) == null` | `"unknown_activity"` |
| `requested == null` and the row at `hour` exists with `isClosed` | `"closed"` |
| `requested == null` otherwise | `"no_data"` |
| `isAlreadyQuiet` | `"already_quiet"` |
| `alternatives.isEmpty()` | `"no_alternative_10pp"` |
| otherwise | `null` |

Unknown tool name (shouldn't happen) → `ok=false, error="UNKNOWN_TOOL"`. Any exception →
`ok=false, error="DB_UNAVAILABLE"`.

## 4. Output JSON (exact field names)

The common hour row is `HourAvailability` plus `occupancyLabel` and `isUsable`:

```json
{"hour": 18, "occupied": 5, "capacity": 5, "load": 0.9139, "is_closed": false, "shift_change": false,
 "low_data": false, "long_block": true, "usable": true, "label": "FULL"}
```

| Tool | `output` |
|---|---|
| `list_activities` | `{"activities": [{"activity_id": "tennis", "is_person_count": false, "capacity": 5, "resource_ids": ["TENIS_PISTA_1", "…"]}]}` |
| `get_opening_hours` | `{"opening_hours": [{"weekday": "ds", "open_min": 480, "close_min": 1200}]}` |
| `get_facility_info` | `{"activity": {"activity_id": "tennis", "is_person_count": false, "capacity": 5, "resource_ids": ["…"]}}` or `{"activity": null}` |
| `get_hourly_occupancy` | `{"activity_id": "piscina_25m", "period": "lectiu", "days": [{"weekday": "dl", "hours": [HourRow, …]}]}` |
| `find_quieter_slots` | `{"activity_id": "sala_fitness", "period": "lectiu", "slots": [{"weekday": "ds", "row": HourRow}, …]}` |
| `recommend_alternatives` | `{"activity_id": "tennis", "weekday": "dl", "hour": 18, "period": "lectiu", "requested": HourRow or null, "is_already_quiet": false, "alternatives": [{"kind": "SAME_DAY", "activity_id": "tennis", "weekday": "dl", "reduction_pp": 86, "row": HourRow}], "no_result_reason": null}` |
| `get_dataset_info` | `{"entries": {"date_min": "2026-04-01", "date_max": "2026-10-31", "active_days": "193", "…": "…"}}` |

Real examples for every tool: [`contracts/fixtures/device_tool_outputs.json`](../../contracts/fixtures/device_tool_outputs.json).
Unknown extra fields are ignored by the backend; missing or mistyped required fields cause a 422.

## 5. Kotlin code

### 5.1 Dependencies and permission

```kotlin
// app/build.gradle.kts
implementation("com.squareup.retrofit2:retrofit:2.11.0")
implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
implementation("com.squareup.okhttp3:okhttp:4.12.0")
implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.11.0")

android { buildFeatures { buildConfig = true }
  defaultConfig { buildConfigField("String", "SAFIA_BASE_URL", "\"http://10.0.2.2:8000/\"") } }
```

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET" />
```

### 5.2 DTOs (`data/chat/SafiaDtos.kt`)

```kotlin
@Serializable
data class ChatRequest(
    val message: String,
    @SerialName("conversation_id") val conversationId: String? = null,
    val locale: String? = null,
    val history: List<HistoryMessage> = emptyList(),
)

@Serializable data class HistoryMessage(val role: String, val text: String)

@Serializable
data class ChatResponse(
    val status: String,                                   // "tool_calls" | "final"
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
)

@Serializable data class ToolCall(@SerialName("call_id") val callId: String, val name: String, val arguments: JsonObject)
@Serializable data class Source(val tool: String, val table: String, val label: String)
@Serializable data class RecommendationDto(val type: String, val data: JsonObject)

@Serializable data class ToolResultsRequest(val results: List<ToolResult>)
@Serializable
data class ToolResult(
    @SerialName("call_id") val callId: String,
    val ok: Boolean,
    val output: JsonObject? = null,
    val error: String? = null,
)

@Serializable data class ErrorEnvelope(val error: ErrorBody)
@Serializable data class ErrorBody(val code: String, val message: String, val retryable: Boolean = false)

class SafiaException(val code: String, override val message: String, val retryable: Boolean) : Exception(message)
```

### 5.3 Retrofit (`data/chat/SafiaApi.kt`)

```kotlin
interface SafiaApi {
    @POST("v1/chat")
    suspend fun chat(@Body body: ChatRequest): Response<ChatResponse>

    @POST("v1/chat/{turnId}/tool-results")
    suspend fun toolResults(@Path("turnId") turnId: String, @Body body: ToolResultsRequest): Response<ChatResponse>

    companion object {
        val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

        fun create(baseUrl: String = BuildConfig.SAFIA_BASE_URL): SafiaApi = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(90, TimeUnit.SECONDS)   // the LLM can take a while
                .build())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(SafiaApi::class.java)
    }
}
```

### 5.4 Repository loop (`data/chat/ChatRepository.kt`)

```kotlin
class ChatRepository(private val api: SafiaApi, private val executor: SafiaToolExecutor) {

    suspend fun send(message: String, conversationId: String?, locale: String,
                     history: List<HistoryMessage> = emptyList()): ChatResponse {
        var resp = call { api.chat(ChatRequest(message, conversationId, locale, history.takeLast(10))) }
        while (resp.status == "tool_calls") {
            val results = resp.toolCalls.map { executor.execute(it) }   // never throws
            resp = call { api.toolResults(resp.turnId!!, ToolResultsRequest(results)) }
        }
        return resp
    }

    private suspend fun call(block: suspend () -> Response<ChatResponse>): ChatResponse {
        val r = try { block() } catch (e: IOException) {
            throw SafiaException("NETWORK", "No connection to SAFIA", retryable = true)
        }
        r.body()?.takeIf { r.isSuccessful }?.let { return it }
        val err = r.errorBody()?.string()?.let {
            runCatching { SafiaApi.json.decodeFromString<ErrorEnvelope>(it).error }.getOrNull()
        }
        throw SafiaException(err?.code ?: "HTTP_${r.code()}", err?.message ?: "Error ${r.code()}", err?.retryable ?: true)
    }
}
```

On `TURN_EXPIRED` / `TURN_NOT_FOUND`, the ViewModel can call `send` once more with the same message.

### 5.5 Tool executor (`data/chat/SafiaToolExecutor.kt`)

```kotlin
class SafiaToolExecutor(private val repo: AvailabilityRepository, private val dao: AvailabilityDao) {

    suspend fun execute(call: ToolCall): ToolResult {
      return try {
        val a = call.arguments
        val output: JsonObject = when (call.name) {
            "list_activities" -> buildJsonObject { putJsonArray("activities") { dao.activities().forEach { add(it.toJson()) } } }
            "get_facility_info" -> buildJsonObject { put("activity", dao.activity(a.str("activity_id"))?.toJson() ?: JsonNull) }
            "get_opening_hours" -> {
                val days = a.strList("weekdays")
                buildJsonObject { putJsonArray("opening_hours") {
                    dao.openingHours().filter { days == null || it.weekday in days }.forEach {
                        add(buildJsonObject { put("weekday", it.weekday); put("open_min", it.openMin); put("close_min", it.closeMin) })
                    } } }
            }
            "get_hourly_occupancy" -> {
                val id = a.str("activity_id"); val all = a.period() == "all"
                val from = a.intOrNull("hour_from") ?: 0; val to = a.intOrNull("hour_to") ?: 23
                buildJsonObject {
                    put("activity_id", id); put("period", a.period())
                    putJsonArray("days") { a.strList("weekdays")!!.forEach { wd ->
                        add(buildJsonObject { put("weekday", wd); putJsonArray("hours") {
                            repo.dayAvailability(id, wd, all).filter { it.hour in from..to }.forEach { add(it.toJson()) } } })
                    } }
                }
            }
            "find_quieter_slots" -> {
                val id = a.str("activity_id"); val all = a.period() == "all"; val limit = a.intOrNull("limit") ?: 3
                buildJsonObject {
                    put("activity_id", id); put("period", a.period())
                    putJsonArray("slots") { a.strList("weekdays")!!.forEach { wd ->
                        quietestHours(repo.dayAvailability(id, wd, all), limit).forEach { row ->   // NEW P2 helper
                            add(buildJsonObject { put("weekday", wd); put("row", row.toJson()) }) } } }
                }
            }
            "recommend_alternatives" -> {
                val id = a.str("activity_id"); val wd = a.str("weekday"); val hour = a.int("hour"); val all = a.period() == "all"
                val rec = repo.recommendations(id, wd, hour, all)
                val reason = when {
                    dao.activity(id) == null -> "unknown_activity"
                    rec.requested == null ->
                        if (repo.dayAvailability(id, wd, all).any { it.hour == hour && it.isClosed }) "closed" else "no_data"
                    rec.isAlreadyQuiet -> "already_quiet"
                    rec.alternatives.isEmpty() -> "no_alternative_10pp"
                    else -> null
                }
                buildJsonObject {
                    put("activity_id", id); put("weekday", wd); put("hour", hour); put("period", a.period())
                    put("requested", rec.requested?.toJson() ?: JsonNull)
                    put("is_already_quiet", rec.isAlreadyQuiet)
                    putJsonArray("alternatives") { rec.alternatives.forEach { alt -> add(buildJsonObject {
                        put("kind", alt.kind.name); put("activity_id", alt.activityId); put("weekday", alt.weekday)
                        put("reduction_pp", alt.reductionPp); put("row", alt.row.toJson()) }) } }
                    put("no_result_reason", reason)   // String? -> JsonNull when null
                }
            }
            "get_dataset_info" -> buildJsonObject { putJsonObject("entries") {
                DATASET_KEYS.forEach { k -> dao.datasetInfo(k)?.let { put(k, it) } } } }
            else -> return ToolResult(call.callId, ok = false, error = "UNKNOWN_TOOL")
        }
        ToolResult(call.callId, ok = true, output = output)
    } catch (e: CancellationException) { throw e
    } catch (e: Exception) {
        Log.e("SAFIA", "Tool ${call.name} failed", e)
        ToolResult(call.callId, ok = false, error = "DB_UNAVAILABLE")
      }
    }

    companion object {
        val DATASET_KEYS = listOf("date_min", "date_max", "active_days", "booking_scope",
                                  "clean_rule_version", "closed_day_max_rows", "db_version", "source_file")
    }
}

private fun HourAvailability.toJson() = buildJsonObject {
    put("hour", hour); put("occupied", occupied); put("capacity", capacity); put("load", load)
    put("is_closed", isClosed); put("shift_change", shiftChange); put("low_data", lowData); put("long_block", longBlock)
    put("usable", isUsable); put("label", occupancyLabel(this@toJson).name)
}
private fun ActivityEntity.toJson() = buildJsonObject {
    put("activity_id", id); put("is_person_count", isPersonCount); put("capacity", capacity)
    putJsonArray("resource_ids") { resourceIds.split(",").filter { it.isNotBlank() }.forEach { add(it) } }
}
private fun JsonObject.str(k: String) = getValue(k).jsonPrimitive.content
private fun JsonObject.int(k: String) = getValue(k).jsonPrimitive.int
private fun JsonObject.intOrNull(k: String) = get(k)?.jsonPrimitive?.intOrNull
private fun JsonObject.strList(k: String) = get(k)?.jsonArray?.map { it.jsonPrimitive.content }
private fun JsonObject.period() = get("period")?.jsonPrimitive?.content ?: "lectiu"
```

`AvailabilityRepository` currently has no `dao` getter; pass the DAO in alongside it
(`MySafDatabase.getInstance(context).availabilityDao()`).

### 5.6 ViewModel (`ui/chat/ChatViewModel.kt`)

Requirements:

- Keep `conversationId` in the ViewModel (and in `SavedStateHandle` to survive process death). `null`
  means a new chat; set it from every response.
- One `isSending` flag covering the whole request → tools → results loop. Disable the send button while
  it's on.
- Append the user message immediately; append the assistant message only on `final`.
- On `SafiaException` with `retryable`, show the error with a retry action that resends the same text.
  On `TURN_EXPIRED` / `TURN_NOT_FOUND`, retry once automatically.
- Pass `locale` from the app's current locale (`ca` or `en`).
- Optional: pass the last ~10 messages as `history` so a backend restart doesn't lose context.

```kotlin
data class ChatMessageUi(val id: Long, val fromUser: Boolean, val text: String,
                         val sources: List<String> = emptyList(), val limitations: List<String> = emptyList(),
                         val recommendation: RecommendationDto? = null)

data class ChatUiState(val messages: List<ChatMessageUi> = emptyList(), val isSending: Boolean = false,
                       val error: SafiaException? = null, val lastFailedText: String? = null)

class ChatViewModel(private val repo: ChatRepository, private val state: SavedStateHandle) : ViewModel() {
    private val _ui = MutableStateFlow(ChatUiState())
    val ui: StateFlow<ChatUiState> = _ui.asStateFlow()
    private var conversationId: String?
        get() = state["cid"]
        set(value) { state["cid"] = value }

    fun send(text: String, locale: String) {
        if (text.isBlank() || _ui.value.isSending) return
        _ui.update { it.copy(messages = it.messages + ChatMessageUi(System.nanoTime(), true, text),
                             isSending = true, error = null) }
        viewModelScope.launch {
            try {
                val r = sendWithRetry(text, locale)
                conversationId = r.conversationId
                _ui.update { it.copy(isSending = false, messages = it.messages + ChatMessageUi(
                    System.nanoTime(), false, r.reply.orEmpty(), r.sources.map { s -> s.label },
                    r.limitations, r.recommendation)) }
            } catch (e: SafiaException) {
                _ui.update { it.copy(isSending = false, error = e, lastFailedText = text) }
            }
        }
    }

    private suspend fun sendWithRetry(text: String, locale: String): ChatResponse = try {
        repo.send(text, conversationId, locale)
    } catch (e: SafiaException) {
        if (e.code == "TURN_EXPIRED" || e.code == "TURN_NOT_FOUND") repo.send(text, conversationId, locale) else throw e
    }

    fun newConversation() { conversationId = null; _ui.value = ChatUiState() }
}
```

Navigation: add `@Serializable data object ScreenChat` and a `composable<ScreenChat>` entry in
`NavGraph.kt`, plus an entry point on `HomeScreen`. Existing screens don't change.

## 6. Tests on the Android side

- `SafiaToolExecutorTest` (unit, fake DAO): each tool returns the field names above; unknown tool →
  `ok=false`; exceptions → `ok=false`.
- Instrumented test against the prepackaged DB (like `PrepackagedDatabaseTest`): run each tool with the
  arguments used in `contracts/fixtures/device_tool_outputs.json` and compare. Writing the outputs to that
  file replaces the hand-derived P2 fixtures with real Kotlin output, and the backend tests then replay it.
- Manual: start the backend, run the app in the emulator, ask "A quina hora tanca el SAF els dissabtes?".
