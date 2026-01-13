package com.buceofeliz.app.data

import android.content.Context
import com.buceofeliz.app.BuildConfig
import com.buceofeliz.app.api.ApiClient
import com.buceofeliz.app.api.VersionCheckResponse

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
