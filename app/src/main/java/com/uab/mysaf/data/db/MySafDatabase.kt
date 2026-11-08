package com.uab.mysaf.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * Read-only database prepackaged in assets/database/mysaf.db.
 *
 * Regenerate the asset with `python data_engineering/scripts/create_database.py`.
 * When the asset changes, bump [version] together with DB_VERSION in that script:
 * Room then discards the installed copy and copies the new asset.
 */
@Database(
    entities = [
        ActivityEntity::class,
        HourlyAvailabilityEntity::class,
        OpeningHoursEntity::class,
        DatasetInfoEntity::class,
    ],
    version = 1,
    exportSchema = false,
)
abstract class MySafDatabase : RoomDatabase() {

    abstract fun availabilityDao(): AvailabilityDao

    companion object {
        const val ASSET_PATH = "database/mysaf.db"
        const val NAME = "mysaf.db"

        @Volatile
        private var instance: MySafDatabase? = null

        fun getInstance(context: Context): MySafDatabase =
            instance ?: synchronized(this) {
                instance ?: build(context.applicationContext).also { instance = it }
            }

        private fun build(context: Context): MySafDatabase =
            Room.databaseBuilder(context, MySafDatabase::class.java, NAME)
                .createFromAsset(ASSET_PATH)
                .fallbackToDestructiveMigration(dropAllTables = true)
                .build()
    }
}
