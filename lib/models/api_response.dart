import 'user_model.dart';

// Login Response Model (matches your Token model from backend)
class LoginResponse {
  final String accessToken;
  final String tokenType;
  final User user;

  LoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.user,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      accessToken: json['access_token'] as String,
      tokenType: json['token_type'] as String,
      user: User.fromJson(json['user'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'access_token': accessToken,
      'token_type': tokenType,
      'user': user.toJson(),
    };
  }
}

// Generic API Response wrapper
class ApiResponse<T> {
  final bool success;
  final T? data;
  final String? message;
  final String? error;
  final int? statusCode;

  ApiResponse({
    required this.success,
    this.data,
    this.message,
    this.error,
    this.statusCode,
  });

  factory ApiResponse.success(T data, {String? message, int? statusCode}) {
    return ApiResponse(
      success: true,
      data: data,
      message: message,
      statusCode: statusCode ?? 200,
    );
  }

  factory ApiResponse.error(String error, {int? statusCode}) {
    return ApiResponse(
      success: false,
      error: error,
      statusCode: statusCode,
    );
  }

  bool get isSuccess => success;
  bool get isError => !success && error != null;
}

// User Update Model
class UserUpdate {
  final String? email;
  final String? fullName;

  UserUpdate({
    this.email,
    this.fullName,
  });

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> data = {};
    if (email != null) data['email'] = email;
    if (fullName != null) data['full_name'] = fullName;
    return data;
  }
}

// File Upload Response Model
class FileUploadResponse {
  final String message;
  final String? photoUrl;
  final String? voiceUrl;

  FileUploadResponse({
    required this.message,
    this.photoUrl,
    this.voiceUrl,
  });

  factory FileUploadResponse.fromJson(Map<String, dynamic> json) {
    return FileUploadResponse(
      message: json['message'] as String,
      photoUrl: json['photo_url'] as String?,
      voiceUrl: json['voice_url'] as String?,
    );
  }
}
