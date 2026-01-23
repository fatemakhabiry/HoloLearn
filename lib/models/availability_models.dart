/// Model for availability slot
class AvailabilitySlot {
  final int scheduleId;
  final DateTime startTime;
  final DateTime endTime;
  final String? teacherName;
  final String? lectureTitle;
  final String status;

  AvailabilitySlot({
    required this.scheduleId,
    required this.startTime,
    required this.endTime,
    this.teacherName,
    this.lectureTitle,
    required this.status,
  });

  factory AvailabilitySlot.fromJson(Map<String, dynamic> json) {
    final date = json['date'] ?? DateTime.now().toIso8601String().split('T')[0];

    return AvailabilitySlot(
      scheduleId: json['schedule_id'],
      startTime: _parseTimeToDateTime(json['start_time'], date),
      endTime: _parseTimeToDateTime(json['end_time'], date),
      teacherName: json['teacher_name'],
      lectureTitle: json['lecture_title'],
      status: json['status'] ?? 'available',
    );
  }

  static DateTime _parseTimeToDateTime(String timeString, String dateString) {
    try {
      final dateTime = DateTime.parse('${dateString}T$timeString');
      return dateTime;
    } catch (e) {
      print('Error parsing time: $timeString with date: $dateString');
      return DateTime.now();
    }
  }

  String get formattedTimeSlot {
    final startHour = startTime.hour.toString().padLeft(2, '0');
    final startMinute = startTime.minute.toString().padLeft(2, '0');
    final endHour = endTime.hour.toString().padLeft(2, '0');
    final endMinute = endTime.minute.toString().padLeft(2, '0');

    return "$startHour:$startMinute to $endHour:$endMinute";
  }

  Map<String, dynamic> toJson() {
    return {
      'schedule_id': scheduleId,
      'start_time': startTime.toIso8601String(),
      'end_time': endTime.toIso8601String(),
      'teacher_name': teacherName,
      'lecture_title': lectureTitle,
      'status': status,
    };
  }
}

/// Response wrapper for availability slots
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

  Map<String, dynamic> toJson() {
    return {
      'date': date,
      'available_slots': availableSlots.map((slot) => slot.toJson()).toList(),
    };
  }
}