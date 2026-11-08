package com.uab.mysaf.data

import android.content.Context
import com.uab.mysaf.data.db.AvailabilityDao
import com.uab.mysaf.data.db.MySafDatabase
import com.uab.mysaf.data.db.Period

/** Reads the historical availability shipped in the Room database. */
class AvailabilityRepository(private val dao: AvailabilityDao) {

    /** Hour rows for one activity and weekday, or empty if the activity is unknown. */
    suspend fun dayAvailability(activityId: String, weekday: String, allPeriod: Boolean): List<HourAvailability> =
        dao.day(activityId, Period.of(allPeriod), weekday).map { it.toHourAvailability() }

    /**
     * Quieter alternatives for [activityId] on [weekday] at [hour]. Alternative activities are
     * restricted to those measured the same way (people vs. courts) so loads are comparable.
     */
    suspend fun recommendations(
        activityId: String,
        weekday: String,
        hour: Int,
        allPeriod: Boolean = false,
    ): Recommendations {
        val period = Period.of(allPeriod)
        val activities = dao.activities()
        val requestedKind = activities.firstOrNull { it.id == activityId }?.isPersonCount
        val comparable = activities.filter { it.isPersonCount == requestedKind }.map { it.id }.toSet()

        return findAlternatives(
            activityId = activityId,
            weekday = weekday,
            hour = hour,
            sameDay = dao.day(activityId, period, weekday).map { it.toHourAvailability() },
            sameHourByWeekday = dao.hourAcrossWeekdays(activityId, period, hour)
                .associate { it.weekday to it.toHourAvailability() },
            sameSlotByActivity = dao.slotAcrossActivities(period, weekday, hour)
                .filter { it.activityId in comparable }
                .associate { it.activityId to it.toHourAvailability() },
        )
    }

    companion object {
        fun from(context: Context): AvailabilityRepository =
            AvailabilityRepository(MySafDatabase.getInstance(context).availabilityDao())
    }
}
