import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: Color(0xFF10B981), // Emerald Green (high accessibility)
        secondary: Color(0xFF3B82F6), // Blue
        surface: Color(0xFF1E1E1E), // Dark Surface
        background: Color(0xFF121212), // Deep Pitch Dark first
        error: Color(0xFFEF4444), // High-contrast Red
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: Colors.white,
        onBackground: Color(0xFFE5E7EB), // Soft Gray
      ),
      scaffoldBackgroundColor: const Color(0xFF121212),
      appBarTheme: const AppBarTheme(
        backgroundColor: Color(0xFF121212),
        elevation: 0,
        centerTitle: true,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Color(0xFF1E1E1E),
        selectedItemColor: Color(0xFF10B981),
        unselectedItemColor: Colors.grey,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
      ),
      cardTheme: const CardThemeData(
        color: Color(0xFF1E1E1E),
        elevation: 2,
        margin: EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      ),
    );
  }
}
