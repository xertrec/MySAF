package com.uab.mysaf.data

/**
 * Deterministic demonstration values used only to lay out the UI.
 * Replace this file's source with the on-device profile built from daily_counts.json.
 */
data class HourAvailability(
    val hour: Int,
    val occupied: Int,
    val capacity: Int,
    val isClosed: Boolean = false,
    val shiftChange: Boolean = false,
    val lowData: Boolean = false,
    val longBlock: Boolean = false,
)

enum class OccupancyLabel(val catalan: String) {
    QUIET("Tranquil"),
    MODERATE("Moderat"),
    FULL("Ple"),
}

fun occupancyLabel(row: HourAvailability): OccupancyLabel {
    val load = row.occupied.toFloat() / row.capacity.coerceAtLeast(1)
    return when {
        load < 0.5f -> OccupancyLabel.QUIET
        load < 0.8f -> OccupancyLabel.MODERATE
        else -> OccupancyLabel.FULL
    }
}

private val weekdayCounts = listOf(48, 96, 102, 92, 78, 76, 58, 44, 71, 107, 106, 71, 52, 39)

fun sampleAvailability(
    activity: ActivityInfo,
    weekday: String,
    allPeriod: Boolean,
): List<HourAvailability> {
    val openStart = when (weekday) {
        "ds" -> 8
        "dg" -> 9
        else -> 7
    }
    val openEnd = when (weekday) {
        "ds" -> 20
        "dg" -> 14
        else -> 21
    }
    val dayOffset = listOf("dl", "dt", "dc", "dj", "dv", "ds", "dg").indexOf(weekday).coerceAtLeast(0)
    return (7..20).map { hour ->
        val closed = hour < openStart || hour >= openEnd
        val poolValue = weekdayCounts.getOrElse((hour - 7).coerceAtLeast(0)) { 39 }
        val dayAdjusted = (poolValue + (dayOffset - 2) * 3).coerceAtLeast(0)
        val periodAdjusted = if (allPeriod) (dayAdjusted * 0.94f).toInt() else dayAdjusted
        val occupied = if (activity.isPersonCount) {
            (periodAdjusted * activity.capacity / 120).coerceIn(0, activity.capacity)
        } else {
            // For booking-based activities, display occupied resource units.
            val ratio = (periodAdjusted.toFloat() / 120f).coerceIn(0f, 1f)
            (ratio * activity.capacity).toInt().coerceIn(0, activity.capacity)
        }
        HourAvailability(
            hour = hour,
            occupied = if (closed) 0 else occupied,
            capacity = activity.capacity,
            isClosed = closed,
            shiftChange = activity.id == "sala_fitness" && weekday !in listOf("ds", "dg") && hour in listOf(10, 15),
            longBlock = activity.isPersonCount.not() && hour in 17..18 && weekday == "ds",
        )
    }
}

fun quieterHour(rows: List<HourAvailability>): Int? =
    rows.filterNot { it.isClosed || it.shiftChange || it.lowData }
        .minByOrNull { it.occupied.toFloat() / it.capacity.coerceAtLeast(1) }
        ?.hour

fun weekdayName(short: String): String = when (short) {
    "dl" -> "dilluns"
    "dt" -> "dimarts"
    "dc" -> "dimecres"
    "dj" -> "dijous"
    "dv" -> "divendres"
    "ds" -> "dissabte"
    "dg" -> "diumenge"
    else -> "dilluns"
}
