package com.uab.mysaf.data

import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.uab.mysaf.data.db.ActivityEntity
import com.uab.mysaf.data.db.HourlyAvailabilityEntity
import com.uab.mysaf.data.db.MySafDatabase
import com.uab.mysaf.data.db.Period
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** DAO queries and repository logic against a small in-memory database. */
@RunWith(AndroidJUnit4::class)
class AvailabilityDaoTest {

    private lateinit var db: MySafDatabase

    @Before
    fun setUp() = runBlocking {
        db = Room.inMemoryDatabaseBuilder(
            InstrumentationRegistry.getInstrumentation().targetContext,
            MySafDatabase::class.java,
        ).build()
        val dao = db.availabilityDao()
        dao.insertActivities(
            listOf(
                ActivityEntity("tennis", 1, isPersonCount = false, capacity = 5, resourceIds = "T1"),
                ActivityEntity("padel", 0, isPersonCount = false, capacity = 4, resourceIds = "P1"),
                ActivityEntity("sala_fitness", 2, isPersonCount = true, capacity = 120, resourceIds = "S"),
            ),
        )
        dao.insertHours(
            listOf(
                // inserted out of order on purpose
                hour("padel", "dl", 19, 3.6, 4),
                hour("padel", "dl", 18, 3.6, 4),
                hour("padel", "dl", 16, 1.2, 4),
                hour("padel", "dt", 18, 0.8, 4),
                hour("padel", "dl", 18, 0.4, 4, period = Period.ALL),
                hour("tennis", "dl", 18, 1.0, 5),
                hour("sala_fitness", "dl", 18, 6.0, 120), // much quieter, but not comparable
            ),
        )
    }

    @After
    fun tearDown() = db.close()

    private fun hour(
        activity: String,
        weekday: String,
        hour: Int,
        avg: Double,
        capacity: Int,
        period: String = Period.LECTIU,
    ) = HourlyAvailabilityEntity(
        activityId = activity, period = period, weekday = weekday, hour = hour,
        avgOccupied = avg, peakOccupied = avg, capacity = capacity, sampleDays = 20,
        longBlockShare = 0.0, isClosed = false,
    )

    @Test
    fun activitiesAreSortedBySortOrder() = runBlocking {
        assertEquals(listOf("padel", "tennis", "sala_fitness"), db.availabilityDao().activities().map { it.id })
        assertNull(db.availabilityDao().activity("unknown"))
    }

    @Test
    fun dayFiltersByPeriodAndWeekdayAndSortsByHour() = runBlocking {
        val dao = db.availabilityDao()
        assertEquals(listOf(16, 18, 19), dao.day("padel", Period.LECTIU, "dl").map { it.hour })
        assertEquals(listOf(0.4), dao.day("padel", Period.ALL, "dl").map { it.avgOccupied })
        assertTrue(dao.day("padel", Period.LECTIU, "dg").isEmpty())
    }

    @Test
    fun crossQueries() = runBlocking {
        val dao = db.availabilityDao()
        assertEquals(setOf("dl", "dt"), dao.hourAcrossWeekdays("padel", Period.LECTIU, 18).map { it.weekday }.toSet())
        assertEquals(
            setOf("padel", "tennis", "sala_fitness"),
            dao.slotAcrossActivities(Period.LECTIU, "dl", 18).map { it.activityId }.toSet(),
        )
    }

    @Test
    fun repositoryMapsRowsForTheSelectedPeriod() = runBlocking {
        val repository = AvailabilityRepository(db.availabilityDao())
        val lectiu = repository.dayAvailability("padel", "dl", allPeriod = false)
        assertEquals(listOf(1, 4, 4), lectiu.map { it.occupied })
        assertEquals(0.9f, lectiu.first { it.hour == 18 }.load, 1e-6f)
        assertEquals(0.1f, repository.dayAvailability("padel", "dl", allPeriod = true).single().load, 1e-6f)
    }

    @Test
    fun repositoryRecommendsOnlyComparableActivities() = runBlocking {
        val result = AvailabilityRepository(db.availabilityDao()).recommendations("padel", "dl", 18)
        val byKind = result.alternatives.associateBy { it.kind }
        assertEquals(16, byKind.getValue(AlternativeKind.SAME_DAY).row.hour)
        assertEquals(60, byKind.getValue(AlternativeKind.SAME_DAY).reductionPp)
        assertEquals("dt", byKind.getValue(AlternativeKind.OTHER_DAY).weekday)
        // tennis (courts) is proposed; sala_fitness (people) is not, although it is quieter.
        assertEquals("tennis", byKind.getValue(AlternativeKind.OTHER_ACTIVITY).activityId)
    }

    @Test
    fun unknownActivityHasNoData() = runBlocking {
        val repository = AvailabilityRepository(db.availabilityDao())
        assertTrue(repository.dayAvailability("nope", "dl", allPeriod = false).isEmpty())
        assertNull(repository.recommendations("nope", "dl", 18).requested)
    }
}
