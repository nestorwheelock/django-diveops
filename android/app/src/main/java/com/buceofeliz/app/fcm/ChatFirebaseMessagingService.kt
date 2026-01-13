package com.buceofeliz.app.fcm

import android.Manifest
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.media.RingtoneManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.buceofeliz.app.BuceoFelizApp
import com.buceofeliz.app.MainActivity
import com.buceofeliz.app.R
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class ChatFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "FCMService"
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token: $token")

        // Register the new token with the server
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val deviceId = Settings.Secure.getString(
                    applicationContext.contentResolver,
                    Settings.Secure.ANDROID_ID
                )
                val deviceName = "${Build.MANUFACTURER} ${Build.MODEL}"

                BuceoFelizApp.getInstance().authRepository.registerFCMToken(
                    fcmToken = token,
                    deviceId = deviceId,
                    deviceName = deviceName
                )
                Log.d(TAG, "FCM token registered with server")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to register FCM token", e)
            }
        }
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)

        Log.d(TAG, "Message received from: ${remoteMessage.from}")

        // Check if message contains data payload
        remoteMessage.data.isNotEmpty().let {
            Log.d(TAG, "Message data: ${remoteMessage.data}")

            val title = remoteMessage.data["title"] ?: "New Message"
            val body = remoteMessage.data["body"] ?: ""
            val conversationId = remoteMessage.data["conversation_id"]
            val personId = remoteMessage.data["person_id"]
            val messageId = remoteMessage.data["message_id"]

            showNotification(title, body, conversationId, personId)
        }

        // Check if message contains notification payload (when app is in foreground)
        remoteMessage.notification?.let {
            Log.d(TAG, "Message notification: ${it.body}")
            showNotification(
                title = it.title ?: "New Message",
                body = it.body ?: "",
                conversationId = remoteMessage.data["conversation_id"],
                personId = remoteMessage.data["person_id"]
            )
        }
    }

    private fun showNotification(
        title: String,
        body: String,
        conversationId: String?,
        personId: String?
    ) {
        // Create intent to open chat when notification is tapped
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            putExtra("conversation_id", conversationId)
            putExtra("person_id", personId)
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            conversationId?.hashCode() ?: 0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Get notification sound
        val defaultSoundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

        // Build notification
        val notificationBuilder = NotificationCompat.Builder(this, BuceoFelizApp.CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setSound(defaultSoundUri)
            .setVibrate(longArrayOf(0, 250, 250, 250))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setContentIntent(pendingIntent)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))

        // Show notification
        with(NotificationManagerCompat.from(this)) {
            if (ActivityCompat.checkSelfPermission(
                    this@ChatFirebaseMessagingService,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                notify(conversationId?.hashCode() ?: System.currentTimeMillis().toInt(), notificationBuilder.build())
            }
        }
    }
}
