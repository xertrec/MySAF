package com.uab.mysaf.data

import android.content.Context
import androidx.room.Room
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.uab.mysaf.data.db.AvailabilityDao
import com.uab.mysaf.data.db.MySafDatabase
import com.uab.mysaf.data.db.Period
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Opens the database shipped in assets exactly like the app does. Room validates the asset
 * schema against the @Entity classes on open, so these tests fail if the Python export and
 * the Kotlin entities drift apart.
 */
@RunWith(AndroidJUnit4::class)
class PrepackagedDatabaseTest {

    private lateinit var context: Context
    private lateinit var db: MySafDatabase
    private lateinit var dao: AvailabilityDao

    @Before
    fun open() {
        context = InstrumentationRegistry.getInstrumentation().targetContext
        context.deleteDatabase(TEST_DB)
        db = Room.databaseBuilder(context, MySafDatabase::class.java, TEST_DB)
            .createFromAsset(MySafDatabase.ASSET_PATH)
            .build()
        dao = db.availabilityDao()
    }

    @After
    fun close() {
        db.close()
        context.deleteDatabase(TEST_DB)
    }

    @Test
    fun assetMatchesUiCatalogue() = runBlocking {
        val rows = dao.activities()
        assertEquals(activities.map { it.id }, rows.map { it.id })
        rows.forEach { row ->
            assertEquals(row.id, activityById(row.id).isPersonCount, row.isPersonCount)
            assertTrue(row.id, row.capacity > 0)
        }
    }

    @Test
    fun everyActivityHasAFullWeekForBothPeriods() = runBlocking {
        for (activity in activities) {
            for (period in listOf(Period.LECTIU, Period.ALL)) {
                for (weekday in WEEKDAYS) {
                    val day = dao.day(activity.id, period, weekday)
                    assertEquals("${activity.id}/$period/$weekday", (7..20).toList(), day.map { it.hour })
                }
            }
        }
    }

    @Test
    fun closedHoursFollowOpeningHours() = runBlocking {
        val opening = dao.openingHours().associateBy { it.weekday }
        assertEquals(WEEKDAYS.toSet(), opening.keys)
        assertEquals(9 * 60, opening.getValue("dg").openMin)
        assertEquals(14 * 60, opening.getValue("dg").closeMin)

        val sunday = dao.day("padel", Period.ALL, "dg")
        assertEquals(listOf(9, 10, 11, 12, 13), sunday.filterNot { it.isClosed }.map { it.hour })
        assertTrue(sunday.filter { it.isClosed }.all { it.avgOccupied == 0.0 && it.sampleDays == 0 })
    }

    @Test
    fun valuesAreWithinPlausibleRanges() = runBlocking {
        for (activity in dao.activities()) {
            for (weekday in WEEKDAYS) {
                for (row in dao.day(activity.id, Period.LECTIU, weekday)) {
                    assertEquals(activity.capacity, row.capacity)
                    assertTrue(row.avgOccupied >= 0.0 && row.avgOccupied <= 1.5 * row.capacity)
                    assertTrue(row.peakOccupied + 1e-9 >= row.avgOccupied)
                    assertTrue(row.longBlockShare in 0.0..1.0)
                }
            }
        }
    }

    @Test
    fun datasetInfoDescribesSource() = runBlocking {
        assertEquals("2026-04-01", dao.datasetInfo("date_min"))
        assertEquals("2026-10-31", dao.datasetInfo("date_max"))
        assertNotNull(dao.datasetInfo("clean_rule_version"))
    }

    @Test
    fun repositoryReturnsUiRowsAndValidRecommendations() = runBlocking {
        val repository = AvailabilityRepository(dao)
        val monday = repository.dayAvailability("sala_fitness", "dl", allPeriod = false)
        assertEquals(14, monday.size)
        assertTrue(monday.none { it.isClosed })
        assertTrue(monday.any { it.occupied > 0 })

        for (activity in activities) {
            val result = repository.recommendations(activity.id, "dl", 18)
            assertNotNull(activity.id, result.requested)
            result.alternatives.forEach { alt ->
                assertTrue(alt.reductionPp >= MIN_REDUCTION_PP)
                assertTrue(alt.row.isUsable)
                if (alt.kind == AlternativeKind.OTHER_ACTIVITY) {
                    // Only activities counted the same way are compared.
                    assertEquals(activity.isPersonCount, activityById(alt.activityId).isPersonCount)
                }
            }
        }
    }

    @Test
    fun appSingletonOpensAsset() = runBlocking {
        val dao = MySafDatabase.getInstance(context).availabilityDao()
        assertEquals(activities.size, dao.activities().size)
    }

    private companion object {
        const val TEST_DB = "mysaf-asset-test.db"
    }
}
