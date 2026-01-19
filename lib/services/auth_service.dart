import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../utils/app_state.dart';

class AuthService {
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.loginEndpoint));

    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': email, 'password': password},
    );

    switch (response.statusCode) {
      case 200:
        final data = jsonDecode(response.body) as Map<String, dynamic>;

        AppState.email = data['user']['email'];
        AppState.userName = data['user']['full_name'];
        AppState.userRole = data['user']['role'];
        AppState.accessToken = data['access_token'];
        return data;

      case 400:
        throw Exception('Bad request: Please check your input data.'); 

      case 401:
        throw Exception('Login failed: Incorrect email or password.');

      case 403:
        throw Exception('Access denied: You do not have permission.');

      case 404:
        throw Exception('Server not found: Please try again later.');

      case 409:
        throw Exception('Conflict: Account already exists.');

      case 422:
        throw Exception('Validation error: Invalid email or password format.');

      case 429:
        throw Exception('Too many attempts: Please wait and try again.');

      case 500:
        throw Exception('Server error: Please try again later.');

      case 502:
      case 503:
      case 504:
        throw Exception('Service unavailable: Please try again later.');

      default:
        throw Exception('Unexpected error (${response.statusCode}');
    }
  }
}