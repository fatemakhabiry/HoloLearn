import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../state/providers/app_state_provider.dart';

/// Handles avatar and profile-related operations
class AvatarService {
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

  // Note: The following methods are commented out in the original file
  // Uncomment and implement when needed
  
  // /// Upload avatar (photo + voice)
  // static Future<Map<String, dynamic>> uploadAvatar({
  //   required AppStateProvider appState,
  //   required File photoFile,
  //   required File voiceFile,
  // }) async {
  //   final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadAvatarEndpoint));
  //
  //   var request = http.MultipartRequest('POST', uri);
  //
  //   // Add headers
  //   request.headers['Authorization'] = 'Bearer ${appState.accessToken}';
  //
  //   // Add photo file
  //   request.files.add(
  //     await http.MultipartFile.fromPath('photo', photoFile.path),
  //   );
  //
  //   // Add voice file
  //   request.files.add(
  //     await http.MultipartFile.fromPath('voice_sample', voiceFile.path),
  //   );
  //
  //   final streamedResponse = await request.send();
  //   final response = await http.Response.fromStream(streamedResponse);
  //
  //   if (response.statusCode == 200) {
  //     return jsonDecode(response.body) as Map<String, dynamic>;
  //   } else {
  //     throw Exception('Failed to upload avatar: ${response.statusCode} ${response.body}');
  //   }
  // }
  //
  // /// Upload only photo
  // static Future<Map<String, dynamic>> uploadPhoto({
  //   required AppStateProvider appState,
  //   required File photoFile,
  // }) async {
  //   final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadPhotoEndpoint));
  //
  //   var request = http.MultipartRequest('POST', uri);
  //   request.headers['Authorization'] = 'Bearer ${appState.accessToken}';
  //
  //   request.files.add(
  //     await http.MultipartFile.fromPath('photo', photoFile.path),
  //   );
  //
  //   final streamedResponse = await request.send();
  //   final response = await http.Response.fromStream(streamedResponse);
  //
  //   if (response.statusCode == 200) {
  //     return jsonDecode(response.body) as Map<String, dynamic>;
  //   } else {
  //     throw Exception('Failed to upload photo: ${response.statusCode} ${response.body}');
  //   }
  // }
  //
  // /// Upload only voice
  // static Future<Map<String, dynamic>> uploadVoiceSample({
  //   required AppStateProvider appState,
  //   required File voiceFile,
  // }) async {
  //   final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadVoiceEndpoint));
  //
  //   var request = http.MultipartRequest('POST', uri);
  //   request.headers['Authorization'] = 'Bearer ${appState.accessToken}';
  //
  //   request.files.add(
  //     await http.MultipartFile.fromPath('voice_sample', voiceFile.path),
  //   );
  //
  //   final streamedResponse = await request.send();
  //   final response = await http.Response.fromStream(streamedResponse);
  //
  //   if (response.statusCode == 200) {
  //     return jsonDecode(response.body) as Map<String, dynamic>;
  //   } else {
  //     throw Exception('Failed to upload voice: ${response.statusCode} ${response.body}');
  //   }
  // }
}