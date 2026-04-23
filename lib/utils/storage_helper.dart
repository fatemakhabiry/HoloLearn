import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';

/// Helper class for persisting data using SharedPreferences and Secure Storage
/// This allows data to survive app restarts
class StorageHelper {
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  // Keys for storing data
  static const String _accessTokenKey = 'access_token';
  static const String _emailKey = 'email';
  static const String _passwordKey = 'password';
  static const String _userNameKey = 'user_name';
  static const String _userRoleKey = 'user_role';
  static const String _isFirstTimeLoginKey = 'is_first_time_login';
  static const String _lectureStateKey = 'lecture_state';
  static const String _keyRememberMe = 'remember_me';

  // ========== REMEMBER ME ==========

  /// Save "Remember Me" preference
  static Future<void> saveRememberMe(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyRememberMe, value);
  }

  /// Get "Remember Me" preference
  static Future<bool> getRememberMe() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyRememberMe) ?? false;
  }

  /// Check if user should auto-login
  static Future<bool> shouldAutoLogin() async {
    final rememberMe = await getRememberMe();
    final token = await getAccessToken();
    return rememberMe && token != null && token.isNotEmpty;
  }

  // ========== Auth Data ==========

  /// Save access token in secure storage (encrypted)
  static Future<void> saveAccessToken(String token) async {
    await _secureStorage.write(key: _accessTokenKey, value: token);
  }

  /// Get access token from secure storage
  static Future<String?> getAccessToken() async {
    return await _secureStorage.read(key: _accessTokenKey);
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

  static Future<void> savePassword(String password) async {
    await _secureStorage.write(key: _passwordKey, value: password);
  }

  static Future<String?> getPassword() async {
    return await _secureStorage.read(key: _passwordKey);
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

  // ========== Clear Data ==========

  /// Clear all stored data (useful for complete logout)
  static Future<void> clearAll() async {
    await _secureStorage.deleteAll();
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
static const String _processingStateKey = 'processing_state';

static Future<void> saveProcessingState(Map<String, dynamic> data) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(_processingStateKey, json.encode(data));
}

static Future<Map<String, dynamic>?> getProcessingState() async {
  final prefs = await SharedPreferences.getInstance();
  final jsonString = prefs.getString(_processingStateKey);
  if (jsonString != null) {
    return json.decode(jsonString) as Map<String, dynamic>;
  }
  return null;
}

static Future<void> clearProcessingState() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove(_processingStateKey);
}
  /// Clear only auth data (with option to keep email)
  // static Future<void> clearAuth({bool keepEmail = true}) async {
  //   // Clear secure storage (token)
  //   await _secureStorage.delete(key: _accessTokenKey);

  //   final prefs = await SharedPreferences.getInstance();

  //   // Save email before clearing if needed
  //   final lastEmail = keepEmail ? prefs.getString(_emailKey) : null;

  //   // Clear auth data
  //   await prefs.remove(_userNameKey);
  //   await prefs.remove(_userRoleKey);
  //   await prefs.remove(_isFirstTimeLoginKey);
  //   await prefs.remove(_keyRememberMe);

  //   if (!keepEmail) {
  //     await prefs.remove(_emailKey);
  //   } else if (lastEmail != null) {
  //     // Restore email for next login
  //     await prefs.setString(_emailKey, lastEmail);
  //   }
  // }
  static Future<void> clearAuth({bool keepEmail = true}) async {
  await _secureStorage.delete(key: _accessTokenKey);

  // Only clear password if not remembering
  final prefs = await SharedPreferences.getInstance();
  final rememberMe = prefs.getBool(_keyRememberMe) ?? false;
  if (!rememberMe) {
    await _secureStorage.delete(key: _passwordKey);
  }

  final lastEmail = keepEmail ? prefs.getString(_emailKey) : null;

  await prefs.remove(_userNameKey);
  await prefs.remove(_userRoleKey);
  await prefs.remove(_isFirstTimeLoginKey);
  await prefs.remove(_keyRememberMe);

  if (!keepEmail) {
    await prefs.remove(_emailKey);
  } else if (lastEmail != null) {
    await prefs.setString(_emailKey, lastEmail);
  }
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

  static const String _sessionIdKey = 'session_id';

static Future<void> saveSessionId(int sessionId) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setInt(_sessionIdKey, sessionId);
}

static Future<int?> getSessionId() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getInt(_sessionIdKey);
}

  static Future<void> clearSessionId() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove(_sessionIdKey);
}static const String _lectureSessionMapKey = 'lecture_session_map';

/// Save a lectureId → sessionId mapping
static Future<void> saveLectureSessionId(int lectureId, int sessionId) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureSessionMapKey);
  
  Map<String, dynamic> map = {};
  if (existing != null) {
    map = json.decode(existing) as Map<String, dynamic>;
  }
  
  map[lectureId.toString()] = sessionId;
  await prefs.setString(_lectureSessionMapKey, json.encode(map));
}

/// Get sessionId for a given lectureId
static Future<int?> getSessionIdForLecture(int lectureId) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureSessionMapKey);
  if (existing == null) return null;
  
  final map = json.decode(existing) as Map<String, dynamic>;
  final value = map[lectureId.toString()];
  return value as int?;
}

/// Clear a single lecture-session mapping after deletion
static Future<void> clearLectureSessionId(int lectureId) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureSessionMapKey);
  if (existing == null) return;
  
  final map = json.decode(existing) as Map<String, dynamic>;
  map.remove(lectureId.toString());
  await prefs.setString(_lectureSessionMapKey, json.encode(map));
}
static const String _lectureTypeMapKey = 'lecture_type_map';

static Future<void> saveLectureType(int lectureId, String type) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureTypeMapKey);
  
  Map<String, dynamic> map = {};
  if (existing != null) {
    map = json.decode(existing) as Map<String, dynamic>;
  }
  
  map[lectureId.toString()] = type;
  await prefs.setString(_lectureTypeMapKey, json.encode(map));
}

static Future<String?> getLectureType(int lectureId) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureTypeMapKey);
  if (existing == null) return null;
  
  final map = json.decode(existing) as Map<String, dynamic>;
  return map[lectureId.toString()] as String?;
}

static Future<void> clearLectureType(int lectureId) async {
  final prefs = await SharedPreferences.getInstance();
  final existing = prefs.getString(_lectureTypeMapKey);
  if (existing == null) return;
  
  final map = json.decode(existing) as Map<String, dynamic>;
  map.remove(lectureId.toString());
  await prefs.setString(_lectureTypeMapKey, json.encode(map));
}
}
