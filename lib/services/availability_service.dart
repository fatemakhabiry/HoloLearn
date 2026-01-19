import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class AvailabilitySlot {
  final DateTime startTime;
  final DateTime endTime;
  final int? scheduleId;
  final String? teacherName;
  final String? lectureTitle;
  final String status;

  AvailabilitySlot({
    required this.startTime,
    required this.endTime,
    this.scheduleId,
    this.teacherName,
    this.lectureTitle,
    required this.status,
  });

  factory AvailabilitySlot.fromJson(Map<String, dynamic> json) {
    return AvailabilitySlot(
      startTime: DateTime.parse(json['start_time']),
      endTime: DateTime.parse(json['end_time']),
      scheduleId: json['schedule_id'],
      teacherName: json['teacher_name'],
      lectureTitle: json['lecture_title'],
      status: json['status'] ?? 'available',
    );
  }

  /// Format time slot as "HH:MM to HH:MM"
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
    return AvailabilityResponse(
      date: json['date'],
      availableSlots: (json['available_slots'] as List)
          .map((slot) => AvailabilitySlot.fromJson(slot))
          .toList(),
    );
  }
}

class AvailabilityService {
  /// Fetch available time slots for a specific date
  ///
  /// [token] - The authentication Bearer token
  /// [date] - The date in format "YYYY-MM-DD"
  ///
  /// Returns a list of available time slots
  static Future<AvailabilityResponse> fetchAvailableSlots({
    required String token,
    required String date,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl('${ApiConfig.availabilitySlotsEndpoint}/$date'),
      );

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
      throw Exception('Network error: $e');
    }
  }

  /// Create/Publish a new lecture
  ///
  /// [token] - The authentication Bearer token
  /// [date] - The date in format "YYYY-MM-DD"
  /// [startTime] - Start time in ISO format "YYYY-MM-DDTHH:MM:SS"
  /// [endTime] - End time in ISO format "YYYY-MM-DDTHH:MM:SS"
  /// [avatar] - Selected avatar type (e.g., "standard", "sign_language")
  ///
  /// Returns success message // hna hn8yrhaaaa odam **************************************************************************
  //   static Future<String> publishLecture({
  //     required String token,
  //     required String date,
  //     required String startTime,
  //     required String endTime,
  //     required String avatar,
  //   }) async {
  //     try {
  //       final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.publishLectureEndpoint));

  //       final response = await http
  //           .post(
  //             uri,
  //             headers: {
  //               'Content-Type': 'application/json',
  //               'Authorization': 'Bearer $token',
  //               'ngrok-skip-browser-warning': 'true',
  //             },
  //             body: json.encode({
  //               'date': date,
  //               'start_time': startTime,
  //               'end_time': endTime,
  //               'avatar_type': avatar,
  //             }),
  //           )
  //           .timeout(ApiConfig.connectionTimeout);

  //       if (response.statusCode == 200 || response.statusCode == 201) {
  //         final data = json.decode(response.body);
  //         return data['message'] ?? 'Lecture published successfully';
  //       } else if (response.statusCode == 400) {
  //         final error = json.decode(response.body);
  //         throw Exception(error['detail'] ?? 'Invalid request');
  //       } else if (response.statusCode == 401) {
  //         throw Exception('Unauthorized - Please login again');
  //       } else if (response.statusCode == 409) {
  //         throw Exception('Time slot is no longer available');
  //       } else {
  //         final error = json.decode(response.body);
  //         throw Exception(error['detail'] ?? 'Failed to publish lecture');
  //       }
  //     } catch (e) {
  //       throw Exception('Network error: $e');
  //     }
  //   }
}
