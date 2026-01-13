/**
 * WebRTC Client for DiveOps Video/Audio Calling
 *
 * Handles WebSocket signaling and WebRTC peer connections for
 * staff-to-customer and staff-to-staff video/audio calls.
 */
class DiveOpsWebRTC {
    constructor(options = {}) {
        this.userId = options.userId;
        this.socket = null;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.currentCallTarget = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 5;

        // ICE servers configuration (STUN/TURN)
        this.iceServers = options.iceServers || [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
        ];

        // Callbacks for UI integration
        this.onConnected = options.onConnected || (() => {});
        this.onDisconnected = options.onDisconnected || (() => {});
        this.onIncomingCall = options.onIncomingCall || (() => {});
        this.onCallAccepted = options.onCallAccepted || (() => {});
        this.onCallRejected = options.onCallRejected || (() => {});
        this.onCallEnded = options.onCallEnded || (() => {});
        this.onRemoteStream = options.onRemoteStream || (() => {});
        this.onLocalStream = options.onLocalStream || (() => {});
        this.onError = options.onError || ((error) => console.error('WebRTC Error:', error));
        this.onUserOffline = options.onUserOffline || (() => {});

        // State
        this.isConnected = false;
        this.isInCall = false;
    }

    /**
     * Connect to the WebSocket signaling server
     */
    connect() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/call/`;

        console.log('[WebRTC] Connecting to signaling server:', wsUrl);

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('[WebRTC] WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this._handleSignalingMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('[WebRTC] WebSocket closed:', event.code);
            this.isConnected = false;
            this.onDisconnected();

            // Auto-reconnect if not intentionally closed
            if (!document.hidden && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`[WebRTC] Reconnecting in ${delay}ms...`);
                setTimeout(() => this.connect(), delay);
            }
        };

        this.socket.onerror = (error) => {
            console.error('[WebRTC] WebSocket error:', error);
            this.onError(error);
        };
    }

    /**
     * Disconnect from signaling server and cleanup
     */
    disconnect() {
        this._cleanup();
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    /**
     * Handle incoming signaling messages
     */
    _handleSignalingMessage(data) {
        console.log('[WebRTC] Received:', data.type, data);

        switch (data.type) {
            case 'connected':
                this.userId = data.user_id;
                this.isConnected = true;
                this.onConnected(data.user_id);
                break;

            case 'incoming_call':
                this._handleIncomingCall(data);
                break;

            case 'offer':
                this._handleOffer(data);
                break;

            case 'answer':
                this._handleAnswer(data);
                break;

            case 'ice_candidate':
                this._handleIceCandidate(data);
                break;

            case 'hangup':
                this._handleHangup(data);
                break;

            case 'rejected':
                this._handleRejected(data);
                break;

            case 'user_offline':
                this.onUserOffline(data.target_user_id);
                break;

            case 'error':
                this.onError(new Error(data.message));
                break;

            default:
                console.warn('[WebRTC] Unknown message type:', data.type);
        }
    }

    /**
     * Initiate a call to another user
     */
    async call(targetUserId, callType = 'video') {
        if (this.isInCall) {
            this.onError(new Error('Already in a call'));
            return;
        }

        console.log(`[WebRTC] Initiating ${callType} call to user ${targetUserId}`);
        this.currentCallTarget = targetUserId;

        try {
            // Get local media stream
            await this._getLocalStream(callType);

            // Create peer connection
            this._createPeerConnection();

            // Create and send offer
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);

            // Send call initiation
            this._send({
                type: 'call',
                target_user_id: targetUserId,
                call_type: callType,
            });

            // Send SDP offer
            this._send({
                type: 'offer',
                target_user_id: targetUserId,
                sdp: offer,
            });

            this.isInCall = true;
        } catch (error) {
            console.error('[WebRTC] Failed to initiate call:', error);
            this.onError(error);
            this._cleanup();
        }
    }

    /**
     * Answer an incoming call
     */
    async answer(callerId, callType = 'video') {
        console.log(`[WebRTC] Answering call from user ${callerId}`);
        this.currentCallTarget = callerId;

        try {
            // Get local media stream
            await this._getLocalStream(callType);

            // Create peer connection if not exists
            if (!this.peerConnection) {
                this._createPeerConnection();
            }

            // Create and send answer
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);

            this._send({
                type: 'answer',
                target_user_id: callerId,
                sdp: answer,
            });

            this.isInCall = true;
            this.onCallAccepted({ callerId });
        } catch (error) {
            console.error('[WebRTC] Failed to answer call:', error);
            this.onError(error);
            this._cleanup();
        }
    }

    /**
     * Reject an incoming call
     */
    reject(callerId) {
        console.log(`[WebRTC] Rejecting call from user ${callerId}`);

        this._send({
            type: 'reject',
            target_user_id: callerId,
        });

        this._cleanup();
    }

    /**
     * Hang up current call
     */
    hangup() {
        if (!this.currentCallTarget) {
            return;
        }

        console.log(`[WebRTC] Hanging up call with user ${this.currentCallTarget}`);

        this._send({
            type: 'hangup',
            target_user_id: this.currentCallTarget,
        });

        this._cleanup();
        this.onCallEnded({ endedBy: 'self' });
    }

    /**
     * Toggle local video on/off
     */
    toggleVideo() {
        if (this.localStream) {
            const videoTracks = this.localStream.getVideoTracks();
            videoTracks.forEach(track => {
                track.enabled = !track.enabled;
            });
            return videoTracks.length > 0 ? videoTracks[0].enabled : false;
        }
        return false;
    }

    /**
     * Toggle local audio on/off
     */
    toggleAudio() {
        if (this.localStream) {
            const audioTracks = this.localStream.getAudioTracks();
            audioTracks.forEach(track => {
                track.enabled = !track.enabled;
            });
            return audioTracks.length > 0 ? audioTracks[0].enabled : false;
        }
        return false;
    }

    /**
     * Get local media stream
     */
    async _getLocalStream(callType) {
        const constraints = {
            audio: true,
            video: callType === 'video' ? {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            } : false
        };

        try {
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.onLocalStream(this.localStream);
            console.log('[WebRTC] Got local stream');
        } catch (error) {
            console.error('[WebRTC] Failed to get local stream:', error);
            throw error;
        }
    }

    /**
     * Create RTCPeerConnection
     */
    _createPeerConnection() {
        const config = {
            iceServers: this.iceServers,
        };

        this.peerConnection = new RTCPeerConnection(config);

        // Add local tracks to peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
        }

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate && this.currentCallTarget) {
                this._send({
                    type: 'ice_candidate',
                    target_user_id: this.currentCallTarget,
                    candidate: event.candidate,
                });
            }
        };

        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            console.log('[WebRTC] Received remote track');
            this.remoteStream = event.streams[0];
            this.onRemoteStream(this.remoteStream);
        };

        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('[WebRTC] Connection state:', this.peerConnection.connectionState);

            if (this.peerConnection.connectionState === 'failed' ||
                this.peerConnection.connectionState === 'disconnected') {
                this._cleanup();
                this.onCallEnded({ reason: 'connection_lost' });
            }
        };

        // Handle ICE connection state
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('[WebRTC] ICE connection state:', this.peerConnection.iceConnectionState);
        };

        console.log('[WebRTC] Created peer connection');
    }

    /**
     * Handle incoming call notification
     */
    _handleIncomingCall(data) {
        console.log(`[WebRTC] Incoming ${data.call_type} call from user ${data.caller_id}`);
        this.onIncomingCall({
            callerId: data.caller_id,
            callType: data.call_type,
        });
    }

    /**
     * Handle incoming SDP offer
     */
    async _handleOffer(data) {
        console.log('[WebRTC] Received offer from', data.caller_id);
        this.currentCallTarget = data.caller_id;

        try {
            // Create peer connection if not exists
            if (!this.peerConnection) {
                this._createPeerConnection();
            }

            // Set remote description
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            console.log('[WebRTC] Set remote description');
        } catch (error) {
            console.error('[WebRTC] Failed to handle offer:', error);
            this.onError(error);
        }
    }

    /**
     * Handle incoming SDP answer
     */
    async _handleAnswer(data) {
        console.log('[WebRTC] Received answer from', data.answerer_id);

        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(data.sdp));
            console.log('[WebRTC] Set remote description (answer)');
            this.onCallAccepted({ answererId: data.answerer_id });
        } catch (error) {
            console.error('[WebRTC] Failed to handle answer:', error);
            this.onError(error);
        }
    }

    /**
     * Handle incoming ICE candidate
     */
    async _handleIceCandidate(data) {
        console.log('[WebRTC] Received ICE candidate from', data.sender_id);

        try {
            if (this.peerConnection && data.candidate) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
                console.log('[WebRTC] Added ICE candidate');
            }
        } catch (error) {
            console.error('[WebRTC] Failed to add ICE candidate:', error);
        }
    }

    /**
     * Handle hangup from remote peer
     */
    _handleHangup(data) {
        console.log('[WebRTC] Remote user hung up:', data.ended_by);
        this._cleanup();
        this.onCallEnded({ endedBy: data.ended_by });
    }

    /**
     * Handle call rejection
     */
    _handleRejected(data) {
        console.log('[WebRTC] Call rejected by:', data.rejected_by);
        this._cleanup();
        this.onCallRejected({ rejectedBy: data.rejected_by });
    }

    /**
     * Send message through WebSocket
     */
    _send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
            console.log('[WebRTC] Sent:', data.type);
        } else {
            console.error('[WebRTC] Cannot send - socket not open');
        }
    }

    /**
     * Cleanup resources
     */
    _cleanup() {
        console.log('[WebRTC] Cleaning up');

        // Stop local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        this.remoteStream = null;
        this.currentCallTarget = null;
        this.isInCall = false;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DiveOpsWebRTC;
}
