import 'package:flutter/material.dart';
import 'app_fonts.dart';
import 'app_colors.dart';

class AppStyles {
  AppStyles._();

  static const TextStyle logo = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeXXL,
    fontWeight: AppFonts.bold,
    color: AppColors.textBlack,
    height: 1.2,
  );

  static const TextStyle h1 = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeXL,
    fontWeight: AppFonts.bold,
    color: AppColors.textBlack,
  );

  static const TextStyle h2 = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeL,
    fontWeight: AppFonts.bold,
    color: AppColors.textBlack,
  );

  static const TextStyle h3 = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeML,
    fontWeight: AppFonts.semiBold,
    color: AppColors.textBlack,
  );

  static const TextStyle bodyLarge = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeM,
    fontWeight: AppFonts.regular,
    color: AppColors.textBlack,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeS,
    fontWeight: AppFonts.regular,
    color: AppColors.textBlack,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeXS,
    fontWeight: AppFonts.regular,
    color: AppColors.textBlue,
  );

  // Button text
  static const TextStyle button = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeM,
    fontWeight: AppFonts.semiBold,
    color: AppColors.white,
    letterSpacing: 0.1,
  );

  // labelStyle text (for form fields)
  static const TextStyle labelStyle = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeS,
    fontWeight: AppFonts.medium,
    color: AppColors.textBlack,
  );

  // Caption/Hint text
  static const TextStyle caption = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeXS,
    fontWeight: AppFonts.regular,
    color: AppColors.textLight,
  );

  // Link text
  static const TextStyle link = TextStyle(
    fontFamily: AppFonts.primary,
    fontSize: AppFonts.fontSizeS,
    fontWeight: AppFonts.medium,
    color: AppColors.darkBlue,
    decoration: TextDecoration.none,
  );

  static final inputBorder = OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: BorderSide(color: AppColors.gray, width: 1),
  );

  /// Focused input field border
  static final inputBorderFocused = OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
    borderSide: const BorderSide(color: AppColors.lightBlue, width: 2),
  );

  /// Card border
  static final cardBorder = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(20),
  );

  // ========== SHADOWS ==========

  /// Soft card shadow
  static final cardShadow = [
    BoxShadow(
      color: AppColors.lightBlue,
      blurRadius: 20,
      offset: const Offset(0, 4),
    ),
  ];

  /// Button shadow
  static final buttonShadow = [
    BoxShadow(
      color: AppColors.lightBlue,
      blurRadius: 12,
      offset: const Offset(0, 4),
    ),
  ];

  // ========== SPACING ==========

  static const double spacingXS = 4.0;
  static const double spacingS = 8.0;
  static const double spacingM = 16.0;
  static const double spacingL = 24.0;
  static const double spacingXL = 32.0;
  static const double spacingXXL = 48.0;

  // ========== BORDER RADIUS ==========

  static const double radiusS = 8.0;
  static const double radiusM = 12.0;
  static const double radiusL = 16.0;
  static const double radiusXL = 20.0;
  static const double radiusPill = 100.0;

  // ========== INPUT DECORATION ==========

  static InputDecoration inputDecoration({
    String? label,
    String? hint,
    Widget? prefixIcon,
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: prefixIcon,
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: AppColors.white,
      border: inputBorder,
      enabledBorder: inputBorder,
      focusedBorder: inputBorderFocused,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: spacingM,
        vertical: spacingM,
      ),
    );
  }

  // ========== BUTTON STYLES ==========

  /// Primary button style
  static final primaryButton = ElevatedButton.styleFrom(
    backgroundColor: AppColors.lightBlue,
    foregroundColor: AppColors.white,
    padding: const EdgeInsets.symmetric(
      horizontal: spacingL,
      vertical: spacingM,
    ),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusM)),
    elevation: 0,
    shadowColor: Colors.transparent,
  );

  /// darkBlue button style
  static final secondaryButton = ElevatedButton.styleFrom(
    backgroundColor: AppColors.white,
    foregroundColor: AppColors.lightBlue,
    padding: const EdgeInsets.symmetric(
      horizontal: spacingL,
      vertical: spacingM,
    ),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusM)),
    elevation: 0,
  );

  /// Outlined button style
  static final outlinedButton = OutlinedButton.styleFrom(
    foregroundColor: AppColors.lightBlue,
    side: const BorderSide(color: AppColors.lightBlue, width: 2),
    padding: const EdgeInsets.symmetric(
      horizontal: spacingL,
      vertical: spacingM,
    ),
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radiusM)),
  );
}

