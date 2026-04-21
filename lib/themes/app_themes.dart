// import 'package:flutter/material.dart';
// import '../constants/app_colors.dart';

// class AppThemes {

//   // ─── DARK THEME COLORS (HoloLearn Blue Tech Palette) ──────────────────────
//   static const Color _darkBackground  = Color(0xFF0A192F); // Deep Navy
//   static const Color _darkSurface     = Color(0xFF112240); // Dark Blue
//   static const Color _darkCard        = Color(0xFF1E3A5F); // Navy Blue
//   static const Color _darkPrimary     = Color(0xFF64FFDA); // Cyan Accent
//   static const Color _darkSecondary   = Color(0xFF0EA5E9); // Bright Blue
//   static const Color _darkTextDark    = Color(0xFFCCD6F6); // Light Text
//   static const Color _darkTextLight   = Color(0xFF8892B0); // Gray Text
//   static const Color _darkBorder      = Color(0xFF233554); // Card Background

//   // ─── SHARED ───────────────────────────────────────────────────────────────
//   static const Color _error           = Color(0xFFEF4444);
//   static const Color _success         = Color(0xFF10B981);

//   // =========================================================================
//   // LIGHT THEME (uses your existing AppColors)
//   // =========================================================================
//   static ThemeData get lightTheme => ThemeData(
//     brightness: Brightness.light,
//     useMaterial3: true,

//     colorScheme: ColorScheme.light(
//       primary:          AppColors.lightBlue,
//       secondary:        AppColors.lightBlue,
//       surface:          AppColors.white,
//       background:       AppColors.lightBackground,
//       error:            _error,
//       onPrimary:        AppColors.white,
//       onSecondary:      AppColors.white,
//       onSurface:        AppColors.textBlue,
//       onBackground:     AppColors.textBlue,
//       onError:          AppColors.white,
//     ),

//     scaffoldBackgroundColor: AppColors.lightBackground,

//     appBarTheme: AppBarTheme(
//       backgroundColor:  AppColors.lightBlue,
//       foregroundColor:  AppColors.white,
//       elevation:        0,
//       centerTitle:      false,
//       iconTheme:        const IconThemeData(color: AppColors.white),
//       titleTextStyle:   const TextStyle(
//         color:          AppColors.white,
//         fontSize:       20,
//         fontWeight:     FontWeight.w600,
//       ),
//     ),

//     cardTheme: CardThemeData(
//       color:    AppColors.white,
//       elevation: 2,
//       shape:    RoundedRectangleBorder(
//         borderRadius: BorderRadius.circular(16),
//       ),
//       shadowColor: Colors.black.withValues(alpha: 0.08),
//     ),

//     inputDecorationTheme: InputDecorationTheme(
//       filled:       true,
//       fillColor:    AppColors.white,
//       contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
//       border: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: BorderSide(color: AppColors.gray.withOpacity(0.3)),
//       ),
//       enabledBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: BorderSide(color: AppColors.gray.withOpacity(0.3)),
//       ),
//       focusedBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: AppColors.lightBlue, width: 2),
//       ),
//       errorBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: _error),
//       ),
//       labelStyle: TextStyle(color: AppColors.textLight),
//       hintStyle:  TextStyle(color: AppColors.textLight.withValues(alpha: 0.6)),
//     ),

//     elevatedButtonTheme: ElevatedButtonThemeData(
//       style: ElevatedButton.styleFrom(
//         backgroundColor: AppColors.lightBlue,
//         foregroundColor: AppColors.white,
//         elevation:       0,
//         padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
//         shape: RoundedRectangleBorder(
//           borderRadius: BorderRadius.circular(10),
//         ),
//         textStyle: const TextStyle(
//           fontSize:     16,
//           fontWeight:   FontWeight.w600,
//         ),
//       ),
//     ),

//     textButtonTheme: TextButtonThemeData(
//       style: TextButton.styleFrom(
//         foregroundColor: AppColors.lightBlue,
//       ),
//     ),

//     checkboxTheme: CheckboxThemeData(
//       fillColor: MaterialStateProperty.resolveWith((s) =>
//         s.contains(MaterialState.selected) ? AppColors.lightBlue : Colors.transparent,
//       ),
//       checkColor: MaterialStateProperty.all(AppColors.white),
//       side: BorderSide(color: AppColors.gray),
//       shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
//     ),

//     dividerTheme: DividerThemeData(
//       color:     AppColors.gray.withValues(alpha: 0.3),
//       thickness: 1,
//     ),

//     iconTheme: IconThemeData(color: AppColors.textBlack),

