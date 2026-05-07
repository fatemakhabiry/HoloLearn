import 'dart:convert';
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../providers/app_state_provider.dart';

/// Handles avatar and profile-related operations
class AvatarService {
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

  /// Check avatar status
  static Future<Map<String, dynamic>> checkAvatarStatus(AppStateProvider appState) async {
    final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.avatarStatusEndpoint));

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Bearer ${appState.accessToken}',
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      
      // Update app state with profile setup status
      appState.setFirstTimeLogin(data['needs_profile_setup'] ?? false);
      
      print('First time login: ${appState.isFirstTimeLogin}');
      return data;
    } else {
      throw Exception(
        'Failed to check avatar status: ${response.statusCode} ${response.body}',
      );
    }
  }

  /// Upload avatar (photo and/or voice)
  static Future<Map<String, dynamic>> uploadAvatar({
    required AppStateProvider appState,
    File? photoFile,
    File? voiceFile,
  }) async {
    Map<String, dynamic> results = {};

    if (photoFile != null) {
      results['photo'] = await uploadPhoto(
        appState: appState,
        photoFile: photoFile,
      );
      print('✅ Photo upload result: ${results['photo']}');
    }

    if (voiceFile != null) {
      results['voice'] = await uploadVoiceSample(
        appState: appState,
        voiceFile: voiceFile,
      );
      print('✅ Voice upload result: ${results['voice']}');
    }

    return results;
  }

  /// Upload only photo
  static Future<Map<String, dynamic>> uploadPhoto({
    required AppStateProvider appState,
    required File photoFile,
  }) async {
    try {
      print('📤 Starting photo upload with Dio...');

      // Validate file exists
      if (!await photoFile.exists()) {
        throw 'Photo file not found';
      }

      // Check file size (max 5MB for images)
      final fileSize = await photoFile.length();
      print('Photo file size: ${(fileSize / 1024).toStringAsFixed(2)} KB');

      if (fileSize > 5 * 1024 * 1024) {
        throw 'Photo too large. Maximum 5MB allowed.';
      }

      // Prepare form data
      FormData formData = FormData.fromMap({
        'photo': await MultipartFile.fromFile(
          photoFile.path,
          filename: photoFile.path.split('/').last,
        ),
      });

      // Make API request
      final response = await _dio.post(
        ApiConfig.getUrl(ApiConfig.teacherUploadPhotoEndpoint),
        data: formData,
        options: Options(
          headers: {'Authorization': 'Bearer ${appState.accessToken}'},
          validateStatus: (status) => status != null && status < 500,
        ),
        onSendProgress: (sent, total) {
          final progress = (sent / total * 100).toStringAsFixed(0);
          print('Photo upload progress: $progress%');
        },
      );

      // Handle response
      if (response.statusCode == 200) {
        print('✅ Photo uploaded successfully!');
        return response.data as Map<String, dynamic>;
      } else {
        final errorMessage = _extractErrorMessage(response);
        throw errorMessage;
      }
    } on DioException catch (e) {
      throw _handleDioError(e, 'photo');
    } catch (e) {
      if (e is String) {
        throw e;
      }
      throw 'Failed to upload photo: ${e.toString()}';
    }
  }

  /// Upload only voice sample
 static Future<Map<String, dynamic>> uploadVoiceSample({
  required AppStateProvider appState,
  required File voiceFile,
}) async {
  try {
    print('📤 Starting voice sample upload with Dio...');

    // Validate file exists
    if (!await voiceFile.exists()) {
      throw 'Voice file not found';
    }

    // Check file size (max 10MB for audio)
    final fileSize = await voiceFile.length();
    print('Voice file size: ${(fileSize / 1024).toStringAsFixed(2)} KB');

    if (fileSize > 10 * 1024 * 1024) {
      throw 'Voice file too large. Maximum 10MB allowed.';
    }

    // Detect file extension and set content type
    final fileName = voiceFile.path.split('/').last;
    final extension = fileName.split('.').last.toLowerCase();

    String contentType;
    switch (extension) {
      case 'm4a':
        contentType = 'audio/mp4';
        break;
      case 'mp3':
        contentType = 'audio/mpeg';
        break;
      case 'wav':
        contentType = 'audio/wav';
        break;
      case 'ogg':
        contentType = 'audio/ogg';
        break;
      default:
        contentType = 'audio/mpeg';
    }

    print('File: $fileName, Content-Type: $contentType');

    // ✅ FIX: Changed 'voice_sample' to 'voice' to match backend
    FormData formData = FormData.fromMap({
      'voice': await MultipartFile.fromFile(
        voiceFile.path,
        filename: fileName,
        contentType: DioMediaType.parse(contentType),
      ),
    });

    // Make API request
    final response = await _dio.post(
      ApiConfig.getUrl(ApiConfig.teacherUploadVoiceEndpoint),
      data: formData,
      options: Options(
        headers: {
          'Authorization': 'Bearer ${appState.accessToken}',
        },
        validateStatus: (status) => status != null && status < 500,
      ),
      onSendProgress: (sent, total) {
        final progress = (sent / total * 100).toStringAsFixed(0);
        print('Voice upload progress: $progress%');
      },
    );

    // Handle response
    if (response.statusCode == 200) {
      print('✅ Voice sample uploaded successfully!');
      return response.data as Map<String, dynamic>;
    } else {
      final errorMessage = _extractErrorMessage(response);
      print('❌ Error response: ${response.data}');
      throw errorMessage;
    }
  } on DioException catch (e) {
    throw _handleDioError(e, 'voice sample');
  } catch (e) {
    if (e is String) {
      throw e;
    }
    throw 'Failed to upload voice sample: ${e.toString()}';
  }
}
  /// Extract error message from response
  static String _extractErrorMessage(Response response) {
    try {
      if (response.data != null && response.data is Map) {
        return response.data['detail'] ?? 'Upload failed';
      }
      return 'Upload failed with status ${response.statusCode}';
    } catch (e) {
      return 'Upload failed';
    }
  }

  /// Handle Dio errors with context
  static String _handleDioError(DioException e, String fileType) {
    if (e.response != null) {
      final statusCode = e.response!.statusCode;
      final data = e.response!.data;

      switch (statusCode) {
        case 400:
          if (data != null && data['detail'] != null) {
            return data['detail'];
          }
          return 'Invalid $fileType file. Please check the file format.';
        case 403:
          if (data != null && data['detail'] != null) {
            return data['detail'];
          }
          return 'You do not have permission to upload $fileType.';
        case 413:
          return '$fileType file is too large. Please use a smaller file.';
        case 415:
          return 'Unsupported $fileType format. Please use a valid file type.';
        case 500:
          return 'Server error. Please try again later.';
        default:
          if (data != null && data['detail'] != null) {
            return data['detail'];
          }
          return 'Failed to upload $fileType with status $statusCode';
      }
    } else if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Upload timeout. Please check your internet connection or try a smaller file.';
    } else if (e.type == DioExceptionType.connectionError) {
      return 'Cannot connect to server. Please check your internet connection.';
    } else {
      return 'Network error: ${e.message}';
    }
  }
}