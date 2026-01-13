package com.buceofeliz.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.net.Uri
import android.os.Build
import com.buceofeliz.app.data.AuthRepository

class BuceoFelizApp : Application() {

    lateinit var authRepository: AuthRepository
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        authRepository = AuthRepository(this)
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = getString(R.string.notification_channel_desc)
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 250, 250, 250)

                // Set notification sound
                val soundUri = Uri.parse(
                    "android.resource://${packageName}/raw/notification_sound"
                )
                val audioAttributes = AudioAttributes.Builder()
                    .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                    .build()
                setSound(soundUri, audioAttributes)
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ID = "chat_messages"

        @Volatile
        private var instance: BuceoFelizApp? = null

        fun getInstance(): BuceoFelizApp {
            return instance ?: throw IllegalStateException("Application not initialized")
        }
    }
}
