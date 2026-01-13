package com.diveops.chat.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.diveops.chat.api.ApiClient
import com.diveops.chat.api.CustomerUserInfo
import com.diveops.chat.api.FCMRegisterRequest
import com.diveops.chat.api.LoginRequest
import com.diveops.chat.api.UserInfo
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "auth")

class AuthRepository(private val context: Context) {

    private object PreferencesKeys {
        val AUTH_TOKEN = stringPreferencesKey("auth_token")
        val USER_EMAIL = stringPreferencesKey("user_email")
        val USER_FIRST_NAME = stringPreferencesKey("user_first_name")
        val USER_LAST_NAME = stringPreferencesKey("user_last_name")
        val USER_PERSON_ID = stringPreferencesKey("user_person_id")
        val USER_IS_STAFF = booleanPreferencesKey("user_is_staff")
    }

    val authToken: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[PreferencesKeys.AUTH_TOKEN]
    }

    val isStaff: Flow<Boolean> = context.dataStore.data.map { preferences ->
        preferences[PreferencesKeys.USER_IS_STAFF] ?: false
    }

    val personId: Flow<String?> = context.dataStore.data.map { preferences ->
        preferences[PreferencesKeys.USER_PERSON_ID]
    }

    val userInfo: Flow<UserInfo?> = context.dataStore.data.map { preferences ->
        val email = preferences[PreferencesKeys.USER_EMAIL]
        val firstName = preferences[PreferencesKeys.USER_FIRST_NAME]
        val lastName = preferences[PreferencesKeys.USER_LAST_NAME]

        if (email != null) {
            UserInfo(
                id = 0,
                email = email,
                first_name = firstName ?: "",
                last_name = lastName ?: ""
            )
        } else {
            null
        }
    }

    suspend fun getAuthToken(): String? {
        return context.dataStore.data.first()[PreferencesKeys.AUTH_TOKEN]
    }

    suspend fun getIsStaff(): Boolean {
        return context.dataStore.data.first()[PreferencesKeys.USER_IS_STAFF] ?: false
    }

    fun getBearerToken(): Flow<String?> = authToken.map { token ->
        token?.let { "Bearer $it" }
    }

    suspend fun login(email: String, password: String): Result<CustomerUserInfo> {
        return try {
            val response = ApiClient.apiService.customerLogin(LoginRequest(email, password))

            if (response.isSuccessful && response.body() != null) {
                val loginResponse = response.body()!!

                // Save auth token and user info
                context.dataStore.edit { preferences ->
                    preferences[PreferencesKeys.AUTH_TOKEN] = loginResponse.token
                    preferences[PreferencesKeys.USER_EMAIL] = loginResponse.user.email
                    preferences[PreferencesKeys.USER_FIRST_NAME] = loginResponse.user.first_name
                    preferences[PreferencesKeys.USER_LAST_NAME] = loginResponse.user.last_name
                    preferences[PreferencesKeys.USER_PERSON_ID] = loginResponse.user.person_id
                    preferences[PreferencesKeys.USER_IS_STAFF] = loginResponse.user.is_staff
                }

                Result.success(loginResponse.user)
            } else {
                val errorBody = response.errorBody()?.string() ?: "Login failed"
                Result.failure(Exception(errorBody))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout() {
        context.dataStore.edit { preferences ->
            preferences.remove(PreferencesKeys.AUTH_TOKEN)
            preferences.remove(PreferencesKeys.USER_EMAIL)
            preferences.remove(PreferencesKeys.USER_FIRST_NAME)
            preferences.remove(PreferencesKeys.USER_LAST_NAME)
            preferences.remove(PreferencesKeys.USER_PERSON_ID)
            preferences.remove(PreferencesKeys.USER_IS_STAFF)
        }
    }

    suspend fun registerFCMToken(fcmToken: String, deviceId: String, deviceName: String): Result<Unit> {
        return try {
            val authToken = getAuthToken() ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.registerFCMDevice(
                token = "Bearer $authToken",
                request = FCMRegisterRequest(
                    registration_id = fcmToken,
                    platform = "android",
                    device_id = deviceId,
                    device_name = deviceName,
                    app_version = "1.0.0"
                )
            )

            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Failed to register FCM token"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun unregisterFCMToken(fcmToken: String): Result<Unit> {
        return try {
            val authToken = getAuthToken() ?: return Result.failure(Exception("Not authenticated"))

            val response = ApiClient.apiService.unregisterFCMDevice(
                token = "Bearer $authToken",
                request = FCMRegisterRequest(registration_id = fcmToken)
            )

            if (response.isSuccessful) {
                Result.success(Unit)
            } else {
                Result.failure(Exception("Failed to unregister FCM token"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
