package com.buceofeliz.app.location

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.buceofeliz.app.BuceoFelizApp
import com.buceofeliz.app.MainActivity
import com.buceofeliz.app.R
import com.buceofeliz.app.data.LocationRepository
import com.google.android.gms.location.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class LocationTrackingService : Service() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private lateinit var locationRepository: LocationRepository

    private var intervalSeconds = DEFAULT_INTERVAL_SECONDS

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service created")

        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        locationRepository = LocationRepository(BuceoFelizApp.getInstance().authRepository)

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { location ->
                    Log.d(TAG, "Location received: ${location.latitude}, ${location.longitude}")
                    serviceScope.launch {
                        locationRepository.submitLocation(
                            latitude = location.latitude,
                            longitude = location.longitude,
                            accuracy = location.accuracy,
                            altitude = location.altitude,
                            source = "fused"
                        ).fold(
                            onSuccess = { Log.d(TAG, "Location submitted successfully") },
                            onFailure = { Log.e(TAG, "Failed to submit location", it) }
                        )
                    }
                }
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Service started")

        // Get interval from intent
        intervalSeconds = intent?.getIntExtra(EXTRA_INTERVAL_SECONDS, DEFAULT_INTERVAL_SECONDS)
            ?: DEFAULT_INTERVAL_SECONDS

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, createNotification())
        startLocationUpdates()

        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "Service destroyed")
        stopLocationUpdates()
        serviceScope.cancel()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Location Tracking",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Shows when location is being shared"
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Location Sharing Active")
            .setContentText("Your location is being shared")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun startLocationUpdates() {
        if (ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            Log.e(TAG, "Location permission not granted")
            stopSelf()
            return
        }

        val locationRequest = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            intervalSeconds * 1000L
        ).apply {
            setMinUpdateIntervalMillis(intervalSeconds * 500L)
            setWaitForAccurateLocation(false)
        }.build()

        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            )
            Log.d(TAG, "Location updates started with interval: ${intervalSeconds}s")
        } catch (e: SecurityException) {
            Log.e(TAG, "Failed to start location updates", e)
            stopSelf()
        }
    }

    private fun stopLocationUpdates() {
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
            Log.d(TAG, "Location updates stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to stop location updates", e)
        }
    }

    companion object {
        private const val TAG = "LocationTrackingService"
        private const val CHANNEL_ID = "location_tracking"
        private const val NOTIFICATION_ID = 1001
        private const val EXTRA_INTERVAL_SECONDS = "interval_seconds"
        private const val DEFAULT_INTERVAL_SECONDS = 60

        fun start(context: Context, intervalSeconds: Int = DEFAULT_INTERVAL_SECONDS) {
            val intent = Intent(context, LocationTrackingService::class.java).apply {
                putExtra(EXTRA_INTERVAL_SECONDS, intervalSeconds)
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, LocationTrackingService::class.java))
        }
    }
}
