package com.uab.mysaf.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface AvailabilityDao {

    @Query("SELECT * FROM activity ORDER BY sort_order")
    suspend fun activities(): List<ActivityEntity>

    @Query("SELECT * FROM activity WHERE id = :activityId")
    suspend fun activity(activityId: String): ActivityEntity?

    /** All hours of one day for one activity, in hour order. */
    @Query(
        "SELECT * FROM hourly_availability " +
            "WHERE activity_id = :activityId AND period = :period AND weekday = :weekday " +
            "ORDER BY hour",
    )
    suspend fun day(activityId: String, period: String, weekday: String): List<HourlyAvailabilityEntity>

    /** The same hour on every weekday for one activity. */
    @Query(
        "SELECT * FROM hourly_availability " +
            "WHERE activity_id = :activityId AND period = :period AND hour = :hour",
    )
    suspend fun hourAcrossWeekdays(activityId: String, period: String, hour: Int): List<HourlyAvailabilityEntity>

    /** The same weekday and hour for every activity. */
    @Query(
        "SELECT * FROM hourly_availability " +
            "WHERE period = :period AND weekday = :weekday AND hour = :hour",
    )
    suspend fun slotAcrossActivities(period: String, weekday: String, hour: Int): List<HourlyAvailabilityEntity>

    @Query("SELECT * FROM opening_hours")
    suspend fun openingHours(): List<OpeningHoursEntity>

    @Query("SELECT value FROM dataset_info WHERE `key` = :key")
    suspend fun datasetInfo(key: String): String?

    // The shipped database is read-only in practice; these are used by tests.
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertActivities(rows: List<ActivityEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertHours(rows: List<HourlyAvailabilityEntity>)
}
