import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/schedule_models.dart';
import '../providers/app_state_provider.dart';

/// Handles schedule-related operations for teachers and students
class ScheduleService {
  /// Fetch reserved slots (teacher's lectures) from the API
  /// The API uses the Bearer token to identify the teacher and return their lectures
  static Future<List<ScheduleSlot>> fetchMyLectures(AppStateProvider appState) async {
    try {
      final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.reservedSlotsEndpoint));

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data
            .map((slot) => ScheduleSlot.fromJson(slot as Map<String, dynamic>))
            .toList();
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized - Please login again');
      } else if (response.statusCode == 404) {
        throw Exception('No lectures found');
      } else {
        try {
          final error = json.decode(response.body);
          throw Exception(error['detail'] ?? 'Failed to fetch lectures');
        } catch (e) {
          throw Exception('Failed to fetch lectures: ${response.statusCode}');
        }
      }
    } on http.ClientException catch (e) {
      throw Exception('Network error: ${e.message}');
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('Error fetching lectures: $e');
    }
  }

  /// Fetch student lectures from the API
 static Future<List<ScheduleSlot>> fetchStudentLectures(AppStateProvider appState) async {
    if (appState.accessToken.isEmpty) {
      throw Exception('No authentication token found. Please login again.');
    }

    try {
      final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.studentLectureEndpoint));

      print('📡 Fetching student lectures from: $uri');

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');

      if (response.statusCode == 200) {
        final dynamic jsonData = json.decode(response.body);

        // ✅ FIXED: Handle the actual API response structure
        if (jsonData is Map<String, dynamic>) {
          // Check if response has "lectures" key (your actual API response)
          if (jsonData.containsKey('lectures')) {
            final List<dynamic> lectures = jsonData['lectures'] as List;
            print('✅ Found ${lectures.length} lectures');
            
            return lectures
                .map((lecture) => ScheduleSlot.fromJson(lecture as Map<String, dynamic>))
                .toList();
          }
          // Check if response has "reserved_slots" key (alternative format)
          else if (jsonData.containsKey('reserved_slots')) {
            final scheduleResponse = ScheduleResponse.fromJson(jsonData);
            return scheduleResponse.reservedSlots;
          }
          // Single lecture object
          else if (jsonData.containsKey('schedule_id')) {
            return [ScheduleSlot.fromJson(jsonData)];
          }
          else {
            throw Exception('Unexpected response format: missing "lectures" or "reserved_slots" key');
          }
        } 
        // Direct array response
        else if (jsonData is List) {
          return jsonData
              .map((slot) => ScheduleSlot.fromJson(slot as Map<String, dynamic>))
              .toList();
        } 
        else {
          throw Exception('Unexpected response format: ${jsonData.runtimeType}');
        }
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized. Please login again.');
      } else if (response.statusCode == 404) {
        throw Exception('No lectures found.');
      } else if (response.statusCode >= 500) {
        throw Exception('Server error. Please try again later.');
      } else {
        throw Exception('Failed to fetch lectures: ${response.statusCode}');
      }
    } on http.ClientException catch (e) {
      throw Exception('Network error: ${e.message}');
    } catch (e) {
      print('❌ Error in fetchStudentLectures: $e');
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('Error fetching student lectures: $e');
    }
  }


  /// Update an existing lecture
  static Future<String> updateLecture({
    required AppStateProvider appState,
    required int scheduleId,
    required String lectureTitle,
    required String startTime,
    required String endTime,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl('${ApiConfig.updateLectureEndpoint}/$scheduleId'),
      );

      final response = await http
          .put(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
            body: json.encode({
              'lecture_title': lectureTitle,
              'start_time': startTime,
              'end_time': endTime,
            }),
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['message'] ?? 'Lecture updated successfully';
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to update lecture');
      }
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('Network error: $e');
    }
  }

  /// Cancel/Delete a lecture
  static Future<String> cancelLecture({
    required AppStateProvider appState,
    required int scheduleId,
  }) async {
    try {
      // Build URL with scheduleId replacing the placeholder
      final endpoint = ApiConfig.cancleLectureEndpoint.replaceAll(
        '{schedule_id}',
        scheduleId.toString(),
      );
      final uri = Uri.parse(ApiConfig.getUrl(endpoint));

      final response = await http
          .patch(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['message'] ?? 'Lecture cancelled successfully';
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to cancel lecture');
      }
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('Network error: $e');
    }
  }

  /// Fetch lecture history for teacher
  static Future<List<ScheduleSlot>> fetchMyLectureHistory(AppStateProvider appState) async {
    try {
      final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.lectureHistoryendpoint));

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
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
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('Network error: $e');
    }
  }
}