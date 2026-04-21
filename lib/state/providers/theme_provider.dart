// import 'package:flutter/material.dart';
// import '../../utils/storage_helper.dart';

// class ThemeProvider extends ChangeNotifier {
//   ThemeMode _themeMode = ThemeMode.light;

//   ThemeMode get themeMode => _themeMode;
//   bool get isDark  => _themeMode == ThemeMode.dark;
//   bool get isLight => _themeMode == ThemeMode.light;

//   /// Load saved theme on app start
//   Future<void> init() async {
//     final saved = await StorageHelper.getThemeMode();
//     _themeMode = saved == 'dark' ? ThemeMode.dark : ThemeMode.light;
//     notifyListeners();
//   }

//   /// Toggle between light and dark
//   Future<void> toggle() async {
//     _themeMode = isDark ? ThemeMode.light : ThemeMode.dark;
//     await StorageHelper.saveThemeMode(isDark ? 'dark' : 'light');
//     notifyListeners();
//   }

//   Future<void> setDark()  async {
//     _themeMode = ThemeMode.dark;
//     await StorageHelper.saveThemeMode('dark');
//     notifyListeners();
//   }

//   Future<void> setLight() async {
//     _themeMode = ThemeMode.light;
//     await StorageHelper.saveThemeMode('light');
//     notifyListeners();
//   }
// }