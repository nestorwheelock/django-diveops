package com.buceofeliz.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.buceofeliz.app.api.BookingItem
import com.buceofeliz.app.api.ConversationItem
import com.buceofeliz.app.api.LocationSettingsResponse
import com.buceofeliz.app.api.MessageItem
import com.buceofeliz.app.api.VersionCheckResponse
import com.buceofeliz.app.data.AuthRepository
import com.buceofeliz.app.data.BookingsRepository
import com.buceofeliz.app.data.ChatRepository
import com.buceofeliz.app.data.LocationRepository
import com.buceofeliz.app.data.ProfileRepository
import com.buceofeliz.app.data.UpdateRepository
import com.buceofeliz.app.location.LocationTrackingService
import com.buceofeliz.app.ui.BookingsScreen
import com.buceofeliz.app.ui.CallScreen
import com.buceofeliz.app.ui.ChatScreen
import com.buceofeliz.app.ui.ConversationsScreen
import com.buceofeliz.app.ui.CustomerHomeScreen
import com.buceofeliz.app.ui.IncomingCallDialog
import com.buceofeliz.app.ui.LocationSettingsScreen
import com.buceofeliz.app.ui.LoginScreen
import com.buceofeliz.app.ui.ProfileEditScreen
import com.buceofeliz.app.ui.ProfileScreen
import com.buceofeliz.app.ui.theme.BuceoFelizTheme
import com.buceofeliz.app.webrtc.WebRTCManager
import com.buceofeliz.app.webrtc.WebRTCSignalingClient
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import org.webrtc.VideoTrack

class MainActivity : ComponentActivity() {

    private lateinit var authRepository: AuthRepository
    private lateinit var chatRepository: ChatRepository
    private lateinit var updateRepository: UpdateRepository
    private lateinit var bookingsRepository: BookingsRepository
    private lateinit var locationRepository: LocationRepository
    private lateinit var profileRepository: ProfileRepository

    // WebRTC components
    private var signalingClient: WebRTCSignalingClient? = null
    private var webRTCManager: WebRTCManager? = null

    // Call state - using mutableStateOf for Compose reactivity
    private val _inCall = mutableStateOf(false)
    private val _callTargetUserId = mutableStateOf<String?>(null)
    private val _callTargetName = mutableStateOf("")
    private val _callTargetInitials = mutableStateOf("")
    private val _callStatus = mutableStateOf("Connecting...")
    private val _callDuration = mutableStateOf("00:00")
    private val _localVideoTrack = mutableStateOf<VideoTrack?>(null)
    private val _remoteVideoTrack = mutableStateOf<VideoTrack?>(null)
    private val _isVideoEnabled = mutableStateOf(true)
    private val _isAudioEnabled = mutableStateOf(true)
    private val _incomingCall = mutableStateOf<IncomingCallInfo?>(null)

    data class IncomingCallInfo(
        val callerId: String,
        val callerName: String,
        val callerInitials: String,
        val callType: String
    )

    // Pending call action after permission granted
    private var pendingCallTarget: CallTarget? = null

    data class CallTarget(
        val userId: String,
        val name: String,
        val initials: String
    )

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (isGranted) {
            Log.d(TAG, "Notification permission granted")
        } else {
            Log.d(TAG, "Notification permission denied")
        }
    }

    private val requestCameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val cameraGranted = permissions[Manifest.permission.CAMERA] == true
        val microphoneGranted = permissions[Manifest.permission.RECORD_AUDIO] == true

        if (cameraGranted && microphoneGranted) {
            Log.d(TAG, "Camera and microphone permissions granted")
            pendingCallTarget?.let { target ->
                startCallWithPermissions(target.userId, target.name, target.initials)
                pendingCallTarget = null
            }
        } else {
            Log.d(TAG, "Camera or microphone permission denied")
        }
    }

    // Location permission handling
    private var pendingLocationSettings: PendingLocationSettings? = null

    data class PendingLocationSettings(
        val visibility: String?,
        val trackingEnabled: Boolean?,
        val interval: Int?,
        val onSuccess: () -> Unit
    )

    private val requestLocationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val fineLocationGranted = permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true
        val coarseLocationGranted = permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true

        if (fineLocationGranted || coarseLocationGranted) {
            Log.d(TAG, "Location permissions granted")
            pendingLocationSettings?.let { pending ->
                // Start the tracking service
                val interval = pending.interval ?: 60
                LocationTrackingService.start(this, interval)
                pending.onSuccess()
                pendingLocationSettings = null
            }
        } else {
            Log.d(TAG, "Location permission denied")
            pendingLocationSettings = null
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        authRepository = BuceoFelizApp.getInstance().authRepository
        chatRepository = ChatRepository(authRepository)
        updateRepository = UpdateRepository(this)
        bookingsRepository = BookingsRepository(authRepository)
        locationRepository = LocationRepository(authRepository)
        profileRepository = ProfileRepository(authRepository)

        askNotificationPermission()

        setContent {
            BuceoFelizTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    AppNavigation()
                }
            }
        }
    }

    @Composable
    private fun AppNavigation() {
        val navController = rememberNavController()
        val coroutineScope = rememberCoroutineScope()

        // Check if user is logged in and their role
        var isLoggedIn by remember { mutableStateOf<Boolean?>(null) }
        var isStaff by remember { mutableStateOf(false) }

        // Update dialog state
        var showUpdateDialog by remember { mutableStateOf(false) }
        var updateInfo by remember { mutableStateOf<VersionCheckResponse?>(null) }

        LaunchedEffect(Unit) {
            val token = authRepository.authToken.first()
            isLoggedIn = token != null
            isStaff = authRepository.getIsStaff()

            // Check for app updates
            updateRepository.checkForUpdate().fold(
                onSuccess = { response ->
                    if (response.update_available) {
                        updateInfo = response
                        showUpdateDialog = true
                    }
                },
                onFailure = { /* Ignore update check failures */ }
            )
        }

        // Update available dialog
        if (showUpdateDialog && updateInfo != null) {
            UpdateDialog(
                updateInfo = updateInfo!!,
                onDismiss = {
                    if (!updateInfo!!.force_update) {
                        showUpdateDialog = false
                    }
                },
                onUpdate = {
                    updateInfo?.latest_version?.download_url?.let { url ->
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                        startActivity(intent)
                    }
                }
            )
        }

        // Wait for login state to be determined
        if (isLoggedIn == null) {
            return
        }

        // Role-based start destination
        val startDestination = when {
            isLoggedIn != true -> "login"
            isStaff -> "conversations"  // Staff see conversations
            else -> "customer_home"     // Customers see their home screen
        }

        NavHost(navController = navController, startDestination = startDestination) {
            composable("login") {
                var isLoading by remember { mutableStateOf(false) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                LoginScreen(
                    onLogin = { email, password ->
                        coroutineScope.launch {
                            isLoading = true
                            errorMessage = null

                            val result = authRepository.login(email, password)

                            result.fold(
                                onSuccess = { userInfo ->
                                    // Register FCM token after login
                                    registerFCMToken()

                                    // Navigate based on role
                                    val destination = if (userInfo.is_staff) "conversations" else "customer_home"
                                    navController.navigate(destination) {
                                        popUpTo("login") { inclusive = true }
                                    }
                                },
                                onFailure = { e ->
                                    errorMessage = e.message ?: getString(R.string.error_login)
                                }
                            )

                            isLoading = false
                        }
                    },
                    isLoading = isLoading,
                    errorMessage = errorMessage
                )
            }

            composable("conversations") {
                var conversations by remember { mutableStateOf<List<ConversationItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                fun loadConversations() {
                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null

                        val result = chatRepository.getConversations()

                        result.fold(
                            onSuccess = { conversations = it },
                            onFailure = { e -> errorMessage = e.message ?: getString(R.string.error_network) }
                        )

                        isLoading = false
                    }
                }

                LaunchedEffect(Unit) {
                    loadConversations()
                }

                ConversationsScreen(
                    conversations = conversations,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onConversationClick = { conversation ->
                        navController.navigate("chat/${conversation.id}/${conversation.name}/${conversation.initials}/${conversation.email}")
                    },
                    onRefresh = { loadConversations() },
                    onLogout = {
                        coroutineScope.launch {
                            // Unregister FCM token before logout
                            unregisterFCMToken()
                            authRepository.logout()
                            navController.navigate("login") {
                                popUpTo("conversations") { inclusive = true }
                            }
                        }
                    },
                    onLocationSettingsClick = { navController.navigate("location_settings") }
                )
            }

            composable(
                route = "chat/{conversationId}/{name}/{initials}/{email}",
                arguments = listOf(
                    navArgument("conversationId") { type = NavType.StringType },
                    navArgument("name") { type = NavType.StringType },
                    navArgument("initials") { type = NavType.StringType },
                    navArgument("email") { type = NavType.StringType }
                )
            ) { backStackEntry ->
                val conversationId = backStackEntry.arguments?.getString("conversationId") ?: ""
                val name = backStackEntry.arguments?.getString("name") ?: ""
                val initials = backStackEntry.arguments?.getString("initials") ?: ""
                val email = backStackEntry.arguments?.getString("email") ?: ""

                val conversation = ConversationItem(
                    id = conversationId,
                    person_id = "",
                    name = name,
                    email = email,
                    initials = initials,
                    last_message = "",
                    last_message_time = null,
                    needs_reply = false,
                    unread_count = 0,
                    status = ""
                )

                var messages by remember { mutableStateOf<List<MessageItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var isSending by remember { mutableStateOf(false) }

                LaunchedEffect(conversationId) {
                    val result = chatRepository.getMessages(conversationId)
                    result.fold(
                        onSuccess = { messages = it },
                        onFailure = { /* Handle error */ }
                    )
                    isLoading = false
                }

                ChatScreen(
                    conversation = conversation,
                    messages = messages,
                    isLoading = isLoading,
                    isSending = isSending,
                    onSendMessage = { messageText ->
                        coroutineScope.launch {
                            isSending = true
                            val result = chatRepository.sendMessage(conversationId, messageText)
                            result.fold(
                                onSuccess = {
                                    // Reload messages
                                    val messagesResult = chatRepository.getMessages(conversationId)
                                    messagesResult.fold(
                                        onSuccess = { messages = it },
                                        onFailure = { /* Handle error */ }
                                    )
                                },
                                onFailure = { /* Handle error */ }
                            )
                            isSending = false
                        }
                    },
                    onStartCall = {
                        // Get person_id from conversation for WebRTC call
                        // Note: We need the person_id, not conversation_id for calls
                        startCall(
                            targetUserId = conversation.person_id,
                            targetName = name,
                            targetInitials = initials
                        )
                        navController.navigate("call")
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            // Customer Home Screen
            composable("customer_home") {
                var userInfo by remember { mutableStateOf<String>("") }

                LaunchedEffect(Unit) {
                    authRepository.userInfo.first()?.let {
                        userInfo = "${it.first_name} ${it.last_name}"
                    }
                }

                CustomerHomeScreen(
                    userName = userInfo,
                    onBookingsClick = { navController.navigate("bookings") },
                    onMessagesClick = { navController.navigate("conversations") },
                    onProfileClick = { navController.navigate("profile") },
                    onLocationSettingsClick = { navController.navigate("location_settings") },
                    onLogout = {
                        coroutineScope.launch {
                            unregisterFCMToken()
                            authRepository.logout()
                            navController.navigate("login") {
                                popUpTo("customer_home") { inclusive = true }
                            }
                        }
                    }
                )
            }

            // Bookings Screen
            composable("bookings") {
                var upcomingBookings by remember { mutableStateOf<List<BookingItem>>(emptyList()) }
                var pastBookings by remember { mutableStateOf<List<BookingItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                fun loadBookings() {
                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null

                        bookingsRepository.getBookings().fold(
                            onSuccess = { response ->
                                upcomingBookings = response.upcoming
                                pastBookings = response.past
                            },
                            onFailure = { e ->
                                errorMessage = e.message ?: "Failed to load bookings"
                            }
                        )

                        isLoading = false
                    }
                }

                LaunchedEffect(Unit) {
                    loadBookings()
                }

                BookingsScreen(
                    upcomingBookings = upcomingBookings,
                    pastBookings = pastBookings,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onRefresh = { loadBookings() },
                    onBack = { navController.popBackStack() }
                )
            }

            // Profile Screen
            composable("profile") {
                var profile by remember { mutableStateOf<com.buceofeliz.app.api.ProfileResponse?>(null) }
                var certifications by remember { mutableStateOf<List<com.buceofeliz.app.api.CertificationItem>>(emptyList()) }
                var emergencyContacts by remember { mutableStateOf<List<com.buceofeliz.app.api.EmergencyContactItem>>(emptyList()) }
                var isLoading by remember { mutableStateOf(true) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                fun loadProfile() {
                    coroutineScope.launch {
                        isLoading = true
                        errorMessage = null

                        // Load profile, certifications, and emergency contacts in parallel
                        val profileResult = profileRepository.getProfile()
                        val certsResult = profileRepository.getCertifications()
                        val contactsResult = profileRepository.getEmergencyContacts()

                        profileResult.fold(
                            onSuccess = { profile = it },
                            onFailure = { e -> errorMessage = e.message ?: "Failed to load profile" }
                        )

                        certsResult.fold(
                            onSuccess = { certifications = it },
                            onFailure = { /* Non-critical, ignore */ }
                        )

                        contactsResult.fold(
                            onSuccess = { emergencyContacts = it },
                            onFailure = { /* Non-critical, ignore */ }
                        )

                        isLoading = false
                    }
                }

                LaunchedEffect(Unit) {
                    loadProfile()
                }

                ProfileScreen(
                    profile = profile,
                    certifications = certifications,
                    emergencyContacts = emergencyContacts,
                    isLoading = isLoading,
                    errorMessage = errorMessage,
                    onRefresh = { loadProfile() },
                    onEditGear = { navController.navigate("profile_edit") },
                    onBack = { navController.popBackStack() }
                )
            }

            // Profile Edit Screen
            composable("profile_edit") {
                var profile by remember { mutableStateOf<com.buceofeliz.app.api.ProfileResponse?>(null) }
                var isLoading by remember { mutableStateOf(true) }
                var isSaving by remember { mutableStateOf(false) }
                var errorMessage by remember { mutableStateOf<String?>(null) }

                LaunchedEffect(Unit) {
                    profileRepository.getProfile().fold(
                        onSuccess = { profile = it },
                        onFailure = { e -> errorMessage = e.message }
                    )
                    isLoading = false
                }

                ProfileEditScreen(
                    currentGearSizing = profile?.gear_sizing,
                    currentEquipmentOwnership = profile?.equipment_ownership ?: "none",
                    isLoading = isLoading || isSaving,
                    errorMessage = errorMessage,
                    onSave = { request ->
                        coroutineScope.launch {
                            isSaving = true
                            errorMessage = null

                            profileRepository.updateProfile(request).fold(
                                onSuccess = {
                                    navController.popBackStack()
                                },
                                onFailure = { e ->
                                    errorMessage = e.message ?: "Failed to save profile"
                                    isSaving = false
                                }
                            )
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            // Location Settings Screen
            composable("location_settings") {
                var settings by remember { mutableStateOf<LocationSettingsResponse?>(null) }
                var isLoading by remember { mutableStateOf(true) }
                var isSaving by remember { mutableStateOf(false) }

                LaunchedEffect(Unit) {
                    locationRepository.getSettings().fold(
                        onSuccess = { settings = it },
                        onFailure = { /* Handle error */ }
                    )
                    isLoading = false
                }

                LocationSettingsScreen(
                    settings = settings,
                    isLoading = isLoading,
                    isSaving = isSaving,
                    onUpdateSettings = { visibility, trackingEnabled, interval ->
                        coroutineScope.launch {
                            isSaving = true

                            // Handle tracking service start/stop
                            if (trackingEnabled == true) {
                                // Check if we have location permissions
                                val fineLocation = ContextCompat.checkSelfPermission(
                                    this@MainActivity,
                                    Manifest.permission.ACCESS_FINE_LOCATION
                                )
                                val coarseLocation = ContextCompat.checkSelfPermission(
                                    this@MainActivity,
                                    Manifest.permission.ACCESS_COARSE_LOCATION
                                )

                                if (fineLocation == PackageManager.PERMISSION_GRANTED ||
                                    coarseLocation == PackageManager.PERMISSION_GRANTED) {
                                    // Permissions granted, start tracking
                                    LocationTrackingService.start(this@MainActivity, interval ?: 60)

                                    // Save settings to server
                                    locationRepository.updateSettings(
                                        visibility = visibility,
                                        isTrackingEnabled = trackingEnabled,
                                        trackingIntervalSeconds = interval
                                    ).fold(
                                        onSuccess = { settings = it },
                                        onFailure = { /* Handle error */ }
                                    )
                                    isSaving = false
                                } else {
                                    // Request permissions
                                    pendingLocationSettings = PendingLocationSettings(
                                        visibility = visibility,
                                        trackingEnabled = trackingEnabled,
                                        interval = interval,
                                        onSuccess = {
                                            coroutineScope.launch {
                                                locationRepository.updateSettings(
                                                    visibility = visibility,
                                                    isTrackingEnabled = trackingEnabled,
                                                    trackingIntervalSeconds = interval
                                                ).fold(
                                                    onSuccess = { settings = it },
                                                    onFailure = { /* Handle error */ }
                                                )
                                                isSaving = false
                                            }
                                        }
                                    )
                                    requestLocationPermissionLauncher.launch(
                                        arrayOf(
                                            Manifest.permission.ACCESS_FINE_LOCATION,
                                            Manifest.permission.ACCESS_COARSE_LOCATION
                                        )
                                    )
                                }
                            } else {
                                // Tracking disabled, stop service
                                LocationTrackingService.stop(this@MainActivity)

                                // Save settings to server
                                locationRepository.updateSettings(
                                    visibility = visibility,
                                    isTrackingEnabled = trackingEnabled,
                                    trackingIntervalSeconds = interval
                                ).fold(
                                    onSuccess = { settings = it },
                                    onFailure = { /* Handle error */ }
                                )
                                isSaving = false
                            }
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            // Call Screen
            composable("call") {
                val inCall by _inCall
                val localVideoTrack by _localVideoTrack
                val remoteVideoTrack by _remoteVideoTrack
                val isVideoEnabled by _isVideoEnabled
                val isAudioEnabled by _isAudioEnabled
                val callStatus by _callStatus
                val callDuration by _callDuration
                val targetName by _callTargetName
                val targetInitials by _callTargetInitials

                if (inCall) {
                    webRTCManager?.let { manager ->
                        CallScreen(
                            targetUserName = targetName,
                            targetUserInitials = targetInitials,
                            callStatus = callStatus,
                            callDuration = callDuration,
                            localVideoTrack = localVideoTrack,
                            remoteVideoTrack = remoteVideoTrack,
                            eglBase = manager.getEglBase(),
                            isVideoEnabled = isVideoEnabled,
                            isAudioEnabled = isAudioEnabled,
                            onToggleVideo = {
                                _isVideoEnabled.value = manager.toggleVideo()
                            },
                            onToggleAudio = {
                                _isAudioEnabled.value = manager.toggleAudio()
                            },
                            onSwitchCamera = {
                                manager.switchCamera()
                            },
                            onHangup = {
                                manager.hangup()
                                _inCall.value = false
                                navController.popBackStack()
                            }
                        )
                    }
                }
            }
        }

        // Incoming call dialog (shown on top of any screen)
        val incomingCall by _incomingCall
        incomingCall?.let { call ->
            IncomingCallDialog(
                callerName = call.callerName,
                callerInitials = call.callerInitials,
                callType = call.callType,
                onAccept = {
                    _incomingCall.value = null
                    acceptIncomingCall(call.callerId, call.callerName, call.callerInitials, call.callType)
                    navController.navigate("call")
                },
                onReject = {
                    rejectIncomingCall(call.callerId)
                    _incomingCall.value = null
                }
            )
        }
    }

    @Composable
    private fun UpdateDialog(
        updateInfo: VersionCheckResponse,
        onDismiss: () -> Unit,
        onUpdate: () -> Unit
    ) {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("Update Available") },
            text = {
                Text(
                    if (updateInfo.force_update) {
                        "A required update is available (v${updateInfo.latest_version?.version_name}). " +
                        "Please update to continue using the app.\n\n" +
                        "${updateInfo.latest_version?.release_notes ?: ""}"
                    } else {
                        "A new version is available (v${updateInfo.latest_version?.version_name}).\n\n" +
                        "${updateInfo.latest_version?.release_notes ?: ""}"
                    }
                )
            },
            confirmButton = {
                TextButton(onClick = onUpdate) {
                    Text("Update")
                }
            },
            dismissButton = if (!updateInfo.force_update) {
                { TextButton(onClick = onDismiss) { Text("Later") } }
            } else null
        )
    }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) !=
                PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun registerFCMToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                Log.d(TAG, "FCM Token: $token")

                // Register with server
                kotlinx.coroutines.GlobalScope.launch {
                    try {
                        val deviceId = Settings.Secure.getString(
                            contentResolver,
                            Settings.Secure.ANDROID_ID
                        )
                        val deviceName = "${Build.MANUFACTURER} ${Build.MODEL}"

                        authRepository.registerFCMToken(
                            fcmToken = token,
                            deviceId = deviceId,
                            deviceName = deviceName
                        )
                        Log.d(TAG, "FCM token registered with server")
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to register FCM token", e)
                    }
                }
            } else {
                Log.e(TAG, "Failed to get FCM token", task.exception)
            }
        }
    }

    private fun unregisterFCMToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                kotlinx.coroutines.GlobalScope.launch {
                    try {
                        authRepository.unregisterFCMToken(task.result)
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to unregister FCM token", e)
                    }
                }
            }
        }
    }

    // WebRTC call methods
    private fun startCall(targetUserId: String, targetName: String, targetInitials: String) {
        // Check for camera and microphone permissions
        val cameraPermission = ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
        val microphonePermission = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)

        if (cameraPermission == PackageManager.PERMISSION_GRANTED &&
            microphonePermission == PackageManager.PERMISSION_GRANTED) {
            startCallWithPermissions(targetUserId, targetName, targetInitials)
        } else {
            pendingCallTarget = CallTarget(targetUserId, targetName, targetInitials)
            requestCameraPermissionLauncher.launch(
                arrayOf(Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
            )
        }
    }

    private fun startCallWithPermissions(targetUserId: String, targetName: String, targetInitials: String) {
        Log.d(TAG, "Starting call to $targetUserId ($targetName)")

        _callTargetUserId.value = targetUserId
        _callTargetName.value = targetName
        _callTargetInitials.value = targetInitials
        _callStatus.value = "Calling..."
        _inCall.value = true

        kotlinx.coroutines.GlobalScope.launch {
            initializeWebRTC()
            webRTCManager?.startCall(targetUserId)
        }
    }

    private fun acceptIncomingCall(callerId: String, callerName: String, callerInitials: String, callType: String) {
        Log.d(TAG, "Accepting call from $callerId")

        _callTargetUserId.value = callerId
        _callTargetName.value = callerName
        _callTargetInitials.value = callerInitials
        _callStatus.value = "Connecting..."
        _inCall.value = true

        kotlinx.coroutines.GlobalScope.launch {
            initializeWebRTC()
            webRTCManager?.answerCall(callerId, callType)
        }
    }

    private fun rejectIncomingCall(callerId: String) {
        Log.d(TAG, "Rejecting call from $callerId")
        webRTCManager?.reject()
    }

    private suspend fun initializeWebRTC() {
        if (signalingClient != null && webRTCManager != null) return

        val token = authRepository.authToken.first() ?: return

        signalingClient = WebRTCSignalingClient(token, object : WebRTCSignalingClient.SignalingListener {
            override fun onConnected(userId: String) {
                Log.d(TAG, "WebRTC signaling connected for user $userId")
            }

            override fun onDisconnected() {
                Log.d(TAG, "WebRTC signaling disconnected")
            }

            override fun onIncomingCall(callerId: String, callType: String) {
                Log.d(TAG, "Incoming call from $callerId ($callType)")
                // TODO: Look up caller name/initials from API
                _incomingCall.value = IncomingCallInfo(
                    callerId = callerId,
                    callerName = "Caller",
                    callerInitials = "C",
                    callType = callType
                )
            }

            override fun onOffer(callerId: String, sdp: String) {
                webRTCManager?.handleOffer(callerId, sdp)
            }

            override fun onAnswer(answererId: String, sdp: String) {
                webRTCManager?.handleAnswer(answererId, sdp)
            }

            override fun onIceCandidate(senderId: String, candidate: String) {
                webRTCManager?.handleIceCandidate(senderId, candidate)
            }

            override fun onHangup(endedBy: String) {
                Log.d(TAG, "Call ended by $endedBy")
                _inCall.value = false
                webRTCManager?.cleanup()
            }

            override fun onRejected(rejectedBy: String) {
                Log.d(TAG, "Call rejected by $rejectedBy")
                _inCall.value = false
                _callStatus.value = "Call rejected"
                webRTCManager?.cleanup()
            }

            override fun onUserOffline(userId: String) {
                Log.d(TAG, "User $userId is offline")
                _callStatus.value = "User offline"
            }

            override fun onError(message: String) {
                Log.e(TAG, "Signaling error: $message")
            }
        })

        signalingClient?.connect()

        webRTCManager = WebRTCManager(this, signalingClient!!, object : WebRTCManager.WebRTCListener {
            override fun onLocalStream(videoTrack: VideoTrack?) {
                _localVideoTrack.value = videoTrack
            }

            override fun onRemoteStream(videoTrack: VideoTrack?) {
                _remoteVideoTrack.value = videoTrack
            }

            override fun onCallConnected() {
                _callStatus.value = "Connected"
            }

            override fun onCallEnded(reason: String) {
                _inCall.value = false
                _callStatus.value = reason
            }

            override fun onError(message: String) {
                Log.e(TAG, "WebRTC error: $message")
            }
        })
    }

    override fun onDestroy() {
        super.onDestroy()
        webRTCManager?.release()
        signalingClient?.disconnect()
    }

    companion object {
        private const val TAG = "MainActivity"
    }
}
