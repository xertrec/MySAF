package com.uab.mysaf.data.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/*
 * Tables of the prepackaged database built by data_engineering/scripts/create_database.py.
 * Room validates the asset against these entities when it is opened, so any change here
 * must be mirrored in SCHEMA in that script (data_engineering/tests checks the column names).
 */

/** One activity shown on the home screen. */
@Entity(tableName = "activity")
data class ActivityEntity(
    @PrimaryKey @ColumnInfo(name = "id") val id: String,
    @ColumnInfo(name = "sort_order") val sortOrder: Int,
    /** true: rooms/pools, counted in people. false: courts/pitches, counted in units. */
    @ColumnInfo(name = "is_person_count") val isPersonCount: Boolean,
    /** People (inventory capacity) or number of courts/pitches. */
    @ColumnInfo(name = "capacity") val capacity: Int,
    /** Comma-separated canonical resource ids aggregated into this activity. */
    @ColumnInfo(name = "resource_ids") val resourceIds: String,
)

/** Historical average occupancy of one activity for one weekday, period and hour. */
@Entity(
    tableName = "hourly_availability",
    primaryKeys = ["activity_id", "period", "weekday", "hour"],
)
data class HourlyAvailabilityEntity(
    @ColumnInfo(name = "activity_id") val activityId: String,
    /** [Period.LECTIU] or [Period.ALL]. */
    @ColumnInfo(name = "period") val period: String,
    /** Catalan short code: dl, dt, dc, dj, dv, ds, dg. */
    @ColumnInfo(name = "weekday") val weekday: String,
    @ColumnInfo(name = "hour") val hour: Int,
    /** Mean people (or busy courts) during the hour, averaged over the observed days. */
    @ColumnInfo(name = "avg_occupied") val avgOccupied: Double,
    /** Mean of the per-day maximum during the hour. */
    @ColumnInfo(name = "peak_occupied") val peakOccupied: Double,
    @ColumnInfo(name = "capacity") val capacity: Int,
    /** Number of active days averaged. */
    @ColumnInfo(name = "sample_days") val sampleDays: Int,
    /** Share (0..1) of booked minutes coming from long/club blocks. */
    @ColumnInfo(name = "long_block_share") val longBlockShare: Double,
    @ColumnInfo(name = "is_closed") val isClosed: Boolean,
)

@Entity(tableName = "opening_hours")
data class OpeningHoursEntity(
    @PrimaryKey @ColumnInfo(name = "weekday") val weekday: String,
    @ColumnInfo(name = "open_min") val openMin: Int,
    @ColumnInfo(name = "close_min") val closeMin: Int,
)

@Entity(tableName = "dataset_info")
data class DatasetInfoEntity(
    @PrimaryKey @ColumnInfo(name = "key") val key: String,
    @ColumnInfo(name = "value") val value: String,
)

/** Values stored in [HourlyAvailabilityEntity.period]. */
object Period {
    const val LECTIU = "lectiu"
    const val ALL = "all"

    fun of(allPeriod: Boolean): String = if (allPeriod) ALL else LECTIU
}
