package com.uab.mysaf.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RecommendationsTest {

    /** Row with load = percent / 100. */
    private fun row(hour: Int, percent: Int, lowData: Boolean = false, closed: Boolean = false) =
        HourAvailability(hour = hour, occupied = percent, capacity = 100, lowData = lowData, isClosed = closed)

    private val day = listOf(
        row(7, 0, closed = true),
        row(14, 30),
        row(15, 40),
        row(16, 55),
        row(17, 85),
        row(18, 90), // requested
        row(19, 80),
        row(20, 60),
    )

    private fun recommend(
        sameDay: List<HourAvailability> = day,
        byWeekday: Map<String, HourAvailability> = emptyMap(),
        byActivity: Map<String, HourAvailability> = emptyMap(),
        hour: Int = 18,
    ) = findAlternatives("padel", "dl", hour, sameDay, byWeekday, byActivity)

    @Test
    fun sameDayPicksQuietestHourWithinThreeHours() {
        val result = recommend()
        val alt = result.alternatives.single()
        assertEquals(AlternativeKind.SAME_DAY, alt.kind)
        // 14:00 is quieter but 4 hours away; 15:00 is the quietest within 3 hours.
        assertEquals(15, alt.row.hour)
        assertEquals(50, alt.reductionPp)
        assertEquals("dl", alt.weekday)
        assertEquals(0.9f, result.requested!!.load, 1e-6f)
    }

    @Test
    fun sameDayTieBreaksOnClosestHour() {
        val result = recommend(sameDay = listOf(row(15, 40), row(18, 90), row(19, 40)))
        assertEquals(19, result.alternatives.single().row.hour)
    }

    @Test
    fun lowDataAndClosedSlotsAreNeverProposed() {
        val sameDay = listOf(row(17, 5, lowData = true), row(18, 90), row(19, 0, closed = true))
        val byWeekday = mapOf("dt" to row(18, 1, lowData = true), "dc" to row(18, 0, closed = true))
        assertTrue(recommend(sameDay, byWeekday).alternatives.isEmpty())
    }

    @Test
    fun requiresTenPercentagePointsReduction() {
        val sameDay = listOf(row(17, 81), row(18, 90))
        assertTrue(recommend(sameDay).alternatives.isEmpty())
        val justEnough = listOf(row(17, 80), row(18, 90))
        assertEquals(10, recommend(justEnough).alternatives.single().reductionPp)
    }

    @Test
    fun otherDayPicksQuietestWeekdayExcludingRequestedOne() {
        val byWeekday = mapOf(
            "dl" to row(18, 10), // same weekday: ignored
            "dt" to row(18, 70),
            "dj" to row(18, 45),
            "dv" to row(18, 45),
        )
        val alt = recommend(sameDay = listOf(row(18, 90)), byWeekday = byWeekday).alternatives.single()
        assertEquals(AlternativeKind.OTHER_DAY, alt.kind)
        assertEquals("dj", alt.weekday) // tie with dv resolved in week order
        assertEquals(45, alt.reductionPp)
    }

    @Test
    fun otherActivityExcludesRequestedActivity() {
        val byActivity = mapOf("padel" to row(18, 0), "tennis" to row(18, 50), "esquaix" to row(18, 20))
        val alt = recommend(sameDay = listOf(row(18, 90)), byActivity = byActivity).alternatives.single()
        assertEquals(AlternativeKind.OTHER_ACTIVITY, alt.kind)
        assertEquals("esquaix", alt.activityId)
        assertEquals(70, alt.reductionPp)
    }

    @Test
    fun returnsOneAlternativePerKindInFixedOrder() {
        val result = recommend(
            byWeekday = mapOf("dt" to row(18, 20)),
            byActivity = mapOf("tennis" to row(18, 30)),
        )
        assertEquals(
            listOf(AlternativeKind.SAME_DAY, AlternativeKind.OTHER_DAY, AlternativeKind.OTHER_ACTIVITY),
            result.alternatives.map { it.kind },
        )
    }

    @Test
    fun missingOrClosedRequestedSlotGivesNoRecommendations() {
        val missing = recommend(hour = 12)
        assertNull(missing.requested)
        assertTrue(missing.alternatives.isEmpty())
        assertNull(recommend(hour = 7).requested)
    }

    @Test
    fun alreadyQuietWhenRequestedSlotIsBelowHalf() {
        assertTrue(recommend(hour = 15).isAlreadyQuiet)
        assertFalse(recommend(hour = 18).isAlreadyQuiet)
        assertFalse(recommend(hour = 12).isAlreadyQuiet)
    }
}
