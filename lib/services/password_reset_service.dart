import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';

class PasswordResetService {
  /// Request OTP code - sends to user's email
  static Future<String> requestOTP(String email) async {
    print(email);
    final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.forgotPasswordEndpoint));

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json', // Changed to JSON
      },
      body: json.encode({
        // Encode as JSON
        'email': email,
      }),
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return data['message'];
    } else if (response.statusCode == 404) {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Email not found in system');
    } else {
      final error = json.decode(response.body);
      throw Exception(error['detail'] ?? 'Failed to send OTP');
    }
  }

  /// Verify OTP code
  static Future<Map<String, dynamic>> verifyOTP(String email, String otpCode) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.getUrl(ApiConfig.verifyOtpEndpoint)),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'email': email, 'otp_code': otpCode}),
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Invalid OTP');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Reset password with OTP
  static Future <String> resetPassword({
    required String email,
    required String otpCode,
    required String newPassword,
  }) async {
    try {
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

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['message'];
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to reset password');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }

  /// Resend OTP code
  static Future<String> resendOTP(String email) async {
    try {
      final response = await http
          .post(
            Uri.parse(ApiConfig.getUrl(ApiConfig.resendOtpEndpoint)),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'email': email}),
          )
          .timeout(ApiConfig.connectionTimeout);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return data['message'];
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to resend OTP');
      }
    } catch (e) {
      throw Exception('Network error: $e');
    }
  }
}
