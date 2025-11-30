import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

class StorageService {
  static StorageService? _instance;
  static SharedPreferences? _preferences;

  StorageService._();

  static Future<StorageService> getInstance() async {
    _instance ??= StorageService._();
    _preferences ??= await SharedPreferences.getInstance();
    return _instance!;
  }

  // Save token
  Future<bool> saveToken(String token) async {
    return await _preferences!.setString(ApiConfig.accessTokenKey, token);
  }

  // Get token
  String? getToken() {
    return _preferences!.getString(ApiConfig.accessTokenKey);
  }

  // Save user data
  Future<bool> saveUserData({
    // required int userId,
    required String email,
    required String role,
    required String name,
  }) async {
    // await _preferences!.setInt(ApiConfig.userIdKey, userId);
    await _preferences!.setString(ApiConfig.userEmailKey, email);
    await _preferences!.setString(ApiConfig.userRoleKey, role);
    await _preferences!.setString(ApiConfig.userNameKey, name);
    return true;
  }

  // Get user data
  Map<String, dynamic>? getUserData() {
    // final userId = _preferences!.getInt(ApiConfig.userIdKey);
    // if (userId == null) return null;

    return {
      // 'userId': userId,
      'email': _preferences!.getString(ApiConfig.userEmailKey),
      'role': _preferences!.getString(ApiConfig.userRoleKey),
      'name': _preferences!.getString(ApiConfig.userNameKey),
    };
  }

  // Check if user is logged in
  bool isLoggedIn() {
    return getToken() != null;
  }

  // Get user role
  String? getUserRole() {
    return _preferences!.getString(ApiConfig.userRoleKey);
  }

  // Clear all data (logout)
  Future<bool> clearAll() async {
    return await _preferences!.clear();
  }

  // Clear specific keys
  Future<bool> clearAuth() async {
    await _preferences!.remove(ApiConfig.accessTokenKey);
    // await _preferences!.remove(ApiConfig.userIdKey);
    await _preferences!.remove(ApiConfig.userEmailKey);
    await _preferences!.remove(ApiConfig.userRoleKey);
    await _preferences!.remove(ApiConfig.userNameKey);
    return true;
  }
}
