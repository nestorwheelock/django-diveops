package com.diveops.chat.data

import android.content.Context
import com.diveops.chat.BuildConfig
import com.diveops.chat.api.ApiClient
import com.diveops.chat.api.VersionCheckResponse

class UpdateRepository(private val context: Context) {

    suspend fun checkForUpdate(): Result<VersionCheckResponse> {
        return try {
            val currentVersionCode = BuildConfig.VERSION_CODE

            val response = ApiClient.apiService.checkVersion(
                platform = "android",
                currentVersion = currentVersionCode
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to check for updates"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
