package com.uab.mysaf.data.chat

import android.util.Log
import com.uab.mysaf.data.AvailabilityRepository
import com.uab.mysaf.data.HourAvailability
import com.uab.mysaf.data.isUsable
import com.uab.mysaf.data.occupancyLabel
import com.uab.mysaf.data.quietestHours
import com.uab.mysaf.data.db.ActivityEntity
import com.uab.mysaf.data.db.AvailabilityDao
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import kotlin.coroutines.cancellation.CancellationException

/**
 * Runs the tools the SAFIA backend asks for against the local Room database and the P2 engine.
 * Output field names follow docs/safia/ANDROID_INTEGRATION.md §4 exactly. Never throws
 * (except cancellation): failures become `ok = false` results.
 */
class SafiaToolExecutor(
    private val repo: AvailabilityRepository,
    private val dao: AvailabilityDao,
) {

    suspend fun execute(call: ToolCall): ToolResult {
        return try {
            val a = call.arguments
            val output: JsonObject = when (call.name) {
                "list_activities" -> {
                    val rows = dao.activities()
                    buildJsonObject { putJsonArray("activities") { rows.forEach { add(it.toJson()) } } }
                }

                "get_facility_info" -> {
                    val activity = dao.activity(a.str("activity_id"))
                    buildJsonObject { put("activity", activity?.toJson() ?: JsonNull) }
                }

                "get_opening_hours" -> {
                    val days = a.strList("weekdays")
                    val rows = dao.openingHours().filter { days == null || it.weekday in days }
                    buildJsonObject {
                        putJsonArray("opening_hours") {
                            rows.forEach {
                                add(buildJsonObject {
                                    put("weekday", it.weekday)
                                    put("open_min", it.openMin)
                                    put("close_min", it.closeMin)
                                })
                            }
                        }
                    }
                }

                "get_hourly_occupancy" -> {
                    val id = a.str("activity_id")
                    val period = a.period()
                    val from = a.intOrNull("hour_from") ?: 0
                    val to = a.intOrNull("hour_to") ?: 23
                    val days = a.strList("weekdays").orEmpty().map { wd ->
                        wd to repo.dayAvailability(id, wd, period == ALL).filter { it.hour in from..to }
                    }
                    buildJsonObject {
                        put("activity_id", id)
                        put("period", period)
                        putJsonArray("days") {
                            days.forEach { (wd, rows) ->
                                add(buildJsonObject {
                                    put("weekday", wd)
                                    putJsonArray("hours") { rows.forEach { add(it.toJson()) } }
                                })
                            }
                        }
                    }
                }

                "find_quieter_slots" -> {
                    val id = a.str("activity_id")
                    val period = a.period()
                    val limit = a.intOrNull("limit") ?: 3
                    val slots = a.strList("weekdays").orEmpty().flatMap { wd ->
                        quietestHours(repo.dayAvailability(id, wd, period == ALL), limit).map { wd to it }
                    }
                    buildJsonObject {
                        put("activity_id", id)
                        put("period", period)
                        putJsonArray("slots") {
                            slots.forEach { (wd, row) ->
                                add(buildJsonObject {
                                    put("weekday", wd)
                                    put("row", row.toJson())
                                })
                            }
                        }
                    }
                }

                "recommend_alternatives" -> {
                    val id = a.str("activity_id")
                    val wd = a.str("weekday")
                    val hour = a.int("hour")
                    val period = a.period()
                    val all = period == ALL
                    val rec = repo.recommendations(id, wd, hour, all)
                    val reason = when {
                        dao.activity(id) == null -> "unknown_activity"
                        rec.requested == null ->
                            if (repo.dayAvailability(id, wd, all).any { it.hour == hour && it.isClosed }) {
                                "closed"
                            } else {
                                "no_data"
                            }
                        rec.isAlreadyQuiet -> "already_quiet"
                        rec.alternatives.isEmpty() -> "no_alternative_10pp"
                        else -> null
                    }
                    buildJsonObject {
                        put("activity_id", id)
                        put("weekday", wd)
                        put("hour", hour)
                        put("period", period)
                        put("requested", rec.requested?.toJson() ?: JsonNull)
                        put("is_already_quiet", rec.isAlreadyQuiet)
                        putJsonArray("alternatives") {
                            rec.alternatives.forEach { alt ->
                                add(buildJsonObject {
                                    put("kind", alt.kind.name)
                                    put("activity_id", alt.activityId)
                                    put("weekday", alt.weekday)
                                    put("reduction_pp", alt.reductionPp)
                                    put("row", alt.row.toJson())
                                })
                            }
                        }
                        put("no_result_reason", reason)
                    }
                }

                "get_dataset_info" -> {
                    val entries = DATASET_KEYS.mapNotNull { k -> dao.datasetInfo(k)?.let { k to it } }
                    buildJsonObject { putJsonObject("entries") { entries.forEach { (k, v) -> put(k, v) } } }
                }

                else -> return ToolResult(call.callId, ok = false, error = "UNKNOWN_TOOL")
            }
            ToolResult(call.callId, ok = true, output = output)
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            Log.e("SAFIA", "Tool ${call.name} failed", e)
            ToolResult(call.callId, ok = false, error = "DB_UNAVAILABLE")
        }
    }

    companion object {
        private const val ALL = "all"

        val DATASET_KEYS = listOf(
            "date_min", "date_max", "active_days", "booking_scope",
            "clean_rule_version", "closed_day_max_rows", "db_version", "source_file",
        )
    }
}

private fun HourAvailability.toJson() = buildJsonObject {
    put("hour", hour)
    put("occupied", occupied)
    put("capacity", capacity)
    put("load", load)
    put("is_closed", isClosed)
    put("shift_change", shiftChange)
    put("low_data", lowData)
    put("long_block", longBlock)
    put("usable", isUsable)
    put("label", occupancyLabel(this@toJson).name)
}

private fun ActivityEntity.toJson() = buildJsonObject {
    put("activity_id", id)
    put("is_person_count", isPersonCount)
    put("capacity", capacity)
    putJsonArray("resource_ids") { resourceIds.split(",").map { it.trim() }.filter { it.isNotEmpty() }.forEach { add(it) } }
}

private fun JsonObject.str(k: String) = getValue(k).jsonPrimitive.content
private fun JsonObject.int(k: String) = getValue(k).jsonPrimitive.int
private fun JsonObject.intOrNull(k: String) = get(k)?.takeIf { it !is JsonNull }?.jsonPrimitive?.intOrNull
private fun JsonObject.strList(k: String) =
    get(k)?.takeIf { it !is JsonNull }?.jsonArray?.map { it.jsonPrimitive.content }
private fun JsonObject.period() = get("period")?.takeIf { it !is JsonNull }?.jsonPrimitive?.content ?: "lectiu"
