package com.uab.mysaf.data

import com.uab.mysaf.data.db.HourlyAvailabilityEntity
import com.uab.mysaf.data.db.Period
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AvailabilityMappingTest {

    private fun entity(
        avg: Double = 10.0,
        capacity: Int = 20,
        sampleDays: Int = 20,
        longBlockShare: Double = 0.0,
        isClosed: Boolean = false,
        hour: Int = 10,
    ) = HourlyAvailabilityEntity(
        activityId = "sala_fitness", period = Period.LECTIU, weekday = "dl", hour = hour,
        avgOccupied = avg, peakOccupied = avg, capacity = capacity, sampleDays = sampleDays,
        longBlockShare = longBlockShare, isClosed = isClosed,
    )

    @Test
    fun mapsAverageToRoundedOccupiedAndExactLoad() {
        val row = entity(avg = 86.2361, capacity = 120).toHourAvailability()
        assertEquals(10, row.hour)
        assertEquals(86, row.occupied)
        assertEquals(120, row.capacity)
        assertEquals(0.7186f, row.load, 1e-4f)
        assertFalse(row.isClosed || row.lowData || row.longBlock || row.shiftChange)
    }

    @Test
    fun courtsKeepFractionalLoad() {
        // 1.15 of 4 courts busy: displayed as 1 court, but the bar uses the exact share.
        val row = entity(avg = 1.15, capacity = 4).toHourAvailability()
        assertEquals(1, row.occupied)
        assertEquals(0.2875f, row.load, 1e-4f)
    }

    @Test
    fun occupiedIsClampedButLoadKeepsOverCapacity() {
        val row = entity(avg = 121.4, capacity = 120).toHourAvailability()
        assertEquals(120, row.occupied)
        assertTrue(row.load > 1f)
        assertEquals(OccupancyLabel.FULL, occupancyLabel(row))
    }

    @Test
    fun closedHoursAreZeroedAndNotFlagged() {
        val row = entity(avg = 5.0, sampleDays = 0, longBlockShare = 0.9, isClosed = true).toHourAvailability()
        assertTrue(row.isClosed)
        assertEquals(0, row.occupied)
        assertEquals(0f, row.load)
        assertFalse(row.lowData)
        assertFalse(row.longBlock)
    }

    @Test
    fun lowDataBelowMinimumSampleDays() {
        assertTrue(entity(sampleDays = MIN_SAMPLE_DAYS - 1).toHourAvailability().lowData)
        assertFalse(entity(sampleDays = MIN_SAMPLE_DAYS).toHourAvailability().lowData)
    }

    @Test
    fun longBlockAtThreshold() {
        assertFalse(entity(longBlockShare = 0.249).toHourAvailability().longBlock)
        assertTrue(entity(longBlockShare = LONG_BLOCK_SHARE_THRESHOLD).toHourAvailability().longBlock)
    }

    @Test
    fun zeroCapacityDoesNotDivideByZero() {
        val row = entity(avg = 3.0, capacity = 0).toHourAvailability()
        assertEquals(1, row.capacity)
        assertEquals(1, row.occupied)
    }

    @Test
    fun occupancyLabelThresholds() {
        assertEquals(OccupancyLabel.QUIET, occupancyLabel(0f))
        assertEquals(OccupancyLabel.QUIET, occupancyLabel(0.499f))
        assertEquals(OccupancyLabel.MODERATE, occupancyLabel(0.5f))
        assertEquals(OccupancyLabel.MODERATE, occupancyLabel(0.799f))
        assertEquals(OccupancyLabel.FULL, occupancyLabel(0.8f))
    }

    @Test
    fun quieterHourSkipsClosedAndLowDataRows() {
        val rows = listOf(
            HourAvailability(hour = 7, occupied = 0, capacity = 10, isClosed = true),
            HourAvailability(hour = 8, occupied = 1, capacity = 10, lowData = true),
            HourAvailability(hour = 9, occupied = 6, capacity = 10),
            HourAvailability(hour = 10, occupied = 3, capacity = 10),
            HourAvailability(hour = 11, occupied = 2, capacity = 10, shiftChange = true),
        )
        assertEquals(10, quieterHour(rows))
        assertNull(quieterHour(rows.filter { it.hour < 9 }))
    }

    @Test
    fun periodCodesMatchDatabase() {
        assertEquals("lectiu", Period.of(allPeriod = false))
        assertEquals("all", Period.of(allPeriod = true))
    }
}
