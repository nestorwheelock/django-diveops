package com.buceofeliz.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.buceofeliz.app.api.GearSizing
import com.buceofeliz.app.api.ProfileUpdateRequest

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileEditScreen(
    currentGearSizing: GearSizing?,
    currentEquipmentOwnership: String,
    isLoading: Boolean,
    errorMessage: String?,
    onSave: (ProfileUpdateRequest) -> Unit,
    onBack: () -> Unit
) {
    // Form state
    var weightKg by remember { mutableStateOf(currentGearSizing?.weight_kg ?: "") }
    var heightCm by remember { mutableStateOf(currentGearSizing?.height_cm?.toString() ?: "") }
    var wetsuitSize by remember { mutableStateOf(currentGearSizing?.wetsuit_size ?: "") }
    var bcdSize by remember { mutableStateOf(currentGearSizing?.bcd_size ?: "") }
    var finSize by remember { mutableStateOf(currentGearSizing?.fin_size ?: "") }
    var maskFit by remember { mutableStateOf(currentGearSizing?.mask_fit ?: "") }
    var gloveSize by remember { mutableStateOf(currentGearSizing?.glove_size ?: "") }
    var weightRequired by remember { mutableStateOf(currentGearSizing?.weight_required_kg ?: "") }
    var gearNotes by remember { mutableStateOf(currentGearSizing?.gear_notes ?: "") }
    var equipmentOwnership by remember { mutableStateOf(currentEquipmentOwnership) }

    // Dropdown states
    var wetsuitExpanded by remember { mutableStateOf(false) }
    var bcdExpanded by remember { mutableStateOf(false) }
    var gloveExpanded by remember { mutableStateOf(false) }
    var ownershipExpanded by remember { mutableStateOf(false) }

    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Edit Gear Sizing") },
                navigationIcon = {
                    IconButton(onClick = onBack, enabled = !isLoading) {
                        Icon(Icons.Filled.ArrowBack, "Back")
                    }
                },
                actions = {
                    IconButton(
                        onClick = {
                            val request = ProfileUpdateRequest(
                                weight_kg = weightKg.ifBlank { null },
                                height_cm = heightCm.toIntOrNull(),
                                wetsuit_size = wetsuitSize.ifBlank { null },
                                bcd_size = bcdSize.ifBlank { null },
                                fin_size = finSize.ifBlank { null },
                                mask_fit = maskFit.ifBlank { null },
                                glove_size = gloveSize.ifBlank { null },
                                weight_required_kg = weightRequired.ifBlank { null },
                                gear_notes = gearNotes.ifBlank { null },
                                equipment_ownership = equipmentOwnership.ifBlank { null }
                            )
                            onSave(request)
                        },
                        enabled = !isLoading
                    ) {
                        Icon(Icons.Default.Check, "Save")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(scrollState)
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Error message
                if (errorMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Text(
                            text = errorMessage,
                            modifier = Modifier.padding(16.dp),
                            color = MaterialTheme.colorScheme.onErrorContainer
                        )
                    }
                }

                // Body Measurements Section
                SectionHeader(title = "Body Measurements")

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    OutlinedTextField(
                        value = weightKg,
                        onValueChange = { weightKg = it },
                        label = { Text("Weight (kg)") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        singleLine = true
                    )

                    OutlinedTextField(
                        value = heightCm,
                        onValueChange = { heightCm = it },
                        label = { Text("Height (cm)") },
                        modifier = Modifier.weight(1f),
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        singleLine = true
                    )
                }

                // Gear Sizes Section
                SectionHeader(title = "Gear Sizes")

                // Wetsuit Size Dropdown
                ExposedDropdownMenuBox(
                    expanded = wetsuitExpanded,
                    onExpandedChange = { wetsuitExpanded = it }
                ) {
                    OutlinedTextField(
                        value = wetsuitSize,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Wetsuit Size") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = wetsuitExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = wetsuitExpanded,
                        onDismissRequest = { wetsuitExpanded = false }
                    ) {
                        listOf("", "XS", "S", "M", "L", "XL", "XXL", "XXXL").forEach { size ->
                            DropdownMenuItem(
                                text = { Text(size.ifEmpty { "Not set" }) },
                                onClick = {
                                    wetsuitSize = size
                                    wetsuitExpanded = false
                                }
                            )
                        }
                    }
                }

                // BCD Size Dropdown
                ExposedDropdownMenuBox(
                    expanded = bcdExpanded,
                    onExpandedChange = { bcdExpanded = it }
                ) {
                    OutlinedTextField(
                        value = bcdSize,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("BCD Size") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = bcdExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = bcdExpanded,
                        onDismissRequest = { bcdExpanded = false }
                    ) {
                        listOf("", "XS", "S", "M", "L", "XL", "XXL").forEach { size ->
                            DropdownMenuItem(
                                text = { Text(size.ifEmpty { "Not set" }) },
                                onClick = {
                                    bcdSize = size
                                    bcdExpanded = false
                                }
                            )
                        }
                    }
                }

                // Fin Size - text input for flexibility
                OutlinedTextField(
                    value = finSize,
                    onValueChange = { finSize = it },
                    label = { Text("Fin Size") },
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("e.g., 42-43, M/L") },
                    singleLine = true
                )

                // Mask Fit - text input
                OutlinedTextField(
                    value = maskFit,
                    onValueChange = { maskFit = it },
                    label = { Text("Mask Fit") },
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("e.g., Standard, Low Volume") },
                    singleLine = true
                )

                // Glove Size Dropdown
                ExposedDropdownMenuBox(
                    expanded = gloveExpanded,
                    onExpandedChange = { gloveExpanded = it }
                ) {
                    OutlinedTextField(
                        value = gloveSize,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Glove Size") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = gloveExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = gloveExpanded,
                        onDismissRequest = { gloveExpanded = false }
                    ) {
                        listOf("", "XS", "S", "M", "L", "XL").forEach { size ->
                            DropdownMenuItem(
                                text = { Text(size.ifEmpty { "Not set" }) },
                                onClick = {
                                    gloveSize = size
                                    gloveExpanded = false
                                }
                            )
                        }
                    }
                }

                // Dive Weights Section
                SectionHeader(title = "Dive Weights")

                OutlinedTextField(
                    value = weightRequired,
                    onValueChange = { weightRequired = it },
                    label = { Text("Weight Required (kg)") },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    singleLine = true,
                    placeholder = { Text("e.g., 6.0") }
                )

                // Equipment Ownership
                SectionHeader(title = "Equipment Ownership")

                ExposedDropdownMenuBox(
                    expanded = ownershipExpanded,
                    onExpandedChange = { ownershipExpanded = it }
                ) {
                    OutlinedTextField(
                        value = formatOwnershipDisplay(equipmentOwnership),
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Equipment Status") },
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = ownershipExpanded) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor()
                    )
                    ExposedDropdownMenu(
                        expanded = ownershipExpanded,
                        onDismissRequest = { ownershipExpanded = false }
                    ) {
                        listOf(
                            "none" to "Rents All Equipment",
                            "partial" to "Owns Some Equipment",
                            "full" to "Owns All Equipment"
                        ).forEach { (value, label) ->
                            DropdownMenuItem(
                                text = { Text(label) },
                                onClick = {
                                    equipmentOwnership = value
                                    ownershipExpanded = false
                                }
                            )
                        }
                    }
                }

                // Notes Section
                SectionHeader(title = "Notes")

                OutlinedTextField(
                    value = gearNotes,
                    onValueChange = { gearNotes = it },
                    label = { Text("Gear Notes") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 100.dp),
                    placeholder = { Text("Any special requirements or preferences...") },
                    maxLines = 5
                )

                // Bottom spacing
                Spacer(modifier = Modifier.height(32.dp))
            }

            // Loading overlay
            if (isLoading) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.surface.copy(alpha = 0.7f)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        CircularProgressIndicator()
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.SemiBold,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(top = 8.dp)
    )
}

private fun formatOwnershipDisplay(ownership: String): String {
    return when (ownership) {
        "none" -> "Rents All Equipment"
        "partial" -> "Owns Some Equipment"
        "full" -> "Owns All Equipment"
        else -> ownership.replaceFirstChar { it.uppercase() }
    }
}
