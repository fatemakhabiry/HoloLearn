import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/qa_models.dart';
import '../providers/app_state_provider.dart';

/// Handles all Student Q&A API calls.
///
/// Endpoints (FastAPI  app/api/v1/endpoints/qa.py):
///   1. POST  /qa/{lecture_id}/ask           → askQuestion()
///   2. GET   /qa/{lecture_id}/history       → getHistory()
///   3. GET   /qa/{lecture_id}/status        → getIndexStatus()
///   4. GET   /qa/audio/{message_id}         → getAudioBytes()
///   5. DELETE /qa/session/{session_id}      → clearSession()
class QAService {
  // ─── Shared helpers ───────────────────────────────────────────────────────

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
    throw Exception('QA API error ${res.statusCode}: $detail');
  }

  // ─── 1. Ask a Question ────────────────────────────────────────────────────

  /// Send a text question (or voice file) about [lectureId].
  ///
  /// [text]      — plain text question (required when [voiceFile] is null)
  /// [voiceFile] — audio File recorded by the student (optional)
  ///
  /// Returns [QAAskResponse] containing the student message + AI answer.
  static Future<QAAskResponse> askQuestion({
    required AppStateProvider appState,
    required int lectureId,
    String? text,
    File? voiceFile,
  }) async {
    assert(
      text != null || voiceFile != null,
      'Either text or voiceFile must be provided.',
    );

    final url = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.qaAskEndpoint.replaceFirst(
          '{lecture_id}',
          lectureId.toString(),
        ),
      ),
    );

    final request = http.MultipartRequest('POST', url)
      ..headers.addAll(_headers(appState.accessToken));

    if (text != null && text.isNotEmpty) {
      request.fields['text'] = text;
    }

    if (voiceFile != null) {
      request.files.add(
        await http.MultipartFile.fromPath(
          'voice_file',
          voiceFile.path,
          // Let the server infer media type; common: audio/m4a, audio/wav
        ),
      );
    }

    try {
      final streamed = await request.send().timeout(
        ApiConfig.connectionTimeout,
      );
      final res = await http.Response.fromStream(streamed);
      _checkStatus(res);
      return QAAskResponse.fromJson(
        jsonDecode(res.body) as Map<String, dynamic>,
      );
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }

  // ─── 2. Get Chat History ──────────────────────────────────────────────────

  /// Load paginated chat history for the current student in [lectureId].
  ///
  /// Messages are returned oldest-first.
  static Future<QAChatHistory> getHistory({
    required AppStateProvider appState,
    required int lectureId,
    int page = 1,
    int pageSize = 20,
  }) async {
    final url =
        Uri.parse(
          ApiConfig.getUrl(
            ApiConfig.qaHistoryEndpoint.replaceFirst(
              '{lecture_id}',
              lectureId.toString(),
            ),
          ),
        ).replace(
          queryParameters: {
            'page': page.toString(),
            'page_size': pageSize.toString(),
          },
        );

    try {
      final res = await http
          .get(url, headers: _headers(appState.accessToken))
          .timeout(ApiConfig.connectionTimeout);

      _checkStatus(res);
      return QAChatHistory.fromJson(
        jsonDecode(res.body) as Map<String, dynamic>,
      );
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }

  // ─── 3. Check Index Status ────────────────────────────────────────────────

  /// Poll whether [lectureId] is indexed and ready for Q&A.
  ///
  /// The mobile app should poll this before showing the chat UI and display
  /// a "preparing…" state while [QALectureIndexStatus.status] != ready.
  static Future<QALectureIndexStatus> getIndexStatus({
    required AppStateProvider appState,
    required int lectureId,
  }) async {
    final url = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.qaIndexStatusEndpoint.replaceFirst(
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
      return QALectureIndexStatus.fromJson(
        jsonDecode(res.body) as Map<String, dynamic>,
      );
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }

  // ─── 4. Stream Answer Audio ───────────────────────────────────────────────

  /// Download the WAV audio bytes for assistant [messageId].
  ///
  /// Returns raw bytes you can play with `just_audio` or similar:
  ///   final bytes = await QAService.getAudioBytes(...);
  ///   // Write to a temp file, then play it.
  static Future<List<int>> getAudioBytes({
    required AppStateProvider appState,
    required int messageId,
  }) async {
    final url = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.qaAudioEndpoint.replaceFirst(
          '{message_id}',
          messageId.toString(),
        ),
      ),
    );

    try {
      final res = await http
          .get(
            url,
            headers: {..._headers(appState.accessToken), 'Accept': 'audio/wav'},
          )
          .timeout(const Duration(seconds: 60)); // audio may be larger

      if (res.statusCode == 404) {
        throw Exception('Audio not available for this message.');
      }
      if (res.statusCode == 410) {
        throw Exception('Audio file has been removed from the server.');
      }
      _checkStatus(res);
      return res.bodyBytes;
    } on TimeoutException {
      throw Exception('Audio download timed out.');
    }
  }

  // ─── 5. Clear Session ─────────────────────────────────────────────────────

  /// Delete all messages in the student's chat session [sessionId].
  static Future<void> clearSession({
    required AppStateProvider appState,
    required int sessionId,
  }) async {
    final url = Uri.parse(
      ApiConfig.getUrl(
        ApiConfig.qaClearSessionEndpoint.replaceFirst(
          '{session_id}',
          sessionId.toString(),
        ),
      ),
    );

    try {
      final res = await http
          .delete(url, headers: _headers(appState.accessToken))
          .timeout(ApiConfig.connectionTimeout);

      _checkStatus(res);
    } on TimeoutException {
      throw Exception('Request timed out. Please try again.');
    }
  }
}
