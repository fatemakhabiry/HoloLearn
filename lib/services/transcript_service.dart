import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/transcript_models.dart';
import '../providers/app_state_provider.dart';

/// Handles the lecture transcript API call.
///
/// Endpoint (FastAPI  app/api/v1/endpoints/lecture.py):
///   GET  /{lecture_id}/transcript  → getTranscript()
class TranscriptService {
  static Map<String, String> _headers(String token) => {
    'Accept': 'application/json',
    'ngrok-skip-browser-warning': 'true',
    'Authorization': 'Bearer $token',
  };

  static void _checkStatus(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) return;

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
    throw Exception('Transcript API error ${res.statusCode}: $detail');
  }

  /// Fetch the timestamped transcript for [lectureId].
  ///
  /// Returns a list of [TranscriptSegment] sorted by [startSeconds].
  /// Throws an [Exception] with a user-readable message on any failure.
  static Future<List<TranscriptSegment>> getTranscript({
    required AppStateProvider appState,
    required int lectureId,
  }) async {
    final url = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.lectureTranscriptEndpoint.replaceFirst(
          '{lecture_id}',
          lectureId.toString(),
        ),
      ),
    );

    try {
      final res = await http
          .get(url, headers: _headers(appState.accessToken))
          .timeout(ApiConfig.connectionTimeout);

      _checkStatus(res);

      final raw = jsonDecode(res.body) as List<dynamic>;
      return raw
          .map((e) => TranscriptSegment.fromJson(e as Map<String, dynamic>))
          .toList();
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }
}
