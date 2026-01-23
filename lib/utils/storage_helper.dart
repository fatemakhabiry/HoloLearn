import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';

/// Helper class for persisting data using SharedPreferences
/// This allows data to survive app restarts
class StorageHelper {
  // Keys for storing data
  static const String _accessTokenKey = 'access_token';
  static const String _emailKey = 'email';
  static const String _userNameKey = 'user_name';
  static const String _userRoleKey = 'user_role';
  static const String _isFirstTimeLoginKey = 'is_first_time_login';
  static const String _lectureStateKey = 'lecture_state';

  // ========== Auth Data ==========
  
  static Future<void> saveAccessToken(String token) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_accessTokenKey, token);
  }

  static Future<String?> getAccessToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_accessTokenKey);
  }

  static Future<void> saveEmail(String email) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_emailKey, email);
  }

  static Future<String?> getEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_emailKey);
  }

  static Future<void> saveUserName(String userName) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userNameKey, userName);
  }

  static Future<String?> getUserName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userNameKey);
  }

  static Future<void> saveUserRole(String userRole) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userRoleKey, userRole);
  }

  static Future<String?> getUserRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_userRoleKey);
  }

  static Future<void> saveFirstTimeLogin(bool isFirstTime) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_isFirstTimeLoginKey, isFirstTime);
  }

  static Future<bool> getFirstTimeLogin() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_isFirstTimeLoginKey) ?? false;
  }

  // ========== Lecture State ==========
  
  static Future<void> saveLectureState(Map<String, dynamic> lectureData) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lectureStateKey, json.encode(lectureData));
  }

  static Future<Map<String, dynamic>?> getLectureState() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_lectureStateKey);
    if (jsonString != null) {
      return json.decode(jsonString) as Map<String, dynamic>;
    }
    return null;
  }

  // ========== Clear All Data ==========
  
  /// Clear all stored data (useful for logout)
  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  /// Clear only auth data
  static Future<void> clearAuth() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_emailKey);
    await prefs.remove(_userNameKey);
    await prefs.remove(_userRoleKey);
    await prefs.remove(_isFirstTimeLoginKey);
  }

  /// Clear only lecture state
  static Future<void> clearLectureState() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_lectureStateKey);
  }

  // ========== Check if logged in ==========
  
  static Future<bool> isLoggedIn() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }
}
