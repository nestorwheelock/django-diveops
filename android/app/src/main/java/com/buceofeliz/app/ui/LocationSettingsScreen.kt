package com.buceofeliz.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.buceofeliz.app.api.LocationSettingsResponse

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationSettingsScreen(
    settings: LocationSettingsResponse?,
    isLoading: Boolean,
    isSaving: Boolean,
    onUpdateSettings: (visibility: String?, trackingEnabled: Boolean?, interval: Int?) -> Unit,
    onBack: () -> Unit
) {
    var selectedVisibility by remember(settings) {
        mutableStateOf(settings?.visibility ?: "private")
    }
    var trackingEnabled by remember(settings) {
        mutableStateOf(settings?.is_tracking_enabled ?: false)
    }
    var trackingInterval by remember(settings) {
        mutableStateOf(settings?.tracking_interval_seconds ?: 60)
    }

    val hasChanges = settings?.let {
        it.visibility != selectedVisibility ||
        it.is_tracking_enabled != trackingEnabled ||
        it.tracking_interval_seconds != trackingInterval
    } ?: true

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Location Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp)
                ) {
                    // Location Tracking Toggle
                    Card(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "Enable Location Tracking",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.SemiBold
                                )
                                Text(
                                    text = "Share your location while using the app",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Switch(
                                checked = trackingEnabled,
                                onCheckedChange = { trackingEnabled = it }
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // Visibility Settings
                    Text(
                        text = "Who can see your location?",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )

                    val visibilityOptions = listOf(
                        VisibilityOption("private", "Private", "No one can see your location"),
                        VisibilityOption("staff", "Staff Only", "Only dive shop staff"),
                        VisibilityOption("trip", "Trip Participants", "People on the same trip"),
                        VisibilityOption("buddies", "Dive Buddies", "Your designated dive buddies"),
                        VisibilityOption("public", "All Users", "Everyone using the app")
                    )

                    Card(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.fillMaxWidth()) {
                            visibilityOptions.forEachIndexed { index, option ->
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .selectable(
                                            selected = selectedVisibility == option.value,
                                            onClick = { selectedVisibility = option.value },
                                            role = Role.RadioButton
                                        )
                                        .padding(16.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    RadioButton(
                                        selected = selectedVisibility == option.value,
                                        onClick = null
                                    )
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Column {
                                        Text(
                                            text = option.label,
                                            style = MaterialTheme.typography.bodyLarge
                                        )
                                        Text(
                                            text = option.description,
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }

                                if (index < visibilityOptions.size - 1) {
                                    Divider()
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // Tracking Interval
                    Text(
                        text = "Update Frequency",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )

                    Card(
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            Text(
                                text = "Share location every ${trackingInterval / 60} minute${if (trackingInterval >= 120) "s" else ""}",
                                style = MaterialTheme.typography.bodyMedium
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Slider(
                                value = trackingInterval.toFloat(),
                                onValueChange = { trackingInterval = it.toInt() },
                                valueRange = 30f..300f,
                                steps = 8
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "30 sec",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Text(
                                    text = "5 min",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    // Save Button
                    Button(
                        onClick = {
                            onUpdateSettings(
                                selectedVisibility,
                                trackingEnabled,
                                trackingInterval
                            )
                        },
                        modifier = Modifier.fillMaxWidth(),
                        enabled = hasChanges && !isSaving
                    ) {
                        if (isSaving) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                        }
                        Text(if (isSaving) "Saving..." else "Save Changes")
                    }
                }
            }
        }
    }
}

private data class VisibilityOption(
    val value: String,
    val label: String,
    val description: String
)
