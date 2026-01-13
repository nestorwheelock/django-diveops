package com.buceofeliz.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// Buceo Feliz brand colors
val Primary = Color(0xFF0EA5E9)
val PrimaryDark = Color(0xFF0284C7)
val Secondary = Color(0xFF06B6D4)
val Background = Color(0xFFF8FAFC)
val Surface = Color(0xFFFFFFFF)
val OnPrimary = Color(0xFFFFFFFF)
val OnBackground = Color(0xFF1E293B)
val OnSurface = Color(0xFF1E293B)

// Chat colors
val MessageOutbound = Color(0xFF0EA5E9)
val MessageInbound = Color(0xFFE5E7EB)
val UnreadBadge = Color(0xFF22C55E)  // Green - happier like money

private val LightColorScheme = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    secondary = Secondary,
    background = Background,
    surface = Surface,
    onBackground = OnBackground,
    onSurface = OnSurface,
)

private val DarkColorScheme = darkColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    secondary = Secondary,
    background = Color(0xFF0F172A),
    surface = Color(0xFF1E293B),
    onBackground = Color(0xFFF1F5F9),
    onSurface = Color(0xFFF1F5F9),
)

@Composable
fun BuceoFelizTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
