package com.diveops.chat.data

import com.diveops.chat.api.ApiClient
import com.diveops.chat.api.LocationBatchRequest
import com.diveops.chat.api.LocationSettingsRequest
import com.diveops.chat.api.LocationSettingsResponse
import com.diveops.chat.api.LocationUpdateRequest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class LocationRepository(private val authRepository: AuthRepository) {

    private val isoDateFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
        timeZone = TimeZone.getTimeZone("UTC")
    }

    suspend fun submitLocation(
        latitude: Double,
        longitude: Double,
        accuracy: Float? = null,
        altitude: Double? = null,
        source: String = "fused"
    ): Result<String> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val request = LocationUpdateRequest(
                latitude = latitude,
                longitude = longitude,
                accuracy_meters = accuracy?.toDouble(),
                altitude_meters = altitude,
                source = source,
                recorded_at = isoDateFormat.format(Date())
            )

            val response = ApiClient.apiService.submitLocation(
                token = "Bearer $token",
                request = request
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.id)
            } else {
                Result.failure(Exception("Failed to submit location"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun submitLocationBatch(updates: List<LocationUpdateRequest>): Result<Int> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.submitLocationBatch(
                token = "Bearer $token",
                request = LocationBatchRequest(updates)
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.created)
            } else {
                Result.failure(Exception("Failed to submit location batch"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getSettings(): Result<LocationSettingsResponse> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getLocationSettings(
                token = "Bearer $token"
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to get location settings"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateSettings(
        visibility: String? = null,
        isTrackingEnabled: Boolean? = null,
        trackingIntervalSeconds: Int? = null
    ): Result<LocationSettingsResponse> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val request = LocationSettingsRequest(
                visibility = visibility,
                is_tracking_enabled = isTrackingEnabled,
                tracking_interval_seconds = trackingIntervalSeconds
            )

            val response = ApiClient.apiService.updateLocationSettings(
                token = "Bearer $token",
                request = request
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to update location settings"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
