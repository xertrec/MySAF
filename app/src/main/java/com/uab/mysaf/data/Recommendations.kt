package com.uab.mysaf.data

import kotlin.math.abs
import kotlin.math.roundToInt

/** Minimum improvement, in percentage points, for an alternative to be proposed. */
const val MIN_REDUCTION_PP = 10

/** How far from the requested hour a same-day alternative may be. */
const val SAME_DAY_MAX_HOUR_DISTANCE = 3

enum class AlternativeKind { SAME_DAY, OTHER_DAY, OTHER_ACTIVITY }

data class Alternative(
    val kind: AlternativeKind,
    val activityId: String,
    val weekday: String,
    val row: HourAvailability,
    /** Percentage points quieter than the requested slot. */
    val reductionPp: Int,
)

data class Recommendations(
    /** The slot the user asked about, or null if it has no data. */
    val requested: HourAvailability?,
    val alternatives: List<Alternative>,
) {
    val isAlreadyQuiet: Boolean
        get() = requested != null && occupancyLabel(requested) == OccupancyLabel.QUIET
}

/**
 * Picks at most one alternative of each [AlternativeKind]: the quietest usable slot that is
 * at least [minReductionPp] percentage points below the requested one.
 *
 * @param sameDay every hour of the requested activity and weekday.
 * @param sameHourByWeekday the requested hour on each weekday for the requested activity.
 * @param sameSlotByActivity the requested weekday and hour for every *comparable* activity.
 */
fun findAlternatives(
    activityId: String,
    weekday: String,
    hour: Int,
    sameDay: List<HourAvailability>,
    sameHourByWeekday: Map<String, HourAvailability>,
    sameSlotByActivity: Map<String, HourAvailability>,
    minReductionPp: Int = MIN_REDUCTION_PP,
): Recommendations {
    val requested = sameDay.firstOrNull { it.hour == hour }?.takeIf { !it.isClosed }
        ?: return Recommendations(requested = null, alternatives = emptyList())

    fun reduction(row: HourAvailability) = ((requested.load - row.load) * 100f).roundToInt()

    val sameDayBest = sameDay
        .filter { it.isUsable && it.hour != hour && abs(it.hour - hour) <= SAME_DAY_MAX_HOUR_DISTANCE }
        .minWithOrNull(compareBy<HourAvailability> { it.load }.thenBy { abs(it.hour - hour) })
        ?.let { Alternative(AlternativeKind.SAME_DAY, activityId, weekday, it, reduction(it)) }

    val otherDayBest = sameHourByWeekday
        .filter { (day, row) -> day != weekday && row.isUsable }
        .entries
        .minWithOrNull(compareBy<Map.Entry<String, HourAvailability>> { it.value.load }
            .thenBy { WEEKDAYS.indexOf(it.key) })
        ?.let { (day, row) -> Alternative(AlternativeKind.OTHER_DAY, activityId, day, row, reduction(row)) }

    val otherActivityBest = sameSlotByActivity
        .filter { (id, row) -> id != activityId && row.isUsable }
        .entries
        .minByOrNull { it.value.load }
        ?.let { (id, row) -> Alternative(AlternativeKind.OTHER_ACTIVITY, id, weekday, row, reduction(row)) }

    val alternatives = listOfNotNull(sameDayBest, otherDayBest, otherActivityBest)
        .filter { it.reductionPp >= minReductionPp }
    return Recommendations(requested, alternatives)
}
