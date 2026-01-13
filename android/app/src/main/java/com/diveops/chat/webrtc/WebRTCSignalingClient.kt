package com.diveops.chat.webrtc

import android.util.Log
import com.diveops.chat.BuildConfig
import com.google.gson.Gson
import com.google.gson.JsonObject
import okhttp3.*
import java.util.concurrent.TimeUnit

class WebRTCSignalingClient(
    private val authToken: String,
    private val listener: SignalingListener
) {
    private var webSocket: WebSocket? = null
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var reconnectAttempts = 0
    private val maxReconnectAttempts = 5
    private var isConnected = false

    interface SignalingListener {
        fun onConnected(userId: String)
        fun onDisconnected()
        fun onIncomingCall(callerId: String, callType: String)
        fun onOffer(callerId: String, sdp: String)
        fun onAnswer(answererId: String, sdp: String)
        fun onIceCandidate(senderId: String, candidate: String)
        fun onHangup(endedBy: String)
        fun onRejected(rejectedBy: String)
        fun onUserOffline(userId: String)
        fun onError(message: String)
    }

    fun connect() {
        val baseUrl = BuildConfig.BASE_URL
        val wsProtocol = if (baseUrl.startsWith("https")) "wss" else "ws"
        val wsUrl = "$wsProtocol://${baseUrl.removePrefix("https://").removePrefix("http://")}/ws/call/"

        Log.d(TAG, "Connecting to WebSocket: $wsUrl")

        val request = Request.Builder()
            .url(wsUrl)
            .addHeader("Authorization", "Bearer $authToken")
            .build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d(TAG, "WebSocket connected")
                reconnectAttempts = 0
                isConnected = true
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "WebSocket message: $text")
                handleMessage(text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closing: $code - $reason")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed: $code - $reason")
                isConnected = false
                listener.onDisconnected()
                attemptReconnect()
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "WebSocket failure", t)
                isConnected = false
                listener.onError(t.message ?: "Connection failed")
                listener.onDisconnected()
                attemptReconnect()
            }
        })
    }

    private fun attemptReconnect() {
        if (reconnectAttempts < maxReconnectAttempts) {
            reconnectAttempts++
            val delay = minOf(1000L * (1 shl reconnectAttempts), 30000L)
            Log.d(TAG, "Reconnecting in ${delay}ms (attempt $reconnectAttempts)")
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                connect()
            }, delay)
        }
    }

    private fun handleMessage(text: String) {
        try {
            val json = gson.fromJson(text, JsonObject::class.java)
            val type = json.get("type")?.asString ?: return

            when (type) {
                "connected" -> {
                    val userId = json.get("user_id")?.asString ?: ""
                    listener.onConnected(userId)
                }
                "incoming_call" -> {
                    val callerId = json.get("caller_id")?.asString ?: ""
                    val callType = json.get("call_type")?.asString ?: "video"
                    listener.onIncomingCall(callerId, callType)
                }
                "offer" -> {
                    val callerId = json.get("caller_id")?.asString ?: ""
                    val sdp = json.get("sdp")?.toString() ?: ""
                    listener.onOffer(callerId, sdp)
                }
                "answer" -> {
                    val answererId = json.get("answerer_id")?.asString ?: ""
                    val sdp = json.get("sdp")?.toString() ?: ""
                    listener.onAnswer(answererId, sdp)
                }
                "ice_candidate" -> {
                    val senderId = json.get("sender_id")?.asString ?: ""
                    val candidate = json.get("candidate")?.toString() ?: ""
                    listener.onIceCandidate(senderId, candidate)
                }
                "hangup" -> {
                    val endedBy = json.get("ended_by")?.asString ?: ""
                    listener.onHangup(endedBy)
                }
                "rejected" -> {
                    val rejectedBy = json.get("rejected_by")?.asString ?: ""
                    listener.onRejected(rejectedBy)
                }
                "user_offline" -> {
                    val userId = json.get("target_user_id")?.asString ?: ""
                    listener.onUserOffline(userId)
                }
                "error" -> {
                    val message = json.get("message")?.asString ?: "Unknown error"
                    listener.onError(message)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing message", e)
        }
    }

    fun sendCall(targetUserId: String, callType: String = "video") {
        val message = JsonObject().apply {
            addProperty("type", "call")
            addProperty("target_user_id", targetUserId)
            addProperty("call_type", callType)
        }
        send(message)
    }

    fun sendOffer(targetUserId: String, sdp: String) {
        val message = JsonObject().apply {
            addProperty("type", "offer")
            addProperty("target_user_id", targetUserId)
            add("sdp", gson.fromJson(sdp, JsonObject::class.java))
        }
        send(message)
    }

    fun sendAnswer(targetUserId: String, sdp: String) {
        val message = JsonObject().apply {
            addProperty("type", "answer")
            addProperty("target_user_id", targetUserId)
            add("sdp", gson.fromJson(sdp, JsonObject::class.java))
        }
        send(message)
    }

    fun sendIceCandidate(targetUserId: String, candidate: String) {
        val message = JsonObject().apply {
            addProperty("type", "ice_candidate")
            addProperty("target_user_id", targetUserId)
            add("candidate", gson.fromJson(candidate, JsonObject::class.java))
        }
        send(message)
    }

    fun sendHangup(targetUserId: String) {
        val message = JsonObject().apply {
            addProperty("type", "hangup")
            addProperty("target_user_id", targetUserId)
        }
        send(message)
    }

    fun sendReject(targetUserId: String) {
        val message = JsonObject().apply {
            addProperty("type", "reject")
            addProperty("target_user_id", targetUserId)
        }
        send(message)
    }

    private fun send(message: JsonObject) {
        val text = gson.toJson(message)
        Log.d(TAG, "Sending: $text")
        webSocket?.send(text)
    }

    fun disconnect() {
        reconnectAttempts = maxReconnectAttempts // Prevent reconnection
        webSocket?.close(1000, "User disconnected")
        webSocket = null
        isConnected = false
    }

    fun isConnected(): Boolean = isConnected

    companion object {
        private const val TAG = "WebRTCSignaling"
    }
}
