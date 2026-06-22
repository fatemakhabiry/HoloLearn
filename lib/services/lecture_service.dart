import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import '../config/api_config.dart';
import '../models/lecture_models.dart';
import '../providers/app_state_provider.dart';

// ─────────────────────────────────────────────────────────────────────────────
// Exceptions
// ─────────────────────────────────────────────────────────────────────────────

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

class ContentNotReadyException implements Exception {
  @override
  String toString() => 'Content is not ready yet (425).';
}

// ─────────────────────────────────────────────────────────────────────────────
// LectureService
// ─────────────────────────────────────────────────────────────────────────────

/// Handles all lecture CRUD operations and session management.
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

  static final _client = http.Client();

  static Map<String, String> _headers(String accesstoken) => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    'Authorization': 'Bearer $accesstoken',
  };

  static void _checkStatus(http.Response res) {
    if (res.statusCode == 425) throw ContentNotReadyException();
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String detail = res.body;
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map) {
          detail =
              decoded['detail']?.toString() ??
              decoded['message']?.toString() ??
              detail;
        }
      } catch (_) {}
      throw ApiException(detail, statusCode: res.statusCode);
    }
  }

  // ── Lecture CRUD ──────────────────────────────────────────────────────────

  /// STEP 1: Create lecture draft with file upload.
  static Future<LectureCreateResponse> createLectureDraft({
    required AppStateProvider appState,
    required String title,
    required String courseCode,
    required String filePath,
  }) async {
    try {
      print(' Starting upload with Dio...');

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
          headers: _headers(appState.accessToken),
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

  /// STEP 2: Confirm and publish lecture by reserving a schedule slot.
  static Future<LecturePublishResponse> confirmAndPublishLecture({
    required AppStateProvider appState,
    required int lectureId,
    required int scheduleId,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl(
          ApiConfig.publishLectureEndpoint.replaceFirst(
            '{lecture_id}',
            lectureId.toString(),
          ),
        ),
      );

      final response = await http
          .post(
            uri,
            headers: _headers(appState.accessToken),
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

  /// Fetch lecture details by schedule_id.
  static Future<LectureDetailResponse> getLectureByScheduleId({
    required AppStateProvider appState,
    required int scheduleId,
  }) async {
    final uri = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.getLectureDetailsEndpoint.replaceFirst(
          '{schedule_id}',
          scheduleId.toString(),
        ),
      ),
    );

    try {
      final response = await http
          .get(uri, headers: _headers(appState.accessToken))
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final decoded = json.decode(response.body);
        LectureDetailResponse parsed = LectureDetailResponse.fromJson(decoded);

        return parsed;
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

  /// Update lecture details.
  static Future<LectureUpdateResponse> updateLecture({
    required AppStateProvider appState,
    required int oldScheduleId,
    required String title,
    required String courseCode,
    int? newScheduleId,
  }) async {
    final uri = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.updateLectureEndpoint.replaceFirst(
          '{schedule_id}',
          oldScheduleId.toString(),
        ),
      ),
    );

    try {
      final Map<String, dynamic> body = {
        'title': title,
        'course_code': courseCode,
      };

      if (newScheduleId != null && newScheduleId != oldScheduleId) {
        body['new_schedule_id'] = newScheduleId;
      }

      print('📤 Updating lecture with body: $body');

      final response = await http
          .put(
            uri,
            headers: _headers(appState.accessToken),
            body: json.encode(body),
          )
          .timeout(ApiConfig.connectionTimeout);

      print('Response status: ${response.statusCode}');
      print('Response body: ${response.body}');

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

  /// Delete lecture.
  static Future<void> deleteLecture({
    required AppStateProvider appState,
    required int lectureId,
  }) async {
    final uri = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.deleteLectureEndpoint.replaceFirst(
          '{lecture_id}',
          lectureId.toString(),
        ),
      ),
    );

    try {
      final response = await http
          .delete(uri, headers: _headers(appState.accessToken))
          .timeout(ApiConfig.connectionTimeout);
      print(response.statusCode);
      print(response.body);
      if (response.statusCode != 200 && response.statusCode != 204) {
        final error = json.decode(response.body);
        throw Exception(error['message'] ?? 'Failed to delete lecture');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }

  // static Future<Map<String, dynamic>> _uploadResource(
  //   LectureResource resource,
  //   AppStateProvider appState,
  // ) async {
  //   try {
  //     print('📤 Starting resource upload...');

  //     final file = File(resource.filePath);

  //     // ✅ Check file exists
  //     if (!await file.exists()) {
  //       throw Exception('File not found');
  //     }

  //     // ✅ Check size (optional but recommended)
  //     final fileSize = await file.length();
  //     print('📦 File size: ${fileSize / 1024} KB');

  //     if (fileSize > 10 * 1024 * 1024) {
  //       throw Exception('File too large. Maximum 10MB.');
  //     }

  //     // ✅ Build FormData
  //     FormData formData = FormData.fromMap({
  //       'resource_type': resource.resourceExtension.toLowerCase(),
  //       'query': resource.query,
  //       'file': await MultipartFile.fromFile(
  //         resource.filePath,
  //         filename: resource.filePath.split('/').last,
  //       ),
  //     });

  //     // 🚀 Send request
  //     final response = await _dio.post(
  //       ApiConfig.getUrl(ApiConfig.uploadGeneratedFileEndpoint),
  //       data: formData,
  //       options: Options(
  //         headers: {'Authorization': 'Bearer ${appState.accessToken}'},
  //         validateStatus: (status) => status != null && status < 500,
  //       ),
  //       onSendProgress: (sent, total) {
  //         if (total != 0) {
  //           final progress = (sent / total * 100).toStringAsFixed(0);
  //           print('📊 Upload progress: $progress%');
  //         }
  //       },
  //     );

  //     // ✅ Handle response
  //     if (response.statusCode == 200 || response.statusCode == 201) {
  //       final raw = response.data;

  //       print('🔎 RAW RESPONSE TYPE: ${raw.runtimeType}');
  //       print('🔎 RAW RESPONSE: $raw');

  //       final data = raw is String
  //           ? jsonDecode(raw) as Map<String, dynamic>
  //           : Map<String, dynamic>.from(raw as Map);

  //       // size_bytes can come back as a nested map from the server — normalize it
  //       if (data['size_bytes'] is Map) {
  //         data['size_bytes'] = null;
  //       }

  //       return data;
  //     } else {
  //       final errorData = response.data is String
  //           ? jsonDecode(response.data)
  //           : response.data;

  //       throw Exception(errorData['detail'] ?? 'Upload failed');
  //     }
  //   } on DioException catch (e) {
  //     if (e.type == DioExceptionType.connectionTimeout) {
  //       throw Exception('Connection timeout. Check internet.');
  //     } else if (e.type == DioExceptionType.sendTimeout) {
  //       throw Exception('Upload timeout. File might be too large.');
  //     } else if (e.response != null) {
  //       throw Exception(e.response!.data['detail'] ?? 'Upload failed');
  //     } else {
  //       throw Exception('Network error: ${e.message}');
  //     }
  //   }
  // }
  static Future<Map<String, dynamic>> _uploadResource(
    LectureResource resource,
    AppStateProvider appState,
  ) async {
    try {
      print('📤 Starting resource upload...');

      // 🟢 CASE 1: WEBSITE (no file)
      if (resource.resourceExtension.toLowerCase() == 'website') {
        final response = await _dio.post(
          ApiConfig.getUrl(ApiConfig.uploadGeneratedFileEndpoint),
          data: {
            'resource_type': 'website',
            'query': resource.query,
            'url': resource.filePath, // 👈 use filePath to store URL
          },
          options: Options(
            headers: {
              'Authorization': 'Bearer ${appState.accessToken}',
              'Content-Type': 'application/json',
            },
            validateStatus: (status) => status != null && status < 500,
          ),
        );

        final raw = response.data;

        print('🔎 RAW RESPONSE TYPE: ${raw.runtimeType}');
        print('🔎 RAW RESPONSE: $raw');

        final data = raw is String
            ? jsonDecode(raw) as Map<String, dynamic>
            : Map<String, dynamic>.from(raw as Map);

        return data;
      }

      // 🔵 CASE 2: FILE (pdf, image, etc.)
      final file = File(resource.filePath);

      if (!await file.exists()) {
        throw Exception('File not found');
      }

      final fileSize = await file.length();
      print('📦 File size: ${fileSize / 1024} KB');

      if (fileSize > 500 * 1024 * 1024) {
        throw Exception('File too large. Maximum 500MB.');
      }

      FormData formData = FormData.fromMap({
        'resource_type': resource.resourceExtension.toLowerCase(),
        'query': resource.query,
        'file': await MultipartFile.fromFile(
          resource.filePath,
          filename: resource.filePath.split('/').last,
        ),
      });

      final response = await _dio.post(
        ApiConfig.getUrl(ApiConfig.uploadGeneratedFileEndpoint),
        data: formData,
        options: Options(
          headers: {'Authorization': 'Bearer ${appState.accessToken}'},
          validateStatus: (status) => status != null && status < 500,
        ),
        onSendProgress: (sent, total) {
          if (total != 0) {
            final progress = (sent / total * 100).toStringAsFixed(0);
            print('📊 Upload progress: $progress%');
          }
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final raw = response.data;

        print('🔎 RAW RESPONSE TYPE: ${raw.runtimeType}');
        print('🔎 RAW RESPONSE: $raw');

        final data = raw is String
            ? jsonDecode(raw) as Map<String, dynamic>
            : Map<String, dynamic>.from(raw as Map);

        if (data['size_bytes'] is Map) {
          data['size_bytes'] = null;
        }

        return data;
      } else {
        final errorData = response.data is String
            ? jsonDecode(response.data)
            : response.data;

        throw Exception(errorData['detail'] ?? 'Upload failed');
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

  static Future<StartSessionResponse> startSession(
    StartSessionRequest request,
    AppStateProvider appState,
  ) async {
    List<LectureResource> updatedResources = [];

    // 🔁 Loop over each resource
    for (var resource in request.resources) {
      if (resource.resourceExtension == 'url') {
        updatedResources.add(
          LectureResource(
            resourceExtension: 'website',
            filePath: resource.filePath,
            query: resource.query,
          ),
        );
      } else {
        final uploaded = await _uploadResource(resource, appState);
        print('3dina al upload w raga3na b: $uploaded\n');
        updatedResources.add(
          LectureResource(
            resourceExtension: uploaded['resource_type'] as String,
            filePath: uploaded['file_path'] as String,
            query: uploaded['query'] as String,
          ),
        );
      }
    }
    // updatedResources = await Future.wait(
    //   request.resources.map((resource) async {
    //     if (resource.resourceExtension == 'url') {
    //       return LectureResource(
    //         resourceExtension: 'website',
    //         filePath: resource.filePath,
    //         query: resource.query,
    //       );
    //     } else {
    //       final uploaded = await _uploadResource(resource, appState);

    //       print('Uploaded: $uploaded');

    //       return LectureResource(
    //         resourceExtension: uploaded['resource_type'] as String,
    //         filePath: uploaded['file_path'] as String,
    //         query: uploaded['query'] as String,
    //       );
    //     }
    //   }),
    // );
    print("b3t al files w d5lt flstart\n");
    // 🧱 Build new request with updated resources
    final updatedRequest = StartSessionRequest(
      title: request.title,
      courseCode: request.courseCode,
      resources: updatedResources,
    );

    // 🚀 Send final JSON request
    final res = await _client
        .post(
          Uri.parse(ApiConfig.getUrl(ApiConfig.startGeneratedSessionEndpoint)),
          headers: _headers(appState.accessToken),
          body: jsonEncode(updatedRequest.toJson()),
        )
        .timeout(ApiConfig.connectionTimeout);
    print("5lst flstart\n");

    // _checkStatus(res);
    print('Raw response: ${res.body}');
    final decoded = jsonDecode(res.body);
    print('Decoded response: $decoded');

    _checkStatus(res);
    // if (decoded is! Map<String, dynamic>) {
    //   throw Exception("Expected Map but got ${decoded.runtimeType}");
    // }

    return StartSessionResponse.fromJson(decoded as Map<String, dynamic>);
  }

  /// POST /sessions/start-prepared/{lecture_id}
  static Future<StartSessionResponse> startPreparedSession(
    AppStateProvider appState,
    int lectureId,
  ) async {
    final res = await _client
        .post(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.startPreparedEndpoint,
            ).replaceAll('{lecture_id}', lectureId.toString()),
          ),
          headers: _headers(appState.accessToken),
        )
        .timeout(ApiConfig.connectionTimeout);

    _checkStatus(res);
    return StartSessionResponse.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
    );
  }

  // GET /sessions/{session_id}/status
  static Future<LectureProcessingModel> fetchSessionStatus(
    int sessionId,
    AppStateProvider appState,
  ) async {
    final response = await _client
        .get(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.getSessionStatusEndpoint,
            ).replaceAll('{session_id}', sessionId.toString()),
          ),
          headers: _headers(appState.accessToken),
        )
        .timeout(ApiConfig.connectionTimeout);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Failed to fetch status: ${response.statusCode}');
    }

    final decoded = jsonDecode(response.body) as Map<String, dynamic>;
    return LectureProcessingModel.fromApi(decoded);
  }

  /// POST /sessions/{session_id}/approve
  static Future<bool> approve(int sessionId, AppStateProvider appState) async {
    final res = await _client
        .post(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.approveSessionEndpoint,
            ).replaceAll('{session_id}', sessionId.toString()),
          ),
          headers: _headers(appState.accessToken),
        )
        .timeout(ApiConfig.connectionTimeout);

    print(
      "sessionid: $sessionId,\n res.body: ${res.body} \n res.statusCode: ${res.statusCode}",
    );

    if (res.statusCode != 200) {
      throw Exception('Failed to approve session');
    }

    final data = jsonDecode(res.body);

    return data['status'].toLowerCase() == 'approved'; // "approved"
  }

  /// POST /sessions/{session_id}/reject
  static Future<void> rejectWithFeedback(
    AppStateProvider appState,
    int sessionId,
    String feedback,
  ) async {
    final res = await _client
        .post(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.rejectWithFeedbackSessionEndpoint,
            ).replaceAll('{session_id}', sessionId.toString()),
          ),
          headers: _headers(appState.accessToken),
          body: jsonEncode({'feedback': feedback}),
        )
        .timeout(ApiConfig.connectionTimeout);
    print(res);
    _checkStatus(res);
  }

  /// GET /sessions/{session_id}/content
  // static Future<SessionContent> getContent(
  //   int sessionId,
  //   AppStateProvider appState,
  // ) async {
  //   final res = await _client
  //       .get(
  //         Uri.parse(
  //           ApiConfig.getUrl(
  //             ApiConfig.getLectureContentEndpoint,
  //           ).replaceAll('{session_id}', sessionId.toString()),
  //         ),
  //         headers: _headers(appState.accessToken),
  //       )
  //       .timeout(ApiConfig.connectionTimeout);

  //   _checkStatus(res);
  //   return SessionContent.fromJson(
  //     jsonDecode(res.body) as Map<String, dynamic>,
  //   );
  // }

  // /// GET /sessions/{session_id}/lecture-pdf
  // static Future<List<int>> getLecturePdfBytes(
  //   int sessionId,
  //   AppStateProvider appState,
  // ) async {
  //   final res = await _client
  //       .get(
  //         Uri.parse(
  //           ApiConfig.getUrl(
  //             ApiConfig.getLecturePdfEndpoint,
  //           ).replaceAll('{session_id}', sessionId.toString()),
  //         ),
  //         headers: _headers(appState.accessToken),
  //       )
  //       .timeout(ApiConfig.connectionTimeout);

  //   if (res.statusCode == 404) {
  //     throw const ApiException('No PDF available yet.', statusCode: 404);
  //   }
  //   _checkStatus(res);
  //   return res.bodyBytes;
  // }
  static Future<List<int>> getLecturePdfBytes(
    int lectureId,
    AppStateProvider appState,
  ) async {
    final res = await _client
        .get(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.getLecturePdfEndpoint,
            ).replaceAll('{lecture_id}', lectureId.toString()),
          ),
          headers: _headers(appState.accessToken),
        )
        .timeout(ApiConfig.connectionTimeout);

    if (res.statusCode == 404) {
      throw const ApiException('No PDF available yet.', statusCode: 404);
    }
    _checkStatus(res);
    return res.bodyBytes;
  }

  static Future<List<int>> getLectureGeneratedResourceBytes(
    int lectureId,
    GenContentType contentType,
    AppStateProvider appState,
  ) async {
    final contentTypePathParam = GenContentType.toApiString(contentType);

    String fileKey, contenType;

    switch (contentType) {
      case GenContentType.worksheetAnswers:
      case GenContentType.quizAnswers:
        fileKey = 'answers';
        break;
      default:
        fileKey = 'primary';
    }
    switch (contentType) {
      // case GenContentType.lecture:
      // contenType='application/json';
      case GenContentType.script:
        contenType = 'text/plain';
      case GenContentType.knowledgeGraph:
        contenType = 'text/html';
        break;
      default:
        contenType = 'application/pdf';
    }

    final uri = Uri.parse(
      ApiConfig.getUrl(ApiConfig.getLectureGeneratedResourceEndpoint)
          .replaceAll('{lecture_id}', lectureId.toString())
          .replaceAll('{content_type}', contentTypePathParam),
    ).replace(queryParameters: {'file_key': fileKey});

    final res = await _client
        .get(
          uri,
          headers: {
            'Authorization': 'Bearer ${appState.accessToken}',
            'ngrok-skip-browser-warning': 'true',
            'Accept': contenType,
          },
        )
        .timeout(ApiConfig.connectionTimeout);

    if (res.statusCode == 404) {
      throw const ApiException('No content available yet.', statusCode: 404);
    }

    _checkStatus(res);

    return res.bodyBytes;
  }

  /// Student: download lecture content by lecture_id (no session_id needed)
  static Future<List<int>> getStudentLectureContentBytes(
    int lectureId,
    GenContentType contentType,
    AppStateProvider appState,
  ) async {
    final contentTypeParam = GenContentType.toApiString(contentType);

    String fileKey;
    switch (contentType) {
      case GenContentType.worksheetAnswers:
      case GenContentType.quizAnswers:
        fileKey = 'answers';
        break;
      default:
        fileKey = 'primary';
    }

    String acceptType;
    switch (contentType) {
      case GenContentType.script:
        acceptType = 'text/plain';
        break;
      case GenContentType.knowledgeGraph:
        acceptType = 'text/html';
        break;
      default:
        acceptType = 'application/pdf';
    }

    final uri = Uri.parse(
      ApiConfig.getUrl(ApiConfig.getStudentLectureContentEndpoint)
          .replaceAll('{lecture_id}', lectureId.toString())
          .replaceAll('{content_type}', contentTypeParam),
    ).replace(queryParameters: {'file_key': fileKey});

    final res = await _client
        .get(
          uri,
          headers: {
            'Authorization': 'Bearer ${appState.accessToken}',
            'ngrok-skip-browser-warning': 'true',
            'Accept': acceptType,
          },
        )
        .timeout(ApiConfig.connectionTimeout);

    if (res.statusCode == 404) {
      throw const ApiException('Content not available yet.', statusCode: 404);
    }
    _checkStatus(res);
    return res.bodyBytes;
  }

  static Future<List<int>> getStudentLectureChatHistoryBytes(
    int lectureId,
    AppStateProvider appState,
  ) async {
    final res = await _client
        .get(
          Uri.parse(
            ApiConfig.getUrl(
              ApiConfig.qaHistoryPdfEndpoint,
            ).replaceAll('{lecture_id}', lectureId.toString()),
          ),
          headers: {
            'Authorization': 'Bearer ${appState.accessToken}',
            'ngrok-skip-browser-warning': 'true',
            'Accept': 'application/pdf',
          },
        )
        .timeout(ApiConfig.connectionTimeout);

    if (res.statusCode == 404) {
      throw const ApiException(
        'Chat history not available...',
        statusCode: 404,
      );
    }
    _checkStatus(res);
    return res.bodyBytes;
  }

  static Future<List<String>> getFeedbackSuggestions(
    AppStateProvider appState,
    int sessionId,
  ) async {
    try {
      final response = await _client.get(
        Uri.parse(
          ApiConfig.getUrl(
            ApiConfig.getFeedbackSuggestionsEndpoint.replaceAll(
              '{session_id}',
              sessionId.toString(),
            ),
          ),
        ),
        headers: _headers(appState.accessToken),
      );

      _checkStatus(response);

      final decoded = jsonDecode(response.body);

      if (decoded is Map<String, dynamic>) {
        final suggestions = decoded['suggestions'];

        if (suggestions is List) {
          return suggestions.map((e) => e.toString()).toList();
        }
      }

      throw Exception('Invalid response format');
    } catch (e) {
      throw Exception('Failed to fetch feedback suggestions: $e');
    }
  }
}
