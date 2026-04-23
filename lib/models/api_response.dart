
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

// File Upload Response Model
// class FileUploadResponse {
//   final String message;
//   final String? photoUrl;
//   final String? voiceUrl;

//   FileUploadResponse({
//     required this.message,
//     this.photoUrl,
//     this.voiceUrl,
//   });

//   factory FileUploadResponse.fromJson(Map<String, dynamic> json) {
//     return FileUploadResponse(
//       message: json['message'] as String,
//       photoUrl: json['photo_url'] as String?,
//       voiceUrl: json['voice_url'] as String?,
//     );
//   }
// }
