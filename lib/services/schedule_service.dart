import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../utils/schedule_slot.dart';

class ScheduleService {
  /// Fetch reserved slots (teacher's lectures) from the API
  /// The API uses the Bearer token to identify the teacher and return their lectures
  static Future<List<ScheduleSlot>> fetchMyLectures(String token) async {
    try {
      final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.reservedSlotsEndpoint));

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token', // Pass the authentication token
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((slot) => ScheduleSlot.fromJson(slot)).toList();
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized - Please login again');
      } else if (response.statusCode == 404) {
        throw Exception('No lectures found');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to fetch lectures');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Create a new lecture
  // static Future<String> createLecture({
  //   required String token,
  //   required String lectureTitle,
  //   required String startTime,
  //   required String endTime,
  // }) async {
  //   try {
  //     final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.createLectureEndpoint));

  //     final response = await http.post(
  //       uri,
  //       headers: {
  //         'Content-Type': 'application/json',
  //         'Authorization': 'Bearer $token',
  //       },
  //       body: json.encode({
  //         'lecture_title': lectureTitle,
  //         'start_time': startTime,
  //         'end_time': endTime,
  //       }),
  //     ).timeout(ApiConfig.connectionTimeout);

  //     if (response.statusCode == 200 || response.statusCode == 201) {
  //       final data = json.decode(response.body);
  //       return data['message'] ?? 'Lecture created successfully';
  //     } else {
  //       final error = json.decode(response.body);
  //       throw Exception(error['detail'] ?? 'Failed to create lecture');
  //     }
  //   } catch (e) {
  //     throw Exception('Network error: $e');
  //   }
  // }

  /// Update an existing lecture
  // static Future<String> updateLecture({
  //   required String token,
  //   required int scheduleId,
  //   required String lectureTitle,
  //   required String startTime,
  //   required String endTime,
  // }) async {
  //   try {
  //     final uri = Uri.parse(
  //       ApiConfig.getUrl('${ApiConfig.updateLectureEndpoint}/$scheduleId'),
  //     );

  //     final response = await http.put(
  //       uri,
  //       headers: {
  //         'Content-Type': 'application/json',
  //         'Authorization': 'Bearer $token',
  //       },
  //       body: json.encode({
  //         'lecture_title': lectureTitle,
  //         'start_time': startTime,
  //         'end_time': endTime,
  //       }),
  //     ).timeout(ApiConfig.connectionTimeout);

  //     if (response.statusCode == 200) {
  //       final data = json.decode(response.body);
  //       return data['message'] ?? 'Lecture updated successfully';
  //     } else {
  //       final error = json.decode(response.body);
  //       throw Exception(error['detail'] ?? 'Failed to update lecture');
  //     }
  //   } catch (e) {
  //     throw Exception('Network error: $e');
  //   }
  // }

  /// Cancel/Delete a lecture
  // static Future<String> cancelLecture(String token, int scheduleId) async {
  //   try {
  //     final uri = Uri.parse(
  //       ApiConfig.getUrl('${ApiConfig.deleteLectureEndpoint}/$scheduleId'),
  //     );

  //     final response = await http.delete(
  //       uri,
  //       headers: {
  //         'Content-Type': 'application/json',
  //         'Authorization': 'Bearer $token',
  //       },
  //     ).timeout(ApiConfig.connectionTimeout);

  //     if (response.statusCode == 200) {
  //       final data = json.decode(response.body);
  //       return data['message'] ?? 'Lecture cancelled successfully';
  //     } else {
  //       final error = json.decode(response.body);
  //       throw Exception(error['detail'] ?? 'Failed to cancel lecture');
  //     }
  //   } catch (e) {
  //     throw Exception('Network error: $e');
  //   }
  // }
}
