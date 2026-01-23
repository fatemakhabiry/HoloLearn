/// Model for schedule data from API
class ScheduleSlot {
  final String startTime;
  final String endTime;
  final int scheduleId;
  final String teacherName;
  final String lectureTitle;
  final String status;
  final int? lectureId; 
  final String? courseCode; 
  final String? date;  
  final String? lectureType;  

  ScheduleSlot({
    required this.startTime,
    required this.endTime,
    required this.scheduleId,
    required this.teacherName,
    required this.lectureTitle,
    required this.status,
    this.lectureId,  
    this.courseCode,  
    this.date,  
    this.lectureType,  
  });

  /// Parse from API JSON
  factory ScheduleSlot.fromJson(Map<String, dynamic> json) {
    return ScheduleSlot(
      startTime: json['start_time'] ?? '',
      endTime: json['end_time'] ?? '',
      scheduleId: json['schedule_id'] ?? 0,
      teacherName: json['teacher_name'] ?? '',
      lectureTitle: json['lecture_title'] ?? '',
      status: json['status'] ?? '',
      lectureId: json['lecture_id'],  
      courseCode: json['course_code'],  
      date: json['date'],  
      lectureType: json['lecture_type'],  
    );
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
      final dateTime = DateTime.parse(date ?? startTime);
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

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'start_time': startTime,
      'end_time': endTime,
      'schedule_id': scheduleId,
      'teacher_name': teacherName,
      'lecture_title': lectureTitle,
      'status': status,
      'lecture_id': lectureId, 
      'course_code': courseCode, 
      'date': date, 
      'lecture_type': lectureType, 
    };
  }
}