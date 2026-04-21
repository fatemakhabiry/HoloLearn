

import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/availability_models.dart';

class AvailabilityResponse {
  final String date;
  final List<AvailabilitySlot> availableSlots;

  AvailabilityResponse({required this.date, required this.availableSlots});

  factory AvailabilityResponse.fromJson(Map<String, dynamic> json) {
    final date = json['date'];

    return AvailabilityResponse(
      date: date,
      availableSlots: (json['available_slots'] as List).map((slot) {
        slot['date'] = date;
        return AvailabilitySlot.fromJson(slot);
      }).toList(),
    );
  }
}


class AvailabilityService {
  /// Fetch available time slots for a specific date
  static Future<AvailabilityResponse> fetchAvailableSlots({
    required String token,
    required String date,
  }) async {
    try {
      final uri = Uri.parse(
        ApiConfig.getUrl('${ApiConfig.availabilitySlotsEndpoint}/$date'),
      );

      print('📅 Fetching slots for: $date');
      print('🌐 URL: $uri');

      final response = await http
          .get(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
              'ngrok-skip-browser-warning': 'true',
            },
          )
          .timeout(ApiConfig.connectionTimeout);

      print('📡 Status: ${response.statusCode}');
      print('📥 Response: ${response.body}');

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return AvailabilityResponse.fromJson(data);
      } else if (response.statusCode == 401) {
        throw Exception('Unauthorized - Please login again');
      } else if (response.statusCode == 404) {
        throw Exception('No available slots found for this date');
      } else {
        final error = json.decode(response.body);
        throw Exception(error['detail'] ?? 'Failed to fetch available slots');
      }
    } catch (e) {
      print('❌ Error: $e');
      throw Exception('Network error: $e');
    }
  }


 
}
