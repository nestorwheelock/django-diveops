package com.buceofeliz.app.ui

import android.view.ViewGroup
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import org.webrtc.EglBase
import org.webrtc.SurfaceViewRenderer
import org.webrtc.VideoTrack

@Composable
fun CallScreen(
    targetUserName: String,
    targetUserInitials: String,
    callStatus: String,
    callDuration: String,
    localVideoTrack: VideoTrack?,
    remoteVideoTrack: VideoTrack?,
    eglBase: EglBase,
    isVideoEnabled: Boolean,
    isAudioEnabled: Boolean,
    onToggleVideo: () -> Unit,
    onToggleAudio: () -> Unit,
    onSwitchCamera: () -> Unit,
    onHangup: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF1F2937))
    ) {
        // Remote video (full screen)
        if (remoteVideoTrack != null) {
            VideoRenderer(
                videoTrack = remoteVideoTrack,
                eglBase = eglBase,
                modifier = Modifier.fillMaxSize(),
                mirror = false
            )
        } else {
            // Placeholder when no remote video
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier
                            .size(120.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF374151)),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = targetUserInitials,
                            color = Color.White,
                            fontSize = 48.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = targetUserName,
                        color = Color.White,
                        fontSize = 24.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = callStatus,
                        color = Color.White.copy(alpha = 0.7f),
                        fontSize = 16.sp
                    )
                }
            }
        }

        // Local video (picture-in-picture)
        Box(
            modifier = Modifier
                .padding(16.dp)
                .align(Alignment.TopEnd)
                .size(width = 120.dp, height = 160.dp)
                .clip(RoundedCornerShape(12.dp))
        ) {
            if (localVideoTrack != null && isVideoEnabled) {
                VideoRenderer(
                    videoTrack = localVideoTrack,
                    eglBase = eglBase,
                    modifier = Modifier.fillMaxSize(),
                    mirror = true
                )
            } else {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(Color(0xFF4B5563)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.VideocamOff,
                        contentDescription = "Video off",
                        tint = Color.White.copy(alpha = 0.5f),
                        modifier = Modifier.size(32.dp)
                    )
                }
            }
        }

        // Call duration
        Box(
            modifier = Modifier
                .padding(16.dp)
                .align(Alignment.TopStart)
                .clip(RoundedCornerShape(20.dp))
                .background(Color.Black.copy(alpha = 0.5f))
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            Text(
                text = callDuration,
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium
            )
        }

        // Control buttons
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(
                    brush = androidx.compose.ui.graphics.Brush.verticalGradient(
                        colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.7f))
                    )
                )
                .padding(bottom = 48.dp, top = 24.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Toggle video
                CallControlButton(
                    icon = if (isVideoEnabled) Icons.Default.Videocam else Icons.Default.VideocamOff,
                    contentDescription = "Toggle video",
                    isEnabled = isVideoEnabled,
                    onClick = onToggleVideo,
                    backgroundColor = Color(0xFF374151)
                )

                // Toggle audio
                CallControlButton(
                    icon = if (isAudioEnabled) Icons.Default.Mic else Icons.Default.MicOff,
                    contentDescription = "Toggle audio",
                    isEnabled = isAudioEnabled,
                    onClick = onToggleAudio,
                    backgroundColor = Color(0xFF374151)
                )

                // Hangup
                CallControlButton(
                    icon = Icons.Default.CallEnd,
                    contentDescription = "End call",
                    onClick = onHangup,
                    backgroundColor = Color(0xFFEF4444),
                    size = 72.dp
                )

                // Switch camera
                CallControlButton(
                    icon = Icons.Default.Cameraswitch,
                    contentDescription = "Switch camera",
                    onClick = onSwitchCamera,
                    backgroundColor = Color(0xFF374151)
                )
            }
        }
    }
}

@Composable
private fun CallControlButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    onClick: () -> Unit,
    backgroundColor: Color,
    isEnabled: Boolean = true,
    size: androidx.compose.ui.unit.Dp = 56.dp
) {
    IconButton(
        onClick = onClick,
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .background(if (isEnabled) backgroundColor else backgroundColor.copy(alpha = 0.5f))
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = Color.White,
            modifier = Modifier.size(size / 2)
        )
    }
}

@Composable
fun VideoRenderer(
    videoTrack: VideoTrack,
    eglBase: EglBase,
    modifier: Modifier = Modifier,
    mirror: Boolean = false
) {
    val context = LocalContext.current
    var renderer by remember { mutableStateOf<SurfaceViewRenderer?>(null) }

    DisposableEffect(videoTrack) {
        onDispose {
            try {
                videoTrack.removeSink(renderer)
                renderer?.release()
            } catch (e: Exception) {
                // Ignore cleanup errors
            }
        }
    }

    AndroidView(
        factory = { ctx ->
            SurfaceViewRenderer(ctx).apply {
                layoutParams = ViewGroup.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.MATCH_PARENT
                )
                init(eglBase.eglBaseContext, null)
                setMirror(mirror)
                setEnableHardwareScaler(true)
                renderer = this
                videoTrack.addSink(this)
            }
        },
        modifier = modifier
    )
}

@Composable
fun IncomingCallDialog(
    callerName: String,
    callerInitials: String,
    callType: String,
    onAccept: () -> Unit,
    onReject: () -> Unit
) {
    AlertDialog(
        onDismissRequest = {},
        containerColor = Color(0xFF1F2937),
        title = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                Box(
                    modifier = Modifier
                        .size(80.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF10B981)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Phone,
                        contentDescription = "Incoming call",
                        tint = Color.White,
                        modifier = Modifier.size(40.dp)
                    )
                }
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "Incoming Call",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = callerName,
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 18.sp,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(8.dp))
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = Color(0xFF3B82F6).copy(alpha = 0.2f)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = if (callType == "video") Icons.Default.Videocam else Icons.Default.Phone,
                            contentDescription = null,
                            tint = Color(0xFF3B82F6),
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (callType == "video") "Video Call" else "Audio Call",
                            color = Color(0xFF3B82F6),
                            fontSize = 14.sp
                        )
                    }
                }
            }
        },
        confirmButton = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                // Reject button
                IconButton(
                    onClick = onReject,
                    modifier = Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFEF4444))
                ) {
                    Icon(
                        imageVector = Icons.Default.CallEnd,
                        contentDescription = "Reject",
                        tint = Color.White,
                        modifier = Modifier.size(32.dp)
                    )
                }

                // Accept button
                IconButton(
                    onClick = onAccept,
                    modifier = Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF10B981))
                ) {
                    Icon(
                        imageVector = Icons.Default.Call,
                        contentDescription = "Accept",
                        tint = Color.White,
                        modifier = Modifier.size(32.dp)
                    )
                }
            }
        },
        dismissButton = null
    )
}
