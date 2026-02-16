import 'package:flutter/foundation.dart';
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
  Future<void> clearAuth({bool keepEmail = true}) async {
    _email = keepEmail ? _email : "";
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