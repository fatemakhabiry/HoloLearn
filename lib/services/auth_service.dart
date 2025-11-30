import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';


class AuthService {
  static Future <Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.loginEndpoint));

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'username': email,
        'password': password,
      },
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return data;
    } else {
      throw Exception('Login failed: ${response.statusCode} ${response.body}');
    }
  }
}
