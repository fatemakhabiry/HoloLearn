import 'package:flutter/material.dart';
import '../../utils/storage_helper.dart';
 
class ThemeProvider extends ChangeNotifier {
  ThemeMode _themeMode = ThemeMode.light;
 
  ThemeMode get themeMode => _themeMode;
  bool get isDark => _themeMode == ThemeMode.dark;
 
  Future<void> init() async {
    final isDark = await StorageHelper.getIsDarkMode();
    _themeMode = isDark ? ThemeMode.dark : ThemeMode.light;
    notifyListeners();
  }
 
  Future<void> toggle() async {
    _themeMode =
        _themeMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light;
    await StorageHelper.saveIsDarkMode(_themeMode == ThemeMode.dark);
    notifyListeners();
  }
}