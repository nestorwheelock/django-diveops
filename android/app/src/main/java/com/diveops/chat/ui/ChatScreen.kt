package com.diveops.chat.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Send
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.diveops.chat.R
import com.diveops.chat.api.ConversationItem
import com.diveops.chat.api.MessageItem
import com.diveops.chat.ui.theme.MessageInbound
import com.diveops.chat.ui.theme.MessageOutbound
import com.diveops.chat.ui.theme.Primary
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    conversation: ConversationItem,
    messages: List<MessageItem>,
    isLoading: Boolean,
    isSending: Boolean,
    onSendMessage: (String) -> Unit,
    onStartCall: () -> Unit,
    onBack: () -> Unit
) {
    var messageText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()

    // Scroll to bottom when new messages arrive
    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        // Avatar
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(Primary),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = conversation.initials,
                                color = Color.White,
                                fontWeight = FontWeight.Bold,
                                fontSize = 14.sp
                            )
                        }
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                text = conversation.name,
                                fontSize = 16.sp
                            )
                            if (conversation.email.isNotBlank()) {
                                Text(
                                    text = conversation.email,
                                    fontSize = 12.sp,
                                    color = Color.White.copy(alpha = 0.7f)
                                )
                            }
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            Icons.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    IconButton(onClick = onStartCall) {
                        Icon(
                            Icons.Filled.Videocam,
                            contentDescription = "Start video call",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Primary,
                    titleContentColor = Color.White
                )
            )
        },
        bottomBar = {
            // Message input
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shadowElevation = 8.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OutlinedTextField(
                        value = messageText,
                        onValueChange = { messageText = it },
                        placeholder = { Text(stringResource(R.string.chat_placeholder)) },
                        modifier = Modifier
                            .weight(1f)
                            .padding(end = 8.dp),
                        maxLines = 4,
                        enabled = !isSending,
                        shape = RoundedCornerShape(24.dp)
                    )

                    IconButton(
                        onClick = {
                            if (messageText.isNotBlank()) {
                                onSendMessage(messageText)
                                messageText = ""
                                coroutineScope.launch {
                                    if (messages.isNotEmpty()) {
                                        listState.animateScrollToItem(messages.size - 1)
                                    }
                                }
                            }
                        },
                        enabled = messageText.isNotBlank() && !isSending,
                        modifier = Modifier
                            .size(48.dp)
                            .clip(CircleShape)
                            .background(
                                if (messageText.isNotBlank() && !isSending) Primary
                                else Primary.copy(alpha = 0.5f)
                            )
                    ) {
                        if (isSending) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                color = Color.White
                            )
                        } else {
                            Icon(
                                Icons.Filled.Send,
                                contentDescription = "Send",
                                tint = Color.White
                            )
                        }
                    }
                }
            }
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .background(MaterialTheme.colorScheme.background)
        ) {
            if (isLoading && messages.isEmpty()) {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.Center)
                )
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp),
                    contentPadding = PaddingValues(vertical = 8.dp)
                ) {
                    items(messages) { message ->
                        MessageBubble(message = message)
                    }
                }
            }
        }
    }
}

@Composable
private fun MessageBubble(message: MessageItem) {
    val isOutbound = message.direction == "outbound"

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalAlignment = if (isOutbound) Alignment.End else Alignment.Start
    ) {
        // Sender name for inbound messages
        if (!isOutbound) {
            Text(
                text = message.sender_name,
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.6f),
                modifier = Modifier.padding(start = 12.dp, bottom = 2.dp)
            )
        }

        Box(
            modifier = Modifier
                .widthIn(max = 280.dp)
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (isOutbound) 16.dp else 4.dp,
                        bottomEnd = if (isOutbound) 4.dp else 16.dp
                    )
                )
                .background(if (isOutbound) MessageOutbound else MessageInbound)
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Text(
                text = message.body,
                color = if (isOutbound) Color.White else Color.Black,
                fontSize = 15.sp
            )
        }

        // Time and status
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 2.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = formatMessageTime(message.created_at),
                fontSize = 11.sp,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.5f)
            )

            if (isOutbound) {
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = when (message.status) {
                        "sent" -> "✓"
                        "delivered" -> "✓✓"
                        "read" -> "✓✓"
                        else -> ""
                    },
                    fontSize = 12.sp,
                    color = if (message.status == "read") Primary else MaterialTheme.colorScheme.onBackground.copy(alpha = 0.5f)
                )
            }
        }
    }
}

private fun formatMessageTime(isoString: String): String {
    return try {
        val instant = Instant.parse(isoString)
        val localDateTime = instant.atZone(ZoneId.systemDefault())
        localDateTime.format(DateTimeFormatter.ofPattern("h:mm a"))
    } catch (e: Exception) {
        ""
    }
}
