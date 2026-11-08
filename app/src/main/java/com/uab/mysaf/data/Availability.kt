package com.uab.mysaf.data

import androidx.annotation.StringRes
import com.uab.mysaf.R
import com.uab.mysaf.data.db.HourlyAvailabilityEntity
import kotlin.math.roundToInt

/** Days averaged below this count are flagged as "few data" (see methodology_limit_6). */
const val MIN_SAMPLE_DAYS = 8

/** An hour is flagged as including club/school blocks above this share of booked minutes. */
const val LONG_BLOCK_SHARE_THRESHOLD = 0.25

/**
 * Hours with a staff shift change, per activity, whose figures are not reliable
 * (see methodology_limit_7). They are shown as "shift change" and never recommended.
 */
val SHIFT_CHANGE_HOURS: Map<String, Set<Int>> = mapOf("sala_fitness" to setOf(10, 15))

fun isShiftChange(activityId: String, hour: Int): Boolean =
    SHIFT_CHANGE_HOURS[activityId]?.contains(hour) == true

data class HourAvailability(
    val hour: Int,
    /** Rounded people (or busy courts) used for display. */
    val occupied: Int,
    val capacity: Int,
    val isClosed: Boolean = false,
    val shiftChange: Boolean = false,
    val lowData: Boolean = false,
    val longBlock: Boolean = false,
    /** Unrounded occupancy ratio; may exceed 1 when bookings exceed inventory capacity. */
    val load: Float = occupied.toFloat() / capacity.coerceAtLeast(1),
)

enum class OccupancyLabel(@StringRes val labelRes: Int) {
    QUIET(R.string.occupancy_quiet),
    MODERATE(R.string.occupancy_moderate),
    FULL(R.string.occupancy_full),
}

fun occupancyLabel(load: Float): OccupancyLabel = when {
    load < 0.5f -> OccupancyLabel.QUIET
    load < 0.8f -> OccupancyLabel.MODERATE
    else -> OccupancyLabel.FULL
}

fun occupancyLabel(row: HourAvailability): OccupancyLabel = occupancyLabel(row.load)

/** Whether a row can be offered to the user as a reliable time slot. */
val HourAvailability.isUsable: Boolean
    get() = !isClosed && !shiftChange && !lowData

fun HourlyAvailabilityEntity.toHourAvailability(): HourAvailability {
    val cap = capacity.coerceAtLeast(1)
    return HourAvailability(
        hour = hour,
        occupied = if (isClosed) 0 else avgOccupied.roundToInt().coerceIn(0, cap),
        capacity = cap,
        isClosed = isClosed,
        shiftChange = !isClosed && isShiftChange(activityId, hour),
        lowData = !isClosed && sampleDays < MIN_SAMPLE_DAYS,
        longBlock = !isClosed && longBlockShare >= LONG_BLOCK_SHARE_THRESHOLD,
        load = if (isClosed) 0f else (avgOccupied / cap).toFloat().coerceAtLeast(0f),
    )
}

fun quieterHour(rows: List<HourAvailability>): Int? =
    rows.filter { it.isUsable }
        .minByOrNull { it.load }
        ?.hour

/** P2: the [limit] quietest usable hours of a day, quietest first (used by the SAFIA chat). */
fun quietestHours(rows: List<HourAvailability>, limit: Int): List<HourAvailability> =
    rows.filter { it.isUsable }
        .sortedBy { it.load }
        .take(limit.coerceAtLeast(0))

val WEEKDAYS = listOf("dl", "dt", "dc", "dj", "dv", "ds", "dg")

@StringRes
fun weekdayNameRes(short: String): Int = when (short) {
    "dl" -> R.string.weekday_monday
    "dt" -> R.string.weekday_tuesday
    "dc" -> R.string.weekday_wednesday
    "dj" -> R.string.weekday_thursday
    "dv" -> R.string.weekday_friday
    "ds" -> R.string.weekday_saturday
    "dg" -> R.string.weekday_sunday
    else -> R.string.weekday_monday
}

/** General SAF opening time for one weekday, in minutes from midnight. */
data class OpeningHours(val weekday: String, val openMin: Int, val closeMin: Int) {
    fun isOpenAt(minuteOfDay: Int): Boolean = minuteOfDay in openMin until closeMin
}

/** Short weekday code ("dl"…"dg") for a [java.time.DayOfWeek]. */
fun weekdayCode(day: java.time.DayOfWeek): String = WEEKDAYS[day.value - 1]

/** Epoch day of the next date (today included) that falls on weekday [code] ("dl"…"dg"). */
fun nextEpochDayFor(code: String): Long {
    val today = java.time.LocalDate.now()
    val target = WEEKDAYS.indexOf(code).takeIf { it >= 0 } ?: return today.toEpochDay()
    val delta = (target - (today.dayOfWeek.value - 1) + 7) % 7
    return today.plusDays(delta.toLong()).toEpochDay()
}

/** Weekday code for today. */
fun todayWeekday(): String = weekdayCode(java.time.LocalDate.now().dayOfWeek)

/**
 * Groups the [limit] quietest usable hours into contiguous ranges (start hour, end hour exclusive),
 * sorted by start time. E.g. quiet 8, 9 and 13 → [8..10, 13..14].
 */
fun quietRanges(rows: List<HourAvailability>, limit: Int = 3): List<IntRange> {
    val hours = quietestHours(rows, limit).map { it.hour }.sorted()
    val ranges = mutableListOf<IntRange>()
    for (h in hours) {
        val last = ranges.lastOrNull()
        if (last != null && last.last == h) ranges[ranges.lastIndex] = last.first..(h + 1)
        else ranges += h..(h + 1)
    }
    return ranges
}

/** The busiest usable hour of a day, or null. */
fun busiestHour(rows: List<HourAvailability>): Int? =
    rows.filter { it.isUsable }.maxByOrNull { it.load }?.hour
