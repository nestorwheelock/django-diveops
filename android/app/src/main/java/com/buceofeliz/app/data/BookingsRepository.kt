package com.buceofeliz.app.data

import com.buceofeliz.app.api.ApiClient
import com.buceofeliz.app.api.BookingItem
import com.buceofeliz.app.api.BookingsResponse

class BookingsRepository(private val authRepository: AuthRepository) {

    suspend fun getBookings(): Result<BookingsResponse> {
        return try {
            val token = authRepository.getAuthToken()
                ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.getBookings(
                token = "Bearer $token"
            )

            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to get bookings"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun getUpcomingBookings(): Result<List<BookingItem>> {
        return getBookings().map { it.upcoming }
    }

    suspend fun getPastBookings(): Result<List<BookingItem>> {
        return getBookings().map { it.past }
    }
}
