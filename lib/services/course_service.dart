import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/course_models.dart';
import '../state/providers/app_state_provider.dart';

/// Handles all course-related operations
class CourseService {
  /// Fetch all available course codes
  static Future<List<String>> fetchCourseCodes(AppStateProvider appState) async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.courseListEndpoint));

    try {
      final response = await http
          .get(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((course) => course.toString()).toList();
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized. Please login again.');
      } else if (response.statusCode == 404) {
        throw Exception('Courses endpoint not found.');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to fetch course codes');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('An error occurred: ${e.toString()}');
    }
  }

  /// Fetch detailed course information by course code
  static Future<CourseDetail> getCourseByCode({
    required AppStateProvider appState,
    required String courseCode,
  }) async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.courseListEndpoint));

    try {
      final response = await http
          .get(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return CourseDetail.fromJson(data);
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized. Please login again.');
      } else if (response.statusCode == 404) {
        throw Exception('Course not found.');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to fetch course details');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('An error occurred: ${e.toString()}');
    }
  }

  /// Fetch all courses with details
  static Future<List<CourseDetail>> fetchAllCourses({
    required AppStateProvider appState,
  }) async {
    final url = Uri.parse(ApiConfig.getUrl(ApiConfig.courseListEndpoint));

    try {
      final response = await http
          .get(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ${appState.accessToken}',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final List<dynamic> data = json.decode(response.body);
        return data.map((course) => CourseDetail.fromJson(course)).toList();
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized. Please login again.');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to fetch courses');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    } catch (e) {
      if (e.toString().contains('Exception:')) {
        rethrow;
      }
      throw Exception('An error occurred: ${e.toString()}');
    }
  }
}