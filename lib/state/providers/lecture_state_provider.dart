import 'package:flutter/foundation.dart';
import '../../models/lecture_model.dart';
import '../../models/schedule_models.dart';
import '../../models/availability_models.dart';
import '../../utils/storage_helper.dart';

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

  Future<void> setFromScheduleSlot(ScheduleSlot scheduleSlot) async {
    _lectureId = scheduleSlot.lectureId ?? 0;
    _lectureTitle = scheduleSlot.lectureTitle;
    _courseCode = scheduleSlot.courseCode ;

    // ✅ Parse date from startTime if date field is null
    String extractedDate = scheduleSlot.date ?? "";
    if (extractedDate.isEmpty && scheduleSlot.startTime.isNotEmpty) {
      try {
        final dateTime = DateTime.parse(scheduleSlot.startTime);
        extractedDate =
            '${dateTime.year}-${dateTime.month.toString().padLeft(2, '0')}-${dateTime.day.toString().padLeft(2, '0')}';
      } catch (e) {
        print('Error parsing date from startTime: $e');
      }
    }

    _lectureDate = extractedDate;

    // ✅ Extract time from ISO format
    _lectureStartTime = _extractTimeFromISO(scheduleSlot.startTime);
    _lectureEndTime = _extractTimeFromISO(scheduleSlot.endTime);
    _lectureStatus = scheduleSlot.status;
    _lectureType = scheduleSlot.lectureType ?? "";

    print('✅ Lecture state set for reschedule:');
    print('   Lecture ID: $_lectureId');
    print('   Title: $_lectureTitle');
    print('   Date: $_lectureDate');
    print('   Time: $_lectureStartTime - $_lectureEndTime');

    await _saveToStorage();
    notifyListeners();
  }

  // ✅ Helper to extract time from ISO format "2025-01-20T10:00:00" -> "10:00"
  String _extractTimeFromISO(String isoTime) {
    try {
      final dateTime = DateTime.parse(isoTime);
      return '${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      print('Error extracting time from ISO: $e');
      return "";
    }
  }

  // ✅ Add clear method for when navigating away
  Future<void> clearLectureState() async {
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
    await _saveToStorage();
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
