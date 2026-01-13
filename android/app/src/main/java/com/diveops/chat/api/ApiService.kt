package com.diveops.chat.api

import retrofit2.Response
import retrofit2.http.*

// Request/Response DTOs
data class LoginRequest(
    val email: String,
    val password: String
)

data class LoginResponse(
    val token: String,
    val user: UserInfo
)

data class UserInfo(
    val id: Int,
    val email: String,
    val first_name: String,
    val last_name: String
)

// Customer Login (returns is_staff flag)
data class CustomerLoginResponse(
    val token: String,
    val user: CustomerUserInfo
)

data class CustomerUserInfo(
    val id: Int,
    val person_id: String,
    val email: String,
    val first_name: String,
    val last_name: String,
    val is_staff: Boolean
)

// Version Check (In-App Updates)
data class VersionCheckResponse(
    val update_available: Boolean,
    val force_update: Boolean,
    val latest_version: LatestVersion? = null
)

data class LatestVersion(
    val version_code: Int,
    val version_name: String,
    val download_url: String,
    val release_notes: String
)

// Customer Bookings
data class BookingsResponse(
    val upcoming: List<BookingItem>,
    val past: List<BookingItem>
)

data class BookingItem(
    val id: String,
    val excursion_id: String,
    val excursion_name: String,
    val departure_date: String?,
    val departure_time: String?,
    val status: String
)

// Location Update
data class LocationUpdateRequest(
    val latitude: Double,
    val longitude: Double,
    val accuracy_meters: Double? = null,
    val altitude_meters: Double? = null,
    val source: String = "fused",
    val recorded_at: String? = null
)

data class LocationUpdateResponse(
    val id: String
)

data class LocationBatchRequest(
    val updates: List<LocationUpdateRequest>
)

data class LocationBatchResponse(
    val created: Int
)

// Location Settings
data class LocationSettingsResponse(
    val visibility: String,
    val is_tracking_enabled: Boolean,
    val tracking_interval_seconds: Int
)

data class LocationSettingsRequest(
    val visibility: String? = null,
    val is_tracking_enabled: Boolean? = null,
    val tracking_interval_seconds: Int? = null
)

data class FCMRegisterRequest(
    val registration_id: String,
    val platform: String = "android",
    val device_id: String = "",
    val device_name: String = "",
    val app_version: String = ""
)

data class FCMRegisterResponse(
    val status: String,
    val device_id: String
)

data class ConversationsResponse(
    val conversations: List<ConversationItem>
)

data class ConversationItem(
    val id: String,
    val person_id: String,
    val name: String,
    val email: String,
    val initials: String,
    val last_message: String,
    val last_message_time: String?,
    val needs_reply: Boolean,
    val unread_count: Int,
    val status: String
)

data class MessagesResponse(
    val messages: List<MessageItem>
)

data class MessageItem(
    val id: String,
    val body: String,
    val direction: String,
    val status: String,
    val created_at: String,
    val sender_name: String
)

data class SendMessageRequest(
    val message: String
)

data class SendMessageResponse(
    val status: String,
    val message_id: String
)

data class ErrorResponse(
    val error: String
)

interface ApiService {

    // Authentication (Staff)
    @POST("api/mobile/login/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    // Authentication (Customer - returns is_staff flag)
    @POST("api/mobile/customer/login/")
    suspend fun customerLogin(@Body request: LoginRequest): Response<CustomerLoginResponse>

    // FCM Registration
    @POST("api/mobile/fcm/register/")
    suspend fun registerFCMDevice(
        @Header("Authorization") token: String,
        @Body request: FCMRegisterRequest
    ): Response<FCMRegisterResponse>

    @POST("api/mobile/fcm/unregister/")
    suspend fun unregisterFCMDevice(
        @Header("Authorization") token: String,
        @Body request: FCMRegisterRequest
    ): Response<FCMRegisterResponse>

    // Staff - Conversations
    @GET("api/mobile/conversations/")
    suspend fun getConversations(
        @Header("Authorization") token: String
    ): Response<ConversationsResponse>

    @GET("api/mobile/conversations/{conversation_id}/messages/")
    suspend fun getMessages(
        @Header("Authorization") token: String,
        @Path("conversation_id") conversationId: String
    ): Response<MessagesResponse>

    @POST("api/mobile/conversations/{conversation_id}/send/")
    suspend fun sendMessage(
        @Header("Authorization") token: String,
        @Path("conversation_id") conversationId: String,
        @Body request: SendMessageRequest
    ): Response<SendMessageResponse>

    // Version Check (No Auth - In-App Updates)
    @GET("api/mobile/version/check/")
    suspend fun checkVersion(
        @Query("platform") platform: String = "android",
        @Query("current_version") currentVersion: Int
    ): Response<VersionCheckResponse>

    // Customer Bookings
    @GET("api/mobile/customer/bookings/")
    suspend fun getBookings(
        @Header("Authorization") token: String
    ): Response<BookingsResponse>

    // Location Tracking
    @POST("api/mobile/location/")
    suspend fun submitLocation(
        @Header("Authorization") token: String,
        @Body request: LocationUpdateRequest
    ): Response<LocationUpdateResponse>

    @POST("api/mobile/location/batch/")
    suspend fun submitLocationBatch(
        @Header("Authorization") token: String,
        @Body request: LocationBatchRequest
    ): Response<LocationBatchResponse>

    // Location Settings
    @GET("api/mobile/location/settings/")
    suspend fun getLocationSettings(
        @Header("Authorization") token: String
    ): Response<LocationSettingsResponse>

    @PUT("api/mobile/location/settings/")
    suspend fun updateLocationSettings(
        @Header("Authorization") token: String,
        @Body request: LocationSettingsRequest
    ): Response<LocationSettingsResponse>
}