//     textTheme: TextTheme(
//       displayLarge:  TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.bold),
//       headlineLarge: TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.w700),
//       headlineMedium:TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.w600),
//       titleLarge:    TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.w600),
//       titleMedium:   TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.w500),
//       bodyLarge:     TextStyle(color: AppColors.textBlack),
//       bodyMedium:    TextStyle(color: AppColors.textBlack),
//       bodySmall:     TextStyle(color: AppColors.textLight),
//       labelLarge:    TextStyle(color: AppColors.textBlack, fontWeight: FontWeight.w600),
//       labelMedium:   TextStyle(color: AppColors.textLight),
//     ),
//   );

//   // =========================================================================
//   // DARK THEME (HoloLearn Blue Tech Palette)
//   // =========================================================================
//   static ThemeData get darkTheme => ThemeData(
//     brightness: Brightness.dark,
//     useMaterial3: true,

//     colorScheme: const ColorScheme.dark(
//       primary:          _darkPrimary,
//       secondary:        _darkSecondary,
//       surface:          _darkSurface,
//       background:       _darkBackground,
//       error:            _error,
//       onPrimary:        _darkBackground,
//       onSecondary:      _darkBackground,
//       onSurface:        _darkTextDark,
//       onBackground:     _darkTextDark,
//       onError:          Colors.white,
//     ),

//     scaffoldBackgroundColor: _darkBackground,

//     appBarTheme: const AppBarTheme(
//       backgroundColor:  _darkSurface,
//       foregroundColor:  _darkTextDark,
//       elevation:        0,
//       centerTitle:      false,
//       iconTheme:        IconThemeData(color: _darkPrimary),
//       titleTextStyle:   TextStyle(
//         color:          _darkTextDark,
//         fontSize:       20,
//         fontWeight:     FontWeight.w600,
//       ),
//     ),

//     cardTheme: CardThemeData(
//       color:    _darkCard,
//       elevation: 0,
//       shape:    RoundedRectangleBorder(
//         borderRadius: BorderRadius.circular(16),
//         side: const BorderSide(color: _darkBorder),
//       ),
//     ),

//     inputDecorationTheme: InputDecorationTheme(
//       filled:       true,
//       fillColor:    _darkSurface,
//       contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
//       border: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: _darkBorder),
//       ),
//       enabledBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: _darkBorder),
//       ),
//       focusedBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: _darkPrimary, width: 2),
//       ),
//       errorBorder: OutlineInputBorder(
//         borderRadius: BorderRadius.circular(10),
//         borderSide: const BorderSide(color: _error),
//       ),
//       labelStyle: const TextStyle(color: _darkTextLight),
//       hintStyle:  TextStyle(color: _darkTextLight.withValues(alpha: 0.6)),
//     ),

//     elevatedButtonTheme: ElevatedButtonThemeData(
//       style: ElevatedButton.styleFrom(
//         backgroundColor: _darkPrimary,
//         foregroundColor: _darkBackground,
//         elevation:       0,
//         padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
//         shape: RoundedRectangleBorder(
//           borderRadius: BorderRadius.circular(10),
//         ),
//         textStyle: const TextStyle(
//           fontSize:     16,
//           fontWeight:   FontWeight.w600,
//         ),
//       ),
//     ),

//     textButtonTheme: TextButtonThemeData(
//       style: TextButton.styleFrom(
//         foregroundColor: _darkPrimary,
//       ),
//     ),

//     checkboxTheme: CheckboxThemeData(
//       fillColor: MaterialStateProperty.resolveWith((s) =>
//         s.contains(MaterialState.selected) ? _darkPrimary : Colors.transparent,
//       ),
//       checkColor: MaterialStateProperty.all(_darkBackground),
//       side: const BorderSide(color: _darkTextLight),
//       shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
//     ),

//     dividerTheme: const DividerThemeData(
//       color:     _darkBorder,
//       thickness: 1,
//     ),

//     iconTheme: const IconThemeData(color: _darkPrimary),

//     textTheme: const TextTheme(
//       displayLarge:  TextStyle(color: _darkTextDark, fontWeight: FontWeight.bold),
//       headlineLarge: TextStyle(color: _darkTextDark, fontWeight: FontWeight.w700),
//       headlineMedium:TextStyle(color: _darkTextDark, fontWeight: FontWeight.w600),
//       titleLarge:    TextStyle(color: _darkTextDark, fontWeight: FontWeight.w600),
//       titleMedium:   TextStyle(color: _darkTextDark, fontWeight: FontWeight.w500),
//       bodyLarge:     TextStyle(color: _darkTextDark),
//       bodyMedium:    TextStyle(color: _darkTextDark),
//       bodySmall:     TextStyle(color: _darkTextLight),
//       labelLarge:    TextStyle(color: _darkTextDark, fontWeight: FontWeight.w600),
//       labelMedium:   TextStyle(color: _darkTextLight),
//     ),
//   );
// }
