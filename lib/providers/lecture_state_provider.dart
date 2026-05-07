import 'package:flutter/foundation.dart';
import '../../models/lecture_models.dart';
import '../../models/schedule_models.dart';
import '../../models/availability_models.dart';
import '../../utils/storage_helper.dart';

class LectureStateProvider extends ChangeNotifier {

  // ── Two separate session IDs ──────────────────────────────────────────────
  //
  // _sessionId       : temporary ID used when fetching a resource file from
  //                    lecture history (read-only context). Does NOT persist.
  //
  // _ongoingSessionId: the live session that is currently being processed
  //                    (created → preview → approve → processing).
  //                    Set when a new session starts, cleared ONLY after
  //                    approve() succeeds. Nullable so screens can gate on it.
  //
  int _sessionId = 0;
  int? _ongoingSessionId; // null  = no session in progress
  String _lectureTitle = '';
  String _courseCode = '';
  int _lectureId = 0;
  int _teacherId = 0;
  String _lectureDate = '';
  String _lectureStartTime = '';
  String _lectureEndTime = '';
  String _lectureLink = '';
  String _lectureStatus = '';
  String _lectureType = '';
  bool _isRescheduling = false;
  
  // ── Setters ──────────────────────────────────────────────────────────────

  Future<void> setLectureTitle(String title) async {
    _lectureTitle = title;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setCourseCode(String courseCode) async {
    _courseCode = courseCode;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureId(int lectureId) async {
    _lectureId = lectureId;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setSessionId(int sessionId) async {
    _sessionId = sessionId;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setTeacherId(int teacherId) async {
    _teacherId = teacherId;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureDate(String date) async {
    _lectureDate = date;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureStartTime(String startTime) async {
    _lectureStartTime = startTime;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureEndTime(String endTime) async {
    _lectureEndTime = endTime;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureLink(String link) async {
    _lectureLink = link;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureStatus(String status) async {
    _lectureStatus = status;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setLectureType(String type) async {
    _lectureType = type;
    await _saveToStorage();
    notifyListeners();
  }

  Future<void> setIsRescheduling(bool value) async {
    _isRescheduling = value;
    await _saveToStorage();
    notifyListeners();
  }
   Future<void> startOngoingSession(int sessionId) async {
    _ongoingSessionId = sessionId;
    // Also set _sessionId so existing code that reads sessionId still works
    _sessionId = sessionId;
    await _saveToStorage();
    await StorageHelper.saveOngoingSessionId(sessionId);
    notifyListeners();
  }
 
  /// Clears the ongoing session — call this after approve() succeeds.
  Future<void> clearOngoingSession() async {
    _ongoingSessionId = null;
    await StorageHelper.clearOngoingSessionId();
    await _saveToStorage();
    notifyListeners();
  }
 

  // ── Getters ──────────────────────────────────────────────────────────────
    /// The ongoing live session. Null when no session is in progress.
  int? get ongoingSessionId => _ongoingSessionId;
  /// True when a lecture session is actively being processed.
  bool get hasOngoingSession => _ongoingSessionId != null;
  String get lectureTitle => _lectureTitle;
  String get courseCode => _courseCode;
  int get lectureId => _lectureId;
  int get sessionId => _sessionId;
  int get teacherId => _teacherId;
  String get lectureDate => _lectureDate;
  String get lectureStartTime => _lectureStartTime;
  String get lectureEndTime => _lectureEndTime;
  String get lectureLink => _lectureLink;
  String get lectureStatus => _lectureStatus;
  String get lectureType => _lectureType;
  bool get isRescheduling => _isRescheduling;
  // ── Init / Storage ────────────────────────────────────────────────────────

    Future<void> init() async {
    final state = await StorageHelper.getLectureState();
    if (state != null) {
      _lectureTitle = state['lectureTitle'] ?? '';
      _courseCode = state['courseCode'] ?? '';
      _lectureId = state['lectureId'] ?? 0;
      _teacherId = state['teacherId'] ?? 0;
      _lectureDate = state['lectureDate'] ?? '';
      _lectureStartTime = state['lectureStartTime'] ?? '';
      _lectureEndTime = state['lectureEndTime'] ?? '';
      _lectureLink = state['lectureLink'] ?? '';
      _lectureStatus = state['lectureStatus'] ?? '';
      _lectureType = state['lectureType'] ?? '';
      _isRescheduling = state['isRescheduling'] ?? false;
    }
 
    // Restore sessionId (history lookup)
    final storedSessionId = await StorageHelper.getSessionId();
    if (storedSessionId != null) {
      _sessionId = storedSessionId;
    }
 
    // Restore ongoingSessionId independently
    final storedOngoing = await StorageHelper.getOngoingSessionId();
    if (storedOngoing != null) {
      _ongoingSessionId = storedOngoing;
    }
 
    notifyListeners();
  }
 
  Future<void> _saveToStorage() async {
    await StorageHelper.saveLectureState({
      'lectureTitle': _lectureTitle,
      'courseCode': _courseCode,
      'lectureId': _lectureId,
      'sessionId': _sessionId,
      'teacherId': _teacherId,
      'lectureDate': _lectureDate,
      'lectureStartTime': _lectureStartTime,
      'lectureEndTime': _lectureEndTime,
      'lectureLink': _lectureLink,
      'lectureStatus': _lectureStatus,
      'lectureType': _lectureType,
      'isRescheduling': _isRescheduling,
      // NOTE: ongoingSessionId is stored separately via StorageHelper
    });
  }
 


  // ── Setters ───────────────────────────────────────────────────────────────

  Future<void> setSession({
    required int sessionId,
    required int lectureId,
  }) async {
    _sessionId = sessionId;
    _lectureId = lectureId;
    await _saveToStorage();
    notifyListeners();
  }

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

  Future<void> setFromScheduleSlot(ScheduleSlot scheduleSlot) async {
    _lectureId = scheduleSlot.lectureId ?? 0;
    _lectureTitle = scheduleSlot.lectureTitle;
    _courseCode = scheduleSlot.courseCode;
    _lectureStatus = scheduleSlot.status;
    _lectureType = scheduleSlot.lectureType ?? '';

    // Parse date from the date field, falling back to extracting it from startTime
    String extractedDate = scheduleSlot.date ?? '';
    if (extractedDate.isEmpty && scheduleSlot.startTime.isNotEmpty) {
      try {
        final dt = DateTime.parse(scheduleSlot.startTime);
        extractedDate =
            '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
      } catch (_) {}
    }
    _lectureDate = extractedDate;

    _lectureStartTime = _extractTimeFromISO(scheduleSlot.startTime);
    _lectureEndTime = _extractTimeFromISO(scheduleSlot.endTime);

    await _saveToStorage();
    notifyListeners();
  }

  Future<void> clearLectureState() async {
    _lectureTitle = '';
    _courseCode = '';
    _lectureId = 0;
    _sessionId = 0;
    _teacherId = 0;
    _lectureDate = '';
    _lectureStartTime = '';
    _lectureEndTime = '';
    _lectureLink = '';
    _lectureStatus = '';
    _lectureType = '';
    _isRescheduling = false;
    // NOTE: clearLectureState does NOT clear ongoingSessionId intentionally.
    // Call clearOngoingSession() explicitly after approve().
    await _saveToStorage();
    notifyListeners();
  }

  // ── Private helpers ───────────────────────────────────────────────────────

  /// Converts an ISO datetime string like "2025-01-20T10:00:00" → "10:00".
  String _extractTimeFromISO(String isoTime) {
    try {
      final dt = DateTime.parse(isoTime);
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return '';
    }
  }
  
}

// ─────────────────────────────────────────────────────────────────────────────

class ScheduleStateProvider extends ChangeNotifier {
  List<AvailabilitySlot> _studentSchedules = [];
  List<ScheduleSlot> _teacherSchedules = [];
  List<ScheduleSlot> _lectureHistory = [];

  // ── Getters ──────────────────────────────────────────────────────────────

  List<AvailabilitySlot> get studentSchedules => _studentSchedules;
  List<ScheduleSlot> get teacherSchedules => _teacherSchedules;
  List<ScheduleSlot> get lectureHistory => _lectureHistory;

  // ── Setters ───────────────────────────────────────────────────────────────

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
