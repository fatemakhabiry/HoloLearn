import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../utils/app_state.dart';

class AvatarService {
  // Check avatar status
  static Future<Map<String, dynamic>> checkAvatarStatus() async {
    final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.avatarStatusEndpoint));

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Bearer ${AppState.accessToken}',
        'ngrok-skip-browser-warning': 'true',
        'Accept': 'application/json',
      },
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      AppState.isFirstTimeLogin = data['needs_profile_setup'];
      print( AppState.isFirstTimeLogin);
      return data;
    } else {
      throw Exception(
        'Failed to check avatar status: ${response.statusCode} ${response.body}',
      );
    }
  }

  //   // Upload avatar (photo + voice)
  //   static Future<Map<String, dynamic>> uploadAvatar({
  //     required File photoFile,
  //     required File voiceFile,
  //   }) async {
  //     final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadAvatarEndpoint));

  //     var request = http.MultipartRequest('POST', uri);

  //     // Add headers
  //     request.headers['Authorization'] = 'Bearer ${AppState.accessToken}';

  //     // Add photo file
  //     request.files.add(
  //       await http.MultipartFile.fromPath(
  //         'photo',
  //         photoFile.path,
  //       ),
  //     );

  //     // Add voice file
  //     request.files.add(
  //       await http.MultipartFile.fromPath(
  //         'voice_sample',
  //         voiceFile.path,
  //       ),
  //     );

  //     final streamedResponse = await request.send();
  //     final response = await http.Response.fromStream(streamedResponse);

  //     if (response.statusCode == 200) {
  //       final data = jsonDecode(response.body) as Map<String, dynamic>;
  //       return data;
  //     } else {
  //       throw Exception('Failed to upload avatar: ${response.statusCode} ${response.body}');
  //     }
  //   }

  //   // Upload only photo
  //   static Future<Map<String, dynamic>> uploadPhoto({
  //     required File photoFile,
  //   }) async {
  //     final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadPhotoEndpoint));

  //     var request = http.MultipartRequest('POST', uri);
  //     request.headers['Authorization'] = 'Bearer ${AppState.accessToken}';

  //     request.files.add(
  //       await http.MultipartFile.fromPath(
  //         'photo',
  //         photoFile.path,
  //       ),
  //     );

  //     final streamedResponse = await request.send();
  //     final response = await http.Response.fromStream(streamedResponse);

  //     if (response.statusCode == 200) {
  //       final data = jsonDecode(response.body) as Map<String, dynamic>;
  //       return data;
  //     } else {
  //       throw Exception('Failed to upload photo: ${response.statusCode} ${response.body}');
  //     }
  //   }

  //   // Upload only voice
  //   static Future<Map<String, dynamic>> uploadVoiceSample({
  //     required File voiceFile,
  //   }) async {
  //     final uri = Uri.parse(ApiConfig.getUrl(ApiConfig.uploadVoiceEndpoint));

  //     var request = http.MultipartRequest('POST', uri);
  //     request.headers['Authorization'] = 'Bearer ${AppState.accessToken}';

  //     request.files.add(
  //       await http.MultipartFile.fromPath(
  //         'voice_sample',
  //         voiceFile.path,
  //       ),
  //     );

  //     final streamedResponse = await request.send();
  //     final response = await http.Response.fromStream(streamedResponse);

  //     if (response.statusCode == 200) {
  //       final data = jsonDecode(response.body) as Map<String, dynamic>;
  //       return data;
  //     } else {
  //       throw Exception('Failed to upload voice: ${response.statusCode} ${response.body}');
  //     }
  //   }
}
