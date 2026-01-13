package com.buceofeliz.app.data

import com.buceofeliz.app.api.ApiClient
import com.buceofeliz.app.api.CertificationItem
import com.buceofeliz.app.api.EmergencyContactItem
import com.buceofeliz.app.api.ProfileResponse
import com.buceofeliz.app.api.ProfileUpdateRequest

class ProfileRepository(private val authRepository: AuthRepository) {

    suspend fun getProfile(): Result<ProfileResponse> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getProfile(
                token = "Bearer $token"
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to get profile"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun updateProfile(request: ProfileUpdateRequest): Result<ProfileResponse> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.updateProfile(
                token = "Bearer $token",
                request = request
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to update profile"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getCertifications(): Result<List<CertificationItem>> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getCertifications(
                token = "Bearer $token"
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.certifications)
            } else {
                Result.failure(Exception("Failed to get certifications"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getEmergencyContacts(): Result<List<EmergencyContactItem>> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getEmergencyContacts(
                token = "Bearer $token"
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!.contacts)
            } else {
                Result.failure(Exception("Failed to get emergency contacts"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
