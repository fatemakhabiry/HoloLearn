import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/lecture_model.dart';
import '../state/providers/app_state_provider.dart';

/// Handles all lecture-related operations (CRUD)
class LectureService {
  static final Dio _dio = Dio(
    BaseOptions(
      connectTimeout: const Duration(minutes: 5),
      receiveTimeout: const Duration(minutes: 5),
      sendTimeout: const Duration(minutes: 5),
      headers: {
        'ngrok-skip-browser-warning': 'true',
        'User-Agent': 'Flutter-App',
      },
    ),
  );

  /// STEP 1: Create lecture draft with file upload
  static Future<LectureCreateResponse> createLectureDraft({
    required AppStateProvider appState,
    required String title,
    required String courseCode,
    required String filePath,
  }) async {
    try {
      print('📤 Starting upload with Dio...');

      final file = File(filePath);
      if (!await file.exists()) {
        throw Exception('File not found');
      }

      final fileSize = await file.length();
      print('File size: ${fileSize / 1024} KB');

      if (fileSize > 10 * 1024 * 1024) {
        throw Exception('File too large. Maximum 10MB.');
      }

      FormData formData = FormData.fromMap({
        'title': title,
        'course_code': courseCode,
        'file': await MultipartFile.fromFile(
          filePath,
          filename: filePath.split('/').last,
        ),
      });

      final response = await _dio.post(
        ApiConfig.getUrl(ApiConfig.createLectureDraftEndpoint),
        data: formData,
        options: Options(
          headers: {'Authorization': 'Bearer ${appState.accessToken}'},
          validateStatus: (status) => status != null && status < 500,
        ),
        onSendProgress: (sent, total) {
          final progress = (sent / total * 100).toStringAsFixed(0);
          print('Upload progress: $progress%');
        },
      );

      if (response.statusCode == 201) {
        return LectureCreateResponse.fromJson(response.data);
      } else {
        throw Exception(response.data['detail'] ?? 'Upload failed');
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout) {
        throw Exception('Connection timeout. Check internet.');
      } else if (e.type == DioExceptionType.sendTimeout) {
        throw Exception('Upload timeout. File might be too large.');
      } else if (e.response != null) {
        throw Exception(e.response!.data['detail'] ?? 'Upload failed');
      } else {
        throw Exception('Network error: ${e.message}');
      }
    }
  }

  /// STEP 2: Confirm and publish lecture by reserving a schedule slot
  static Future<LecturePublishResponse> confirmAndPublishLecture({
    required AppStateProvider appState,
    required int lectureId,
    required int scheduleId,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl(
          '${ApiConfig.publishLectureEndpoint}/$lectureId/confirm-and-publish',
        ),
      );

      final response = await http
          .post(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
            body: json.encode({'schedule_id': scheduleId}),
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200 || response.statusCode == 201) {
        return LecturePublishResponse.fromJson(json.decode(response.body));
      } else if (response.statusCode == 409) {
        throw Exception('This schedule slot is already reserved');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to publish lecture');
      }
    } catch (e) {
      if (e.toString().contains('Exception:')) rethrow;
      throw Exception('Network error: $e');
    }
  }
 
  /// Fetch lecture details by schedule_id
  static Future<LectureDetailResponse> getLectureByScheduleId({
    required AppStateProvider appState,
    required int scheduleId,
  }) async {
    final uri = Uri.parse(
      ApiConfig.getUrl('/lecture/schedule/$scheduleId/edit-details'),
    );

    try {
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
        return LectureDetailResponse.fromJson(json.decode(response.body));
      } else if (response.statusCode == 404) {
        throw Exception('Lecture not found.');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to fetch lecture details');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }

  /// Update lecture details
  static Future<LectureUpdateResponse> updateLecture({
    required AppStateProvider appState,
    required int oldScheduleId,
    required String title,
    required String courseCode,
    int? newScheduleId,  // Optional - only if changing schedule
  }) async {
    final uri = Uri.parse(
      ApiConfig.getUrl('/lecture/schedule/$oldScheduleId/edit'),
    );
    
    try {
      // Build request body - only include fields to update
      final Map<String, dynamic> body = {
        'title': title,
        'course_code': courseCode,
      };
      
      // Only add new_schedule_id if changing schedule
      if (newScheduleId != null && newScheduleId != oldScheduleId) {
        body['new_schedule_id'] = newScheduleId;
      }
      
      print('📤 Updating lecture with body: $body');
      
      final response = await http
          .put(
            uri,
            headers: {
              'Content-Type': 'application/json',  // ✅ JSON is correct now!
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
            body: json.encode(body),  // ✅ JSON encoding is correct now!
          )
          .timeout(ApiConfig.connectionTimeout);
      
      print('📥 Response status: ${response.statusCode}');
      print('📥 Response body: ${response.body}');
      
      if (response.statusCode == 200) {
        return LectureUpdateResponse.fromJson(json.decode(response.body));
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to update lecture');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    } catch (e) {
      throw Exception('Failed to update lecture: $e');
    }
  }


  /// Delete lecture
  static Future<void> deleteLecture({
    required AppStateProvider appState,
    required int lectureId,
  }) async {
    final uri = Uri.parse(ApiConfig.getUrl('${ApiConfig.lecturesEndpoint}$lectureId'));

    try {
      final response = await http
          .delete(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode != 200 && response.statusCode != 204) {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to delete lecture');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }
}
