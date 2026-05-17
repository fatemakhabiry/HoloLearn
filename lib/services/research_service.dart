import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/research_models.dart';
import '../providers/app_state_provider.dart';

class ResearchService {
  static final _client = http.Client();

  static Map<String, String> _headers(String token) => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'ngrok-skip-browser-warning': 'true',
        'Authorization': 'Bearer $token',
      };

  static void _checkStatus(http.Response res) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String detail = res.body;
      try {
        final decoded = jsonDecode(res.body);
        if (decoded is Map) {
          detail = decoded['detail']?.toString() ??
              decoded['message']?.toString() ??
              detail;
        }
      } catch (_) {}
      throw Exception(detail);
    }
  }

  /// POST /research/agent
  /// Body: { "question": topic }
  /// Returns a [ResearchResponse] with findings and sources.
  static Future<ResearchResponse> research({
    required String question,
    required AppStateProvider appState,
  }) async {
    final uri = Uri.parse(
        ApiConfig.getUrl(ApiConfig.researchAgentEndpoint));

    final res = await _client
        .post(
          uri,
          headers: _headers(appState.accessToken),
          body: jsonEncode({'question': question}),
        )
        .timeout(const Duration(minutes: 3)); // agent can take a while

    _checkStatus(res);

    final json = jsonDecode(res.body) as Map<String, dynamic>;
    return ResearchResponse.fromJson(json);
  }
}
