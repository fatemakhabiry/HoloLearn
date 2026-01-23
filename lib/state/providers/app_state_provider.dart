import 'package:flutter/foundation.dart';
import '../../utils/storage_helper.dart';


class AppStateProvider extends ChangeNotifier {
  // Auth state
  String _email = "";
  String _userName = "";
  String _userRole = "";
  String _accessToken = "";
  bool _isFirstTimeLogin = false;
  DateTime _linkSentTime = DateTime.now();
  String _otp = '';
  int _lectureId = 0;

  // Getters
  String get email => _email;
  String get userName => _userName;
  String get userRole => _userRole;
  String get accessToken => _accessToken;
  bool get isFirstTimeLogin => _isFirstTimeLogin;
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
    _otp = '';
    await StorageHelper.clearAuth();
    notifyListeners();
  }

  // Check if user is logged in
  bool get isLoggedIn => _accessToken.isNotEmpty;
}



/// Usage in main.dart:
/// ```dart
/// void main() {
///   runApp(
///     MultiProvider(
///       providers: [
///         ChangeNotifierProvider(create: (_) => AppStateProvider()),
///         ChangeNotifierProvider(create: (_) => LectureStateProvider()),
///         ChangeNotifierProvider(create: (_) => ScheduleStateProvider()),
///       ],
///       child: MyApp(),
///     ),
///   );
/// }
/// ```
///
/// Usage in widgets:
/// ```dart
/// // Read value
/// final token = context.read<AppStateProvider>().accessToken;
/// 
/// // Listen to changes
/// final userName = context.watch<AppStateProvider>().userName;
/// 
/// // Update value
/// context.read<AppStateProvider>().setAccessToken(newToken);
/// ```
