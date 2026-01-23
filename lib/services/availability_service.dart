import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class AvailabilitySlot {
  final int scheduleId;
  final DateTime startTime;
  final DateTime endTime;
  final String? teacherName;
  final String? lectureTitle;
  final String status;

  AvailabilitySlot({
    required this.scheduleId,
    required this.startTime,
    required this.endTime,
    this.teacherName,
    this.lectureTitle,
    required this.status,
  });

  factory AvailabilitySlot.fromJson(Map<String, dynamic> json) {
    final date = json['date'] ?? DateTime.now().toIso8601String().split('T')[0];

    return AvailabilitySlot(
      scheduleId: json['schedule_id'],
      startTime: _parseTimeToDateTime(json['start_time'], date),
      endTime: _parseTimeToDateTime(json['end_time'], date),
      teacherName: json['teacher_name'],
      lectureTitle: json['lecture_title'],
      status: json['status'] ?? 'available',
    );
  }

  static DateTime _parseTimeToDateTime(String timeString, String dateString) {
    try {
      final dateTime = DateTime.parse('${dateString}T$timeString');
      return dateTime;
    } catch (e) {
      print('Error parsing time: $timeString with date: $dateString');
      return DateTime.now();
    }
  }

  String get formattedTimeSlot {
    final startHour = startTime.hour.toString().padLeft(2, '0');
    final startMinute = startTime.minute.toString().padLeft(2, '0');
    final endHour = endTime.hour.toString().padLeft(2, '0');
    final endMinute = endTime.minute.toString().padLeft(2, '0');

    return "$startHour:$startMinute to $endHour:$endMinute";
  }
}

class AvailabilityResponse {
  final String date;
  final List<AvailabilitySlot> availableSlots;

  AvailabilityResponse({required this.date, required this.availableSlots});

  factory AvailabilityResponse.fromJson(Map<String, dynamic> json) {
    final date = json['date'];

    return AvailabilityResponse(
      date: date,
      availableSlots: (json['available_slots'] as List).map((slot) {
        slot['date'] = date;
        return AvailabilitySlot.fromJson(slot);
      }).toList(),
    );
  }
}

class ConfirmPublishResponse {
  final String message;
  final int lectureId;
  final int scheduleId;
  final String lectureTitle;
  final String courseCode;
  final String lectureStatus;
  final String scheduleStatus;
  final String scheduledDate;
  final String startTime;
  final String endTime;

  ConfirmPublishResponse({
    required this.message,
    required this.lectureId,
    required this.scheduleId,
    required this.lectureTitle,
    required this.courseCode,
    required this.lectureStatus,
    required this.scheduleStatus,
    required this.scheduledDate,
    required this.startTime,
    required this.endTime,
  });

  factory ConfirmPublishResponse.fromJson(Map<String, dynamic> json) {
    return ConfirmPublishResponse(
      message: json['message'],
      lectureId: json['lecture_id'],
      scheduleId: json['schedule_id'],
      lectureTitle: json['lecture_title'],
      courseCode: json['course_code'],
      lectureStatus: json['lecture_status'],
      scheduleStatus: json['schedule_status'],
      scheduledDate: json['scheduled_date'],
      startTime: json['start_time'],
      endTime: json['end_time'],
    );
  }
}

class AvailabilityService {
  /// Fetch available time slots for a specific date
  static Future<AvailabilityResponse> fetchAvailableSlots({
    required String token,
    required String date,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl('${ApiConfig.availabilitySlotsEndpoint}/$date'),
      );

      print('📅 Fetching slots for: $date');
      print('🌐 URL: $uri');

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      print('📡 Status: ${response.statusCode}');
      print('📥 Response: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return AvailabilityResponse.fromJson(data);
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized - Please login again');
      } else if (response.statusCode == 404) {
        throw Exception('No available slots found for this date');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to fetch available slots');
      }
    } catch (e) {
      print('❌ Error: $e');
      throw Exception('Network error: $e');
    }
  }

  /// Confirm and publish lecture by reserving a schedule slot
  /// 
  /// This is STEP 2 of the lecture creation process:
  /// 1. Create lecture (draft) - done in create_new_lecture_screen
  /// 2. Confirm and publish - done here with schedule_id
  static Future<ConfirmPublishResponse> confirmAndPublishLecture({
    required String token,
    required int lectureId,
    required int scheduleId,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl('${ApiConfig.publishLectureEndpoint}/$lectureId/confirm-and-publish'),
      );

      print('📤 Publishing lecture $lectureId with schedule $scheduleId');
      print('🌐 URL: $uri');

      final response = await http
          .post(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
              'ngrok-skip-browser-warning': 'true',
            },
            body: json.encode({
              'schedule_id': scheduleId,
            }),
          )
          .timeout(ApiConfig.connectionTimeout);

      print('📡 Status: ${response.statusCode}');
      print('📥 Response: ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = json.decode(response.body);
        return ConfirmPublishResponse.fromJson(data);
      } else if (response.statusCode == 400) {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Invalid request');
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized - Please login again');
      } else if (response.statusCode == 403) {
        throw Exception('You can only publish your own lectures');
      } else if (response.statusCode == 404) {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Lecture or schedule not found');
      } else if (response.statusCode == 409) {
        throw Exception('This schedule slot is already reserved');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to publish lecture');
      }
    } catch (e) {
      print('❌ Error: $e');
      throw Exception('Network error: $e');
    }
  }
}
