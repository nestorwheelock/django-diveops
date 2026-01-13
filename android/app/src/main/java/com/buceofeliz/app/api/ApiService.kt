package com.buceofeliz.app.api

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

// Customer Profile
data class ProfileResponse(
    val person: PersonInfo,
    val experience: ExperienceInfo,
    val medical: MedicalInfo,
    val gear_sizing: GearSizing,
    val equipment_ownership: String
)

data class PersonInfo(
    val first_name: String,
    val last_name: String,
    val email: String
)

data class ExperienceInfo(
    val total_dives: Int,
    val highest_certification: String?
)

data class MedicalInfo(
    val clearance_valid_until: String?,
    val is_current: Boolean,
    val waiver_valid: Boolean
)

data class GearSizing(
    val weight_kg: String?,
    val height_cm: Int?,
    val wetsuit_size: String,
    val bcd_size: String,
    val fin_size: String,
    val mask_fit: String,
    val glove_size: String,
    val weight_required_kg: String?,
    val gear_notes: String
)

data class ProfileUpdateRequest(
    val weight_kg: String? = null,
    val height_cm: Int? = null,
    val wetsuit_size: String? = null,
    val bcd_size: String? = null,
    val fin_size: String? = null,
    val mask_fit: String? = null,
    val glove_size: String? = null,
    val weight_required_kg: String? = null,
    val gear_notes: String? = null,
    val equipment_ownership: String? = null
)

// Customer Certifications
data class CertificationsResponse(
    val certifications: List<CertificationItem>
)

data class CertificationItem(
    val id: String,
    val level_name: String,
    val agency_name: String,
    val card_number: String?,
    val issued_on: String?,
    val expires_on: String?,
    val is_verified: Boolean
)

// Customer Emergency Contacts
data class EmergencyContactsResponse(
    val contacts: List<EmergencyContactItem>
)

data class EmergencyContactItem(
    val id: String,
    val name: String,
    val relationship: String,
    val priority: Int
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

    // Customer Profile
    @GET("api/mobile/customer/profile/")
    suspend fun getProfile(
        @Header("Authorization") token: String
    ): Response<ProfileResponse>

    @PUT("api/mobile/customer/profile/")
    suspend fun updateProfile(
        @Header("Authorization") token: String,
        @Body request: ProfileUpdateRequest
    ): Response<ProfileResponse>

    // Customer Certifications
    @GET("api/mobile/customer/certifications/")
    suspend fun getCertifications(
        @Header("Authorization") token: String
    ): Response<CertificationsResponse>

    // Customer Emergency Contacts
    @GET("api/mobile/customer/emergency-contacts/")
    suspend fun getEmergencyContacts(
        @Header("Authorization") token: String
    ): Response<EmergencyContactsResponse>
}
