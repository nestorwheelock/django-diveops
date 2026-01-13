package com.diveops.chat.webrtc

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import org.webrtc.*

class WebRTCManager(
    private val context: Context,
    private val signalingClient: WebRTCSignalingClient,
    private val listener: WebRTCListener
) {
    private var peerConnectionFactory: PeerConnectionFactory? = null
    private var peerConnection: PeerConnection? = null
    private var localVideoTrack: VideoTrack? = null
    private var localAudioTrack: AudioTrack? = null
    private var videoCapturer: CameraVideoCapturer? = null
    private var surfaceTextureHelper: SurfaceTextureHelper? = null
    private var localVideoSource: VideoSource? = null
    private var audioSource: AudioSource? = null

    private var targetUserId: String? = null
    private var isInitiator = false
    private var isVideoEnabled = true
    private var isAudioEnabled = true

    private val gson = Gson()
    private val eglBase = EglBase.create()

    private val iceServers = listOf(
        PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer(),
        PeerConnection.IceServer.builder("stun:stun1.l.google.com:19302").createIceServer()
    )

    interface WebRTCListener {
        fun onLocalStream(videoTrack: VideoTrack?)
        fun onRemoteStream(videoTrack: VideoTrack?)
        fun onCallConnected()
        fun onCallEnded(reason: String)
        fun onError(message: String)
    }

    init {
        initializePeerConnectionFactory()
    }

    private fun initializePeerConnectionFactory() {
        val options = PeerConnectionFactory.InitializationOptions.builder(context)
            .setEnableInternalTracer(true)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(options)

        val encoderFactory = DefaultVideoEncoderFactory(eglBase.eglBaseContext, true, true)
        val decoderFactory = DefaultVideoDecoderFactory(eglBase.eglBaseContext)

        peerConnectionFactory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(encoderFactory)
            .setVideoDecoderFactory(decoderFactory)
            .createPeerConnectionFactory()
    }

    fun getEglBase(): EglBase = eglBase

    fun startCall(targetUserId: String, callType: String = "video") {
        this.targetUserId = targetUserId
        this.isInitiator = true

        Log.d(TAG, "Starting call to $targetUserId")

        // Signal the call initiation
        signalingClient.sendCall(targetUserId, callType)

        // Start local media
        startLocalMedia(callType == "video")

        // Create peer connection
        createPeerConnection()

        // Create and send offer
        createOffer()
    }

    fun answerCall(callerId: String, callType: String = "video") {
        this.targetUserId = callerId
        this.isInitiator = false

        Log.d(TAG, "Answering call from $callerId")

        // Start local media
        startLocalMedia(callType == "video")

        // Peer connection should already exist from handleOffer
        if (peerConnection == null) {
            createPeerConnection()
        }

        // Create and send answer
        createAnswer()
    }

    fun handleOffer(callerId: String, sdpJson: String) {
        this.targetUserId = callerId
        this.isInitiator = false

        Log.d(TAG, "Handling offer from $callerId")

        if (peerConnection == null) {
            createPeerConnection()
        }

        try {
            val sdpObject = gson.fromJson(sdpJson, JsonObject::class.java)
            val type = sdpObject.get("type")?.asString ?: "offer"
            val sdp = sdpObject.get("sdp")?.asString ?: ""

            val sessionDescription = SessionDescription(
                SessionDescription.Type.fromCanonicalForm(type),
                sdp
            )

            peerConnection?.setRemoteDescription(object : SdpObserver {
                override fun onSetSuccess() {
                    Log.d(TAG, "Remote description set successfully")
                }
                override fun onSetFailure(error: String?) {
                    Log.e(TAG, "Failed to set remote description: $error")
                }
                override fun onCreateSuccess(sdp: SessionDescription?) {}
                override fun onCreateFailure(error: String?) {}
            }, sessionDescription)
        } catch (e: Exception) {
            Log.e(TAG, "Error handling offer", e)
        }
    }

    fun handleAnswer(answererId: String, sdpJson: String) {
        Log.d(TAG, "Handling answer from $answererId")

        try {
            val sdpObject = gson.fromJson(sdpJson, JsonObject::class.java)
            val type = sdpObject.get("type")?.asString ?: "answer"
            val sdp = sdpObject.get("sdp")?.asString ?: ""

            val sessionDescription = SessionDescription(
                SessionDescription.Type.fromCanonicalForm(type),
                sdp
            )

            peerConnection?.setRemoteDescription(object : SdpObserver {
                override fun onSetSuccess() {
                    Log.d(TAG, "Remote description (answer) set successfully")
                    listener.onCallConnected()
                }
                override fun onSetFailure(error: String?) {
                    Log.e(TAG, "Failed to set remote description: $error")
                }
                override fun onCreateSuccess(sdp: SessionDescription?) {}
                override fun onCreateFailure(error: String?) {}
            }, sessionDescription)
        } catch (e: Exception) {
            Log.e(TAG, "Error handling answer", e)
        }
    }

    fun handleIceCandidate(senderId: String, candidateJson: String) {
        Log.d(TAG, "Handling ICE candidate from $senderId")

        try {
            val candidateObject = gson.fromJson(candidateJson, JsonObject::class.java)
            val sdpMid = candidateObject.get("sdpMid")?.asString ?: ""
            val sdpMLineIndex = candidateObject.get("sdpMLineIndex")?.asInt ?: 0
            val candidate = candidateObject.get("candidate")?.asString ?: ""

            val iceCandidate = IceCandidate(sdpMid, sdpMLineIndex, candidate)
            peerConnection?.addIceCandidate(iceCandidate)
        } catch (e: Exception) {
            Log.e(TAG, "Error handling ICE candidate", e)
        }
    }

    private fun startLocalMedia(withVideo: Boolean) {
        Log.d(TAG, "Starting local media, video: $withVideo")

        // Create audio track
        val audioConstraints = MediaConstraints()
        audioSource = peerConnectionFactory?.createAudioSource(audioConstraints)
        localAudioTrack = peerConnectionFactory?.createAudioTrack("audio0", audioSource)

        if (withVideo) {
            // Create video track
            videoCapturer = createCameraCapturer()
            videoCapturer?.let { capturer ->
                surfaceTextureHelper = SurfaceTextureHelper.create("CaptureThread", eglBase.eglBaseContext)
                localVideoSource = peerConnectionFactory?.createVideoSource(capturer.isScreencast)
                capturer.initialize(surfaceTextureHelper, context, localVideoSource?.capturerObserver)
                capturer.startCapture(1280, 720, 30)

                localVideoTrack = peerConnectionFactory?.createVideoTrack("video0", localVideoSource)
                listener.onLocalStream(localVideoTrack)
            }
        }
    }

    private fun createCameraCapturer(): CameraVideoCapturer? {
        val enumerator = Camera2Enumerator(context)

        // Try front camera first
        for (deviceName in enumerator.deviceNames) {
            if (enumerator.isFrontFacing(deviceName)) {
                val capturer = enumerator.createCapturer(deviceName, null)
                if (capturer != null) {
                    return capturer
                }
            }
        }

        // Fall back to back camera
        for (deviceName in enumerator.deviceNames) {
            if (!enumerator.isFrontFacing(deviceName)) {
                val capturer = enumerator.createCapturer(deviceName, null)
                if (capturer != null) {
                    return capturer
                }
            }
        }

        return null
    }

    private fun createPeerConnection() {
        val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
        }

        peerConnection = peerConnectionFactory?.createPeerConnection(
            rtcConfig,
            object : PeerConnection.Observer {
                override fun onIceCandidate(candidate: IceCandidate?) {
                    candidate?.let {
                        Log.d(TAG, "ICE candidate: ${it.sdp}")
                        val candidateJson = JsonObject().apply {
                            addProperty("candidate", it.sdp)
                            addProperty("sdpMid", it.sdpMid)
                            addProperty("sdpMLineIndex", it.sdpMLineIndex)
                        }
                        targetUserId?.let { target ->
                            signalingClient.sendIceCandidate(target, gson.toJson(candidateJson))
                        }
                    }
                }

                override fun onTrack(transceiver: RtpTransceiver?) {
                    Log.d(TAG, "onTrack: ${transceiver?.receiver?.track()?.kind()}")
                    transceiver?.receiver?.track()?.let { track ->
                        if (track.kind() == MediaStreamTrack.VIDEO_TRACK_KIND) {
                            val videoTrack = track as VideoTrack
                            listener.onRemoteStream(videoTrack)
                        }
                    }
                }

                override fun onConnectionChange(newState: PeerConnection.PeerConnectionState?) {
                    Log.d(TAG, "Connection state: $newState")
                    when (newState) {
                        PeerConnection.PeerConnectionState.CONNECTED -> {
                            listener.onCallConnected()
                        }
                        PeerConnection.PeerConnectionState.DISCONNECTED,
                        PeerConnection.PeerConnectionState.FAILED -> {
                            listener.onCallEnded("Connection lost")
                        }
                        else -> {}
                    }
                }

                override fun onSignalingChange(state: PeerConnection.SignalingState?) {
                    Log.d(TAG, "Signaling state: $state")
                }

                override fun onIceConnectionChange(state: PeerConnection.IceConnectionState?) {
                    Log.d(TAG, "ICE connection state: $state")
                }

                override fun onIceConnectionReceivingChange(receiving: Boolean) {}
                override fun onIceGatheringChange(state: PeerConnection.IceGatheringState?) {}
                override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>?) {}
                override fun onAddStream(stream: MediaStream?) {}
                override fun onRemoveStream(stream: MediaStream?) {}
                override fun onDataChannel(channel: DataChannel?) {}
                override fun onRenegotiationNeeded() {}
                override fun onAddTrack(receiver: RtpReceiver?, streams: Array<out MediaStream>?) {}
            }
        )

        // Add local tracks to peer connection
        localAudioTrack?.let {
            peerConnection?.addTrack(it, listOf("stream0"))
        }
        localVideoTrack?.let {
            peerConnection?.addTrack(it, listOf("stream0"))
        }
    }

    private fun createOffer() {
        val constraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "true"))
        }

        peerConnection?.createOffer(object : SdpObserver {
            override fun onCreateSuccess(sdp: SessionDescription?) {
                Log.d(TAG, "Offer created")
                sdp?.let {
                    peerConnection?.setLocalDescription(object : SdpObserver {
                        override fun onSetSuccess() {
                            Log.d(TAG, "Local description set")
                            val sdpJson = JsonObject().apply {
                                addProperty("type", it.type.canonicalForm())
                                addProperty("sdp", it.description)
                            }
                            targetUserId?.let { target ->
                                signalingClient.sendOffer(target, gson.toJson(sdpJson))
                            }
                        }
                        override fun onSetFailure(error: String?) {
                            Log.e(TAG, "Failed to set local description: $error")
                        }
                        override fun onCreateSuccess(sdp: SessionDescription?) {}
                        override fun onCreateFailure(error: String?) {}
                    }, it)
                }
            }
            override fun onCreateFailure(error: String?) {
                Log.e(TAG, "Failed to create offer: $error")
                listener.onError("Failed to create offer: $error")
            }
            override fun onSetSuccess() {}
            override fun onSetFailure(error: String?) {}
        }, constraints)
    }

    private fun createAnswer() {
        val constraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "true"))
        }

        peerConnection?.createAnswer(object : SdpObserver {
            override fun onCreateSuccess(sdp: SessionDescription?) {
                Log.d(TAG, "Answer created")
                sdp?.let {
                    peerConnection?.setLocalDescription(object : SdpObserver {
                        override fun onSetSuccess() {
                            Log.d(TAG, "Local description (answer) set")
                            val sdpJson = JsonObject().apply {
                                addProperty("type", it.type.canonicalForm())
                                addProperty("sdp", it.description)
                            }
                            targetUserId?.let { target ->
                                signalingClient.sendAnswer(target, gson.toJson(sdpJson))
                            }
                            listener.onCallConnected()
                        }
                        override fun onSetFailure(error: String?) {
                            Log.e(TAG, "Failed to set local description: $error")
                        }
                        override fun onCreateSuccess(sdp: SessionDescription?) {}
                        override fun onCreateFailure(error: String?) {}
                    }, it)
                }
            }
            override fun onCreateFailure(error: String?) {
                Log.e(TAG, "Failed to create answer: $error")
                listener.onError("Failed to create answer: $error")
            }
            override fun onSetSuccess() {}
            override fun onSetFailure(error: String?) {}
        }, constraints)
    }

    fun toggleVideo(): Boolean {
        isVideoEnabled = !isVideoEnabled
        localVideoTrack?.setEnabled(isVideoEnabled)
        return isVideoEnabled
    }

    fun toggleAudio(): Boolean {
        isAudioEnabled = !isAudioEnabled
        localAudioTrack?.setEnabled(isAudioEnabled)
        return isAudioEnabled
    }

    fun switchCamera() {
        videoCapturer?.switchCamera(null)
    }

    fun hangup() {
        targetUserId?.let {
            signalingClient.sendHangup(it)
        }
        cleanup()
        listener.onCallEnded("Call ended")
    }

    fun reject() {
        targetUserId?.let {
            signalingClient.sendReject(it)
        }
        cleanup()
    }

    fun cleanup() {
        Log.d(TAG, "Cleaning up WebRTC resources")

        videoCapturer?.stopCapture()
        videoCapturer?.dispose()
        videoCapturer = null

        localVideoTrack?.dispose()
        localVideoTrack = null

        localAudioTrack?.dispose()
        localAudioTrack = null

        localVideoSource?.dispose()
        localVideoSource = null

        audioSource?.dispose()
        audioSource = null

        surfaceTextureHelper?.dispose()
        surfaceTextureHelper = null

        peerConnection?.close()
        peerConnection = null

        targetUserId = null
        isInitiator = false
    }

    fun release() {
        cleanup()
        peerConnectionFactory?.dispose()
        peerConnectionFactory = null
        eglBase.release()
    }

    companion object {
        private const val TAG = "WebRTCManager"
    }
}
