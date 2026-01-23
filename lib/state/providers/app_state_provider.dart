import 'package:flutter/foundation.dart';
import '../../models/lecture_model.dart';
import '../../models/schedule_models.dart';
import '../../models/availability_models.dart';
import '../../utils/storage_helper.dart';

/// ✅ RECOMMENDED: Use ChangeNotifier for state management
/// This is better than static classes because:
/// 1. Widget rebuilds automatically when data changes
/// 2. Can be scoped to specific parts of the app
/// 3. Easier to test and debug
/// 4. Follows Flutter best practices
/// 5. Persists data across app restarts using SharedPreferences

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

class LectureStateProvider extends ChangeNotifier {
  String _lectureTitle = "";
  String _courseCode = "";
  int _lectureId = 0;
  int _teacherId = 0;
  String _lectureDate = "";
  String _lectureStartTime = "";
  String _lectureEndTime = "";
  String _lectureLink = "";
  String _lectureStatus = "";
  String _lectureType = "";

  // Initialize from storage
  Future<void> init() async {
    final state = await StorageHelper.getLectureState();
    if (state != null) {
      _lectureTitle = state['lectureTitle'] ?? "";
      _courseCode = state['courseCode'] ?? "";
      _lectureId = state['lectureId'] ?? 0;
      _teacherId = state['teacherId'] ?? 0;
      _lectureDate = state['lectureDate'] ?? "";
      _lectureStartTime = state['lectureStartTime'] ?? "";
      _lectureEndTime = state['lectureEndTime'] ?? "";
      _lectureLink = state['lectureLink'] ?? "";
      _lectureStatus = state['lectureStatus'] ?? "";
      _lectureType = state['lectureType'] ?? "";
      notifyListeners();
    }
  }

  // Save to storage
  Future<void> _saveToStorage() async {
    await StorageHelper.saveLectureState({
      'lectureTitle': _lectureTitle,
      'courseCode': _courseCode,
      'lectureId': _lectureId,
      'teacherId': _teacherId,
      'lectureDate': _lectureDate,
      'lectureStartTime': _lectureStartTime,
      'lectureEndTime': _lectureEndTime,
      'lectureLink': _lectureLink,
      'lectureStatus': _lectureStatus,
      'lectureType': _lectureType,
    });
  }

  // Getters
  String get lectureTitle => _lectureTitle;
  String get courseCode => _courseCode;
  int get lectureId => _lectureId;
  int get teacherId => _teacherId;
  String get lectureDate => _lectureDate;
  String get lectureStartTime => _lectureStartTime;
  String get lectureEndTime => _lectureEndTime;
  String get lectureLink => _lectureLink;
  String get lectureStatus => _lectureStatus;
  String get lectureType => _lectureType;

  // Set from API response
  Future<void> setFromCreateResponse(LectureCreateResponse response) async {
    _lectureTitle = response.title;
    _lectureId = response.lectureId;
    _teacherId = response.teacherId;
    _lectureType = response.lectureType;
    _courseCode = response.courseCode;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setFromPublishResponse(LecturePublishResponse response) async {
    _lectureTitle = response.lectureTitle;
    _courseCode = response.courseCode;
    _lectureId = response.lectureId;
    _lectureStatus = response.lectureStatus;
    _lectureDate = response.scheduledDate;
    _lectureStartTime = response.startTime;
    _lectureEndTime = response.endTime;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> updateScheduleDetails({
    required String date,
    required String startTime,
    required String endTime,
  }) async {
    _lectureDate = date;
    _lectureStartTime = startTime;
    _lectureEndTime = endTime;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> clearLecture() async {
    _lectureTitle = "";
    _courseCode = "";
    _lectureId = 0;
    _teacherId = 0;
    _lectureDate = "";
    _lectureStartTime = "";
    _lectureEndTime = "";
    _lectureLink = "";
    _lectureStatus = "";
    _lectureType = "";
    await StorageHelper.clearLectureState();
    notifyListeners();
  }
}

class ScheduleStateProvider extends ChangeNotifier {
  List<AvailabilitySlot> _studentSchedules = [];
  List<ScheduleSlot> _teacherSchedules = [];
  List<ScheduleSlot> _lectureHistory = [];

  List<AvailabilitySlot> get studentSchedules => _studentSchedules;
  List<ScheduleSlot> get teacherSchedules => _teacherSchedules;
  List<ScheduleSlot> get lectureHistory => _lectureHistory;

  void setStudentSchedules(List<AvailabilitySlot> schedules) {
    _studentSchedules = schedules;
    notifyListeners();
  }

  void setTeacherSchedules(List<ScheduleSlot> schedules) {
    _teacherSchedules = schedules;
    notifyListeners();
  }

  void setLectureHistory(List<ScheduleSlot> history) {
    _lectureHistory = history;
    notifyListeners();
  }

  void addSchedule(ScheduleSlot schedule) {
    _teacherSchedules.add(schedule);
    notifyListeners();
  }

  void removeSchedule(int scheduleId) {
    _teacherSchedules.removeWhere((s) => s.scheduleId == scheduleId);
    notifyListeners();
  }

  void clearAll() {
    _studentSchedules = [];
    _teacherSchedules = [];
    _lectureHistory = [];
    notifyListeners();
  }
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
