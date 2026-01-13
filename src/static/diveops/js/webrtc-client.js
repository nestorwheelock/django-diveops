/**
 * DiveOps WebRTC Client
 * Handles peer-to-peer video/audio calls via WebSocket signaling
 */
class DiveOpsWebRTC {
    constructor(options = {}) {
        this.options = options;
        this.socket = null;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteStream = null;
        this.currentUserId = null;
        this.targetUserId = null;
        this.isVideoEnabled = true;
        this.isAudioEnabled = true;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        this.iceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' }
        ];
    }

    connect() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/call/`;

        console.log('[WebRTC] Connecting to', wsUrl);

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('[WebRTC] WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.socket.onclose = (event) => {
            console.log('[WebRTC] WebSocket closed:', event.code);
            this.currentUserId = null;

            if (this.options.onDisconnected) {
                this.options.onDisconnected();
            }

            // Attempt reconnection
            if (!document.hidden && this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
                console.log(`[WebRTC] Reconnecting in ${delay}ms`);
                setTimeout(() => this.connect(), delay);
            }
        };

        this.socket.onerror = (error) => {
            console.error('[WebRTC] WebSocket error:', error);
            if (this.options.onError) {
                this.options.onError({ message: 'WebSocket connection error' });
            }
        };
    }

    disconnect() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    handleMessage(data) {
        console.log('[WebRTC] Received:', data.type);

        switch (data.type) {
            case 'connected':
                this.currentUserId = data.user_id;
                if (this.options.onConnected) {
                    this.options.onConnected(data.user_id);
                }
                break;

            case 'call':
                if (this.options.onIncomingCall) {
                    this.options.onIncomingCall({
                        callerId: data.caller_id,
                        callType: data.call_type
                    });
                }
                break;

            case 'offer':
                this.handleOffer(data.caller_id, data.sdp);
                break;

            case 'answer':
                this.handleAnswer(data.answerer_id, data.sdp);
                break;

            case 'ice_candidate':
                this.handleIceCandidate(data.sender_id, data.candidate);
                break;

            case 'hangup':
                this.handleHangup(data.ended_by);
                break;

            case 'reject':
                if (this.options.onCallRejected) {
                    this.options.onCallRejected({ rejectedBy: data.rejected_by });
                }
                this.cleanup();
                break;

            case 'user_offline':
                if (this.options.onUserOffline) {
                    this.options.onUserOffline(data.user_id);
                }
                break;

            case 'error':
                console.error('[WebRTC] Server error:', data.message);
                if (this.options.onError) {
                    this.options.onError({ message: data.message });
                }
                break;
        }
    }

    async call(targetUserId, callType = 'video') {
        this.targetUserId = targetUserId;

        try {
            // Get user media
            await this.startLocalMedia(callType === 'video');

            // Send call notification
            this.send({
                type: 'call',
                target_user_id: targetUserId,
                call_type: callType
            });

            // Create peer connection and offer
            this.createPeerConnection();
            await this.createOffer();

        } catch (error) {
            console.error('[WebRTC] Call error:', error);
            if (this.options.onError) {
                this.options.onError({ message: error.message });
            }
        }
    }

    async answer(callerId, callType = 'video') {
        this.targetUserId = callerId;

        try {
            // Get user media
            await this.startLocalMedia(callType === 'video');

            // Peer connection should already exist from handleOffer
            if (!this.peerConnection) {
                this.createPeerConnection();
            }

            // Create and send answer
            await this.createAnswer();

        } catch (error) {
            console.error('[WebRTC] Answer error:', error);
            if (this.options.onError) {
                this.options.onError({ message: error.message });
            }
        }
    }

    reject(callerId) {
        this.send({
            type: 'reject',
            target_user_id: callerId
        });
    }

    hangup() {
        if (this.targetUserId) {
            this.send({
                type: 'hangup',
                target_user_id: this.targetUserId
            });
        }

        if (this.options.onCallEnded) {
            this.options.onCallEnded({ endedBy: 'self' });
        }

        this.cleanup();
    }

    async startLocalMedia(withVideo = true) {
        const constraints = {
            audio: true,
            video: withVideo ? {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            } : false
        };

        try {
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);

            if (this.options.onLocalStream) {
                this.options.onLocalStream(this.localStream);
            }

        } catch (error) {
            console.error('[WebRTC] getUserMedia error:', error);
            throw new Error('Could not access camera/microphone');
        }
    }

    createPeerConnection() {
        const config = {
            iceServers: this.iceServers,
            sdpSemantics: 'unified-plan'
        };

        this.peerConnection = new RTCPeerConnection(config);

        // Add local tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });
        }

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.send({
                    type: 'ice_candidate',
                    target_user_id: this.targetUserId,
                    candidate: JSON.stringify({
                        candidate: event.candidate.candidate,
                        sdpMid: event.candidate.sdpMid,
                        sdpMLineIndex: event.candidate.sdpMLineIndex
                    })
                });
            }
        };

        // Handle incoming tracks
        this.peerConnection.ontrack = (event) => {
            console.log('[WebRTC] Remote track received:', event.track.kind);

            if (event.streams && event.streams[0]) {
                this.remoteStream = event.streams[0];

                if (this.options.onRemoteStream) {
                    this.options.onRemoteStream(this.remoteStream);
                }
            }
        };

        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('[WebRTC] Connection state:', this.peerConnection.connectionState);

            switch (this.peerConnection.connectionState) {
                case 'connected':
                    if (this.options.onCallAccepted) {
                        this.options.onCallAccepted();
                    }
                    break;

                case 'disconnected':
                case 'failed':
                    if (this.options.onCallEnded) {
                        this.options.onCallEnded({ reason: 'connection_lost' });
                    }
                    this.cleanup();
                    break;
            }
        };

        // Handle ICE connection state
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('[WebRTC] ICE state:', this.peerConnection.iceConnectionState);
        };
    }

    async createOffer() {
        const offerOptions = {
            offerToReceiveAudio: true,
            offerToReceiveVideo: true
        };

        try {
            const offer = await this.peerConnection.createOffer(offerOptions);
            await this.peerConnection.setLocalDescription(offer);

            this.send({
                type: 'offer',
                target_user_id: this.targetUserId,
                sdp: JSON.stringify({
                    type: offer.type,
                    sdp: offer.sdp
                })
            });

        } catch (error) {
            console.error('[WebRTC] Create offer error:', error);
            throw error;
        }
    }

    async createAnswer() {
        const answerOptions = {
            offerToReceiveAudio: true,
            offerToReceiveVideo: true
        };

        try {
            const answer = await this.peerConnection.createAnswer(answerOptions);
            await this.peerConnection.setLocalDescription(answer);

            this.send({
                type: 'answer',
                target_user_id: this.targetUserId,
                sdp: JSON.stringify({
                    type: answer.type,
                    sdp: answer.sdp
                })
            });

            if (this.options.onCallAccepted) {
                this.options.onCallAccepted();
            }

        } catch (error) {
            console.error('[WebRTC] Create answer error:', error);
            throw error;
        }
    }

    async handleOffer(callerId, sdpJson) {
        console.log('[WebRTC] Handling offer from', callerId);
        this.targetUserId = callerId;

        if (!this.peerConnection) {
            this.createPeerConnection();
        }

        try {
            const sdpData = JSON.parse(sdpJson);
            const offer = new RTCSessionDescription({
                type: sdpData.type,
                sdp: sdpData.sdp
            });

            await this.peerConnection.setRemoteDescription(offer);

        } catch (error) {
            console.error('[WebRTC] Handle offer error:', error);
        }
    }

    async handleAnswer(answererId, sdpJson) {
        console.log('[WebRTC] Handling answer from', answererId);

        try {
            const sdpData = JSON.parse(sdpJson);
            const answer = new RTCSessionDescription({
                type: sdpData.type,
                sdp: sdpData.sdp
            });

            await this.peerConnection.setRemoteDescription(answer);

            if (this.options.onCallAccepted) {
                this.options.onCallAccepted();
            }

        } catch (error) {
            console.error('[WebRTC] Handle answer error:', error);
        }
    }

    handleIceCandidate(senderId, candidateJson) {
        console.log('[WebRTC] Handling ICE candidate from', senderId);

        try {
            const candidateData = JSON.parse(candidateJson);
            const candidate = new RTCIceCandidate({
                candidate: candidateData.candidate,
                sdpMid: candidateData.sdpMid,
                sdpMLineIndex: candidateData.sdpMLineIndex
            });

            this.peerConnection.addIceCandidate(candidate);

        } catch (error) {
            console.error('[WebRTC] Handle ICE candidate error:', error);
        }
    }

    handleHangup(endedBy) {
        console.log('[WebRTC] Call ended by', endedBy);

        if (this.options.onCallEnded) {
            this.options.onCallEnded({ endedBy });
        }

        this.cleanup();
    }

    toggleVideo() {
        if (this.localStream) {
            const videoTrack = this.localStream.getVideoTracks()[0];
            if (videoTrack) {
                this.isVideoEnabled = !this.isVideoEnabled;
                videoTrack.enabled = this.isVideoEnabled;
            }
        }
        return this.isVideoEnabled;
    }

    toggleAudio() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                this.isAudioEnabled = !this.isAudioEnabled;
                audioTrack.enabled = this.isAudioEnabled;
            }
        }
        return this.isAudioEnabled;
    }

    cleanup() {
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        this.remoteStream = null;
        this.targetUserId = null;
        this.isVideoEnabled = true;
        this.isAudioEnabled = true;
    }

    send(message) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('[WebRTC] WebSocket not connected');
        }
    }
}

// Export for module usage or attach to window for script tag usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DiveOpsWebRTC;
} else {
    window.DiveOpsWebRTC = DiveOpsWebRTC;
}
