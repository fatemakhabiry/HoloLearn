import 'package:flutter/material.dart';
import 'app_colors.dart';
import 'app_fonts.dart';

class AppTheme {
  AppTheme._();

  static const _primary    = AppColors.primaryColor;
  static const _fontFamily = AppFonts.primary;

  // ─────────────────────────────────────────────────────────────────────────
  // LIGHT
  // ─────────────────────────────────────────────────────────────────────────
  static final ThemeData light = ThemeData(
    brightness: Brightness.light,
    fontFamily: _fontFamily,
    colorScheme: ColorScheme.light(
      primary: _primary,
      secondary: AppColors.secondaryColor,
      surface: AppColors.white,
      error: AppColors.error,
    ),
    scaffoldBackgroundColor: AppColors.lightBackground,
    cardColor: AppColors.white,

    appBarTheme: const AppBarTheme(
      backgroundColor: _primary,
      foregroundColor: AppColors.white,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontFamily: _fontFamily,
        fontSize: AppFonts.fontSizeML,
        fontWeight: AppFonts.semiBold,
        color: AppColors.white,
      ),
    ),

    cardTheme: CardThemeData(
      color: AppColors.white,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.lightBackground,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
      hintStyle: TextStyle(
        fontFamily: _fontFamily,
        color: AppColors.gray,
        fontSize: AppFonts.fontSizeS,
      ),
    ),

    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? _primary : AppColors.gray,
      ),
      trackColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected)
            ? _primary.withOpacity(0.4)
            : AppColors.gray.withOpacity(0.3),
      ),
    ),

    textTheme: const TextTheme(
      displayLarge: TextStyle(fontFamily: _fontFamily, color: AppColors.textBlack),
      bodyLarge:    TextStyle(fontFamily: _fontFamily, color: AppColors.textBlack),
      bodyMedium:   TextStyle(fontFamily: _fontFamily, color: AppColors.textBlack),
      bodySmall:    TextStyle(fontFamily: _fontFamily, color: AppColors.gray),
      labelSmall:   TextStyle(fontFamily: _fontFamily, color: AppColors.gray),
    ),

    dividerColor: AppColors.gray.withOpacity(0.3),
    iconTheme: const IconThemeData(color: AppColors.textBlack),
  );

  // ─────────────────────────────────────────────────────────────────────────
  // DARK
  // ─────────────────────────────────────────────────────────────────────────
  static final ThemeData dark = ThemeData(
    brightness: Brightness.dark,
    fontFamily: _fontFamily,
    colorScheme: ColorScheme.dark(
      primary: _primary,
      secondary: AppColors.secondaryColor,
      surface: AppColors.darkCard,
      error: AppColors.error,
    ),
    scaffoldBackgroundColor: AppColors.darkBackground,
    cardColor: AppColors.darkCard,

    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.darkCard,
      foregroundColor: AppColors.textLight,
      elevation: 0,
      centerTitle: true,
      titleTextStyle: TextStyle(
        fontFamily: _fontFamily,
        fontSize: AppFonts.fontSizeML,
        fontWeight: AppFonts.semiBold,
        color: AppColors.textLight,
      ),
    ),

    cardTheme: CardThemeData(
      color: AppColors.darkCard,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
    ),

    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.darkBorder.withOpacity(0.5),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
      hintStyle: TextStyle(
        fontFamily: _fontFamily,
        color: AppColors.darkTextSecondary,
        fontSize: AppFonts.fontSizeS,
      ),
    ),

    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected) ? _primary : AppColors.darkTextSecondary,
      ),
      trackColor: WidgetStateProperty.resolveWith(
        (s) => s.contains(WidgetState.selected)
            ? _primary.withOpacity(0.4)
            : AppColors.darkBorder,
      ),
    ),

    textTheme: TextTheme(
      displayLarge: TextStyle(fontFamily: _fontFamily, color: AppColors.textLight),
      bodyLarge:    TextStyle(fontFamily: _fontFamily, color: AppColors.textLight),
      bodyMedium:   TextStyle(fontFamily: _fontFamily, color: AppColors.textLight),
      bodySmall:    TextStyle(fontFamily: _fontFamily, color: AppColors.darkTextSecondary),
      labelSmall:   TextStyle(fontFamily: _fontFamily, color: AppColors.darkTextSecondary),
    ),

    dividerColor: AppColors.darkBorder,
    iconTheme: IconThemeData(color: AppColors.textLight),
  );
}
extension ThemeColors on BuildContext {
  bool get isDark => Theme.of(this).brightness == Brightness.dark;
 
  // ── Backgrounds ───────────────────────────────────────────────────────────
  Color get cardColor  => isDark ? AppColors.darkCard       : AppColors.white;
  Color get inputColor => isDark ? AppColors.darkCard       : AppColors.lightBackground;
 
  // ── Text ──────────────────────────────────────────────────────────────────
  Color get textPrimary   => isDark ? AppColors.textLight   : AppColors.textBlack;
  Color get textSecondary => isDark ? AppColors.darkTextSecondary : AppColors.textLight;
 
  // ── Shadow — none in dark mode ────────────────────────────────────────────
  List<BoxShadow> get cardShadow =>  [
          BoxShadow(
            color: AppColors.primaryColor.withOpacity(0.1),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ];
}