import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class StorageService {
  // Secure storage for sensitive data
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
  );

  // Storage keys
  static const String _keyAccessToken = 'access_token';
  static const String _keyRefreshToken = 'refresh_token';
  static const String _keyUserId = 'user_id';
  static const String _keyUserEmail = 'user_email';
  static const String _keyUserRole = 'user_role';
  static const String _keyUserName = 'user_name';
  static const String _keyRememberMe = 'remember_me';
  static const String _keyIsLoggedIn = 'is_logged_in';
  static const String _keyLastEmail = 'last_email'; // For pre-filling

  // ========== SAVE LOGIN DATA ==========
  
  /// Save complete login session
  static Future<void> saveLoginData({
    required String accessToken,
    String? refreshToken,
    required int userId,
    required String email,
    required String role,
    String? userName,
    required bool rememberMe,
  }) async {
    try {
      // Save tokens securely (encrypted)
      await _secureStorage.write(key: _keyAccessToken, value: accessToken);
      if (refreshToken != null) {
        await _secureStorage.write(key: _keyRefreshToken, value: refreshToken);
      }
      
      // Save user info in shared preferences
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_keyUserId, userId);
      await prefs.setString(_keyUserEmail, email);
      await prefs.setString(_keyUserRole, role);
      if (userName != null) {
        await prefs.setString(_keyUserName, userName);
      }
      await prefs.setBool(_keyRememberMe, rememberMe);
      await prefs.setBool(_keyIsLoggedIn, true);
      await prefs.setString(_keyLastEmail, email);
      
      print('✅ Login data saved successfully');
    } catch (e) {
      print('❌ Error saving login data: $e');
      rethrow;
    }
  }

  // ========== GET TOKENS ==========
  
  static Future<String?> getAccessToken() async {
    try {
      return await _secureStorage.read(key: _keyAccessToken);
    } catch (e) {
      print('❌ Error reading access token: $e');
      return null;
    }
  }

  static Future<String?> getRefreshToken() async {
    try {
      return await _secureStorage.read(key: _keyRefreshToken);
    } catch (e) {
      print('❌ Error reading refresh token: $e');
      return null;
    }
  }

  // ========== GET USER DATA ==========
  
  static Future<int?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_keyUserId);
  }

  static Future<String?> getUserEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyUserEmail);
  }

  static Future<String?> getUserRole() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyUserRole);
  }

  static Future<String?> getUserName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyUserName);
  }

  static Future<String?> getLastEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keyLastEmail);
  }

  // ========== CHECK LOGIN STATE ==========
  
  /// Check if user is logged in and has valid token
  static Future<bool> isLoggedIn() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isLoggedIn = prefs.getBool(_keyIsLoggedIn) ?? false;
      final hasToken = await getAccessToken() != null;
      final rememberMe = prefs.getBool(_keyRememberMe) ?? false;
      
      return isLoggedIn && hasToken && rememberMe;
    } catch (e) {
      print('❌ Error checking login state: $e');
      return false;
    }
  }

  static Future<bool> shouldRememberUser() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyRememberMe) ?? false;
  }

  // ========== UPDATE DATA ==========
  
  static Future<void> updateAccessToken(String newToken) async {
    await _secureStorage.write(key: _keyAccessToken, value: newToken);
  }

  // ========== LOGOUT ==========
  
  /// Clear login data but keep last email for convenience
  static Future<void> logout({bool clearEmail = false}) async {
    try {
      // Clear secure storage
      await _secureStorage.delete(key: _keyAccessToken);
      await _secureStorage.delete(key: _keyRefreshToken);
      
      // Get last email before clearing (if needed)
      final prefs = await SharedPreferences.getInstance();
      final lastEmail = clearEmail ? null : prefs.getString(_keyUserEmail);
      
      // Clear user data
      await prefs.remove(_keyUserId);
      await prefs.remove(_keyUserEmail);
      await prefs.remove(_keyUserRole);
      await prefs.remove(_keyUserName);
      await prefs.remove(_keyIsLoggedIn);
      await prefs.remove(_keyRememberMe);
      
      // Restore last email if not clearing
      if (lastEmail != null && !clearEmail) {
        await prefs.setString(_keyLastEmail, lastEmail);
      }
      
      print('✅ Logged out successfully');
    } catch (e) {
      print('❌ Error during logout: $e');
      rethrow;
    }
  }

  /// Clear all data including last email
  static Future<void> clearAllData() async {
    await _secureStorage.deleteAll();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  // ========== GET COMPLETE USER DATA ==========
  
  static Future<Map<String, dynamic>?> getUserData() async {
    final token = await getAccessToken();
    final userId = await getUserId();
    final email = await getUserEmail();
    final role = await getUserRole();
    final userName = await getUserName();
    
    if (token == null || userId == null) return null;
    
    return {
      'accessToken': token,
      'userId': userId,
      'email': email,
      'role': role,
      'userName': userName,
    };
  }
}
