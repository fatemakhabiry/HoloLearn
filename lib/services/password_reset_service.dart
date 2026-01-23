import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class PasswordResetService {
  /// Request OTP code - sends to user's email
  static Future<String> requestOTP(String email) async {
    final response = await http.post(
      Uri.parse(ApiConfig.getUrl(ApiConfig.forgotPasswordEndpoint)),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email}),
    );

    final body = json.decode(response.body);

    switch (response.statusCode) {
      case 200:
        return body['message'];

      case 400:
        throw Exception('Invalid email format');

      case 404:
        throw Exception('Email not found');

      case 429:
        throw Exception('Too many requests. Please try again later');

      case 500:
        throw Exception('Server error. Please try again later');

      default:
        throw Exception('Failed to send OTP error :(${response.statusCode})');
    }
  }

  /// Verify OTP code
  static Future<Map<String, dynamic>> verifyOTP(
    String email,
    String otpCode,
  ) async {
    final response = await http
        .post(
          Uri.parse(ApiConfig.getUrl(ApiConfig.verifyOtpEndpoint)),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({'email': email, 'otp_code': otpCode}),
        )
        .timeout(ApiConfig.connectionTimeout);

    final body = json.decode(response.body);

    switch (response.statusCode) {
      case 200:
        return body;

      case 400:
        throw Exception('Invalid OTP format');

      case 401:
        throw Exception('OTP expired or invalid');

      case 404:
        throw Exception('OTP not found');

      case 429:
        throw Exception('Too many attempts. Try again later');

      case 500:
        throw Exception('Server error. Please try again later');

      default:
        throw Exception(
          'OTP verification failed error (${response.statusCode})',
        );
    }
  }

  /// Reset password with OTP
  static Future<String> resetPassword({
    required String email,
    required String otpCode,
    required String newPassword,
  }) async {
    final response = await http
        .post(
          Uri.parse(ApiConfig.getUrl(ApiConfig.resetPasswordEndpoint)),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'email': email,
            'otp_code': otpCode,
            'new_password': newPassword,
            'confirm_password': newPassword,
          }),
        )
        .timeout(ApiConfig.connectionTimeout);

    final body = json.decode(response.body);

    switch (response.statusCode) {
      case 200:
        return body['message'];

      case 400:
        throw Exception(body['detail'] ?? 'Passwords do not match');

      case 401:
        throw Exception('Invalid or expired OTP');

      case 404:
        throw Exception('User not found');

      case 422:
        throw Exception('Password does not meet security requirements');

      case 500:
        throw Exception('Server error. Please try again later');

      default:
        throw Exception('Password reset failed error (${response.statusCode})');
    }
  }

  static Future<String> changePassword({
    required String email,
    required String oldPassword,
    required String newPassword,
  }) async {
    final response = await http
        .post(
          Uri.parse(ApiConfig.getUrl(ApiConfig.changePasswordEndpoint)),
          headers: {'Content-Type': 'application/json'},
          body: json.encode({
            'email': email,
            'old_password': oldPassword,
            'new_password': newPassword,
          }),
        )
        .timeout(ApiConfig.connectionTimeout);

    final body = json.decode(response.body);

    switch (response.statusCode) {
      case 200:
        return body['message'];

      case 400:
        throw Exception('Invalid request');

      case 401:
        throw Exception('Old password is incorrect');

      case 404:
        throw Exception('User not found');

      case 422:
        throw Exception('New password is too weak');

      case 500:
        throw Exception('Server error. Please try again later');

      default:
        throw Exception(
          body['detail'] ?? 'Change password failed (${response.statusCode})',
        );
    }
  }

  /// Resend OTP code
  static Future<String> resendOTP(String email) async {
    print(email);
    final response = await http
        .post(
          Uri.parse(ApiConfig.getUrl(ApiConfig.resendOtpEndpoint)),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'email': email}),
        )
        .timeout(ApiConfig.connectionTimeout);

    switch (response.statusCode) {
      case 200:
        final data = jsonDecode(response.body);
        return data['message'] ?? 'OTP sent successfully';

      case 400:
        throw Exception('Invalid request: Please check the email address.');

      case 401:
        throw Exception('Unauthorized: Please log in again.');

      case 404:
        throw Exception('Email not found.');

      case 409:
        throw Exception('OTP already sent. Please wait before retrying.');

      case 422:
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? errorData['message'] ?? 'Validation error: Invalid email format.');

      case 429:
        throw Exception('Too many requests: Please wait and try again later.');

      case 500:
        throw Exception('Server error: Please try again later.');

      case 502:
      case 503:
      case 504:
        throw Exception('Service unavailable: Please try again later.');

      default:
        final errorBody = response.body.isNotEmpty
            ? response.body
            : 'No response body';
        throw Exception(
          'Unexpected error (${response.statusCode}): $errorBody',
        );
    }
  }
}
