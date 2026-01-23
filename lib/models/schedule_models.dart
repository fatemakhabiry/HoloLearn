/// Model for schedule data from API
class ScheduleSlot {
  final String startTime;
  final String endTime;
  final int? scheduleId;
  final int? lectureId;
  final String teacherName;
  final String lectureTitle;
  final String courseCode;
  final String status;
  final String? lectureType;
  final String? date;


  ScheduleSlot({
    required this.startTime,
    required this.endTime,
    this.scheduleId,
    this.lectureId,
    required this.teacherName,
    required this.lectureTitle,
    this.courseCode = '',
    this.status = '',
    this.lectureType,
    this.date,
  });

  /// Parse from API JSON
  factory ScheduleSlot.fromJson(Map<String, dynamic> json) {
    return ScheduleSlot(
      startTime: json['start_time'] ?? '',
      endTime: json['end_time'] ?? '',
      scheduleId: json['schedule_id'] ?? 0,
      lectureId: json['lecture_id'] ?? 0,
      teacherName: json['teacher_name'] ?? '',
      lectureTitle: json['lecture_title'] ?? '',
      courseCode: json['course_code'] ?? '',
      status: json['status'] ?? '',
      lectureType: json['lecture_type']?? '',
      date: json['date'] ?? '',
    );
  }

  /// Get DateTime objects for comparison and sorting
  DateTime get startDateTime {
    try {
      return DateTime.parse(startTime);
    } catch (e) {
      return DateTime.now();
    }
  }

  DateTime get endDateTime {
    try {
      return DateTime.parse(endTime);
    } catch (e) {
      return DateTime.now();
    }
  }

  /// Get session status
  SessionStatus get sessionStatus {
    final now = DateTime.now();
    if (now.isBefore(startDateTime)) {
      return SessionStatus.upcoming;
    } else if (now.isAfter(endDateTime)) {
      return SessionStatus.passed;
    } else {
      return SessionStatus.ongoing;
    }
  }

  /// Format time from "2025-01-20T10:00:00" to "10:00 AM"
  String formatTime(String isoTime) {
    try {
      final dateTime = DateTime.parse(isoTime);
      final hour = dateTime.hour;
      final minute = dateTime.minute.toString().padLeft(2, '0');
      final period = hour >= 12 ? 'PM' : 'AM';
      final displayHour = hour > 12 ? hour - 12 : (hour == 0 ? 12 : hour);
      return '$displayHour:$minute $period';
    } catch (e) {
      return isoTime;
    }
  }

  /// Get formatted time range "10:00 AM - 11:30 AM"
  String get timeRange {
    return '${formatTime(startTime)} - ${formatTime(endTime)}';
  }

  /// Format date from "2025-01-20T10:00:00" to "Oct 15, 2025"
  String get formattedDate {
    try {
      final dateTime = DateTime.parse(startTime);
      final months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec',
      ];
      return '${months[dateTime.month - 1]} ${dateTime.day}, ${dateTime.year}';
    } catch (e) {
      return '';
    }
  }

  /// Get remaining time until session starts
  String get remainingTime {
    final now = DateTime.now();
    final diff = startDateTime.difference(now);

    if (diff.isNegative) return '';
    final hours = diff.inHours;
    final minutes = diff.inMinutes.remainder(60);

    return hours > 0 ? '$hours hours and $minutes minutes' : '$minutes minutes';
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'start_time': startTime,
      'end_time': endTime,
      'schedule_id': scheduleId,
      'lecture_id': lectureId,
      'teacher_name': teacherName,
      'lecture_title': lectureTitle,
      'course_code': courseCode,
      'status': status,
      'lecture_type': lectureType,
      'date': date,
    };
  }
}

enum SessionStatus { upcoming, ongoing, passed }

/// Model for the complete API response
class ScheduleResponse {
  final List<ScheduleSlot> reservedSlots;

  ScheduleResponse({required this.reservedSlots});

  /// Parse complete API response
  factory ScheduleResponse.fromJson(Map<String, dynamic> json) {
    return ScheduleResponse(
      reservedSlots:
          (json['reserved_slots'] as List<dynamic>?)
              ?.map(
                (slot) => ScheduleSlot.fromJson(slot as Map<String, dynamic>),
              )
              .toList() ??
          [],
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'reserved_slots': reservedSlots.map((slot) => slot.toJson()).toList(),
    };
  }
}