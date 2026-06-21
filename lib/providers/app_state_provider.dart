import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../services/auth_service.dart';
import '../../utils/storage_helper.dart';

class AppStateProvider extends ChangeNotifier {
  // Auth state
  String _email = "";
  String _userName = "";
  String _userRole = "";
  String _accessToken = "";
  bool _isFirstTimeLogin = false;
  bool _rememberMe = false; // NEW
  DateTime _linkSentTime = DateTime.now();
  String _otp = '';
  int _lectureId = 0;

  // Getters
  String get email => _email;
  String get userName => _userName;
  String get userRole => _userRole;
  String get accessToken => _accessToken;
  bool get isFirstTimeLogin => _isFirstTimeLogin;
  bool get rememberMe => _rememberMe; // NEW
  DateTime get linkSentTime => _linkSentTime;
  String get otp => _otp;
  int get lectureId => _lectureId;

  // Initialize from storage on app start
  Future<void> init() async {
    _email = await StorageHelper.getEmail() ?? "";
    _userName = await StorageHelper.getUserName() ?? "";
    _userRole = await StorageHelper.getUserRole() ?? "";
    _accessToken = await StorageHelper.getAccessToken() ?? "";
    _isFirstTimeLogin = await StorageHelper.getFirstTimeLogin();
    _rememberMe = await StorageHelper.getRememberMe(); // NEW
    notifyListeners();
  }

  Future<bool> tryAutoLogin() async {
    // final shouldAutoLogin = await StorageHelper.shouldAutoLogin();
    // if (!shouldAutoLogin) return false;

    final savedEmail = await StorageHelper.getEmail();
    final savedPassword = await StorageHelper.getPassword();

    if (savedEmail == null || savedEmail.isEmpty) return false;
    if (savedPassword == null || savedPassword.isEmpty) return false;

    try {
      final data = await AuthService.login(
        email: savedEmail,
        password: savedPassword,
      );
      setUserData(
        accessToken: data['access_token'],
        email: data['user']['email'],
        userName: data['user']['full_name'],
        role: data['user']['role'],
      );
      if (data['user']['role'] == 'teacher') {
      final sessionId = data['user']['latest_session_id'];

      if (sessionId != null) {
        await StorageHelper.saveOngoingSessionId(sessionId as int);
      }
      }
      return true;
    } catch (_) {
      Exception('Auto-login failed: Please check your credentials.');
      return false;
    }
  }

  Future<void> setUserData({
    required String email,
    required String userName,
    required String role,
    required String accessToken,
  }) async {
    _email = email;
    _userName = userName;
    _userRole = role;
    _accessToken = accessToken;

    await StorageHelper.saveEmail(email);
    await StorageHelper.saveUserName(userName);
    await StorageHelper.saveUserRole(role);
    await StorageHelper.saveAccessToken(accessToken);

    notifyListeners();
  }

  // Setters with notification and persistence
  Future<void> setEmail(String value) async {
    _email = value;
    await StorageHelper.saveEmail(value);
    notifyListeners();
  }

  Future<void> setUserName(String value) async {
    _userName = value;
    await StorageHelper.saveUserName(value);
    notifyListeners();
  }

  Future<void> setUserRole(String value) async {
    _userRole = value;
    await StorageHelper.saveUserRole(value);
    notifyListeners();
  }

  Future<void> setAccessToken(String value) async {
    _accessToken = value;
    await StorageHelper.saveAccessToken(value);
    notifyListeners();
  }

  Future<void> setFirstTimeLogin(bool value) async {
    _isFirstTimeLogin = value;
    await StorageHelper.saveFirstTimeLogin(value);
    notifyListeners();
  }

  // NEW: Remember Me setter
  Future<void> setRememberMe(bool value) async {
    _rememberMe = value;
    await StorageHelper.saveRememberMe(value);
    notifyListeners();
  }

  void setOtp(String value) {
    _otp = value;
    notifyListeners();
  }

  void setLectureId(int value) {
    _lectureId = value;
    notifyListeners();
  }

  void updateLinkSentTime() {
    _linkSentTime = DateTime.now();
    notifyListeners();
  }

  // Clear all auth data on logout
  Future<void> clearAuth() async {
    _email = "";
    _userName = "";
    _userRole = "";
    _accessToken = "";
    _isFirstTimeLogin = false;
    _rememberMe = false; // NEW
    _otp = '';
    await StorageHelper.clearAuth();
    notifyListeners();
  }

  // Check if user is logged in
  bool get isLoggedIn => _accessToken.isNotEmpty;

  // NEW: Check if should auto-login
  Future<bool> shouldAutoLogin() async {
    return await StorageHelper.shouldAutoLogin();
  }
}
