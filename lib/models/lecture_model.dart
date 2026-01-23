/// Models for lecture-related data

class LectureCreateResponse {
  final String title;
  final int lectureId;
  final int teacherId;
  final String lectureType;
  final String courseCode;

  LectureCreateResponse({
    required this.title,
    required this.lectureId,
    required this.teacherId,
    required this.lectureType,
    required this.courseCode,
  });

  factory LectureCreateResponse.fromJson(Map<String, dynamic> json) {
    return LectureCreateResponse(
      title: json['title'].toString(),
      lectureId: int.parse(json['lecture_id'].toString()),
      teacherId: int.parse(json['teacher_id'].toString()),
      lectureType: json['lecture_type'],
      courseCode: json['course_code'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'title': title,
      'lecture_id': lectureId,
      'teacher_id': teacherId,
      'lecture_type': lectureType,
      'course_code': courseCode,
    };
  }
}

class LecturePublishResponse {
  final String message;
  final int lectureId;
  final int scheduleId;
  final String lectureTitle;
  final String courseCode;
  final String lectureStatus;
  final String scheduleStatus;
  final String scheduledDate;
  final String startTime;
  final String endTime;

  LecturePublishResponse({
    required this.message,
    required this.lectureId,
    required this.scheduleId,
    required this.lectureTitle,
    required this.courseCode,
    required this.lectureStatus,
    required this.scheduleStatus,
    required this.scheduledDate,
    required this.startTime,
    required this.endTime,
  });

  factory LecturePublishResponse.fromJson(Map<String, dynamic> json) {
    return LecturePublishResponse(
      message: json['message'],
      lectureId: json['lecture_id'],
      scheduleId: json['schedule_id'],
      lectureTitle: json['lecture_title'],
      courseCode: json['course_code'],
      lectureStatus: json['lecture_status'],
      scheduleStatus: json['schedule_status'],
      scheduledDate: json['scheduled_date'],
      startTime: json['start_time'],
      endTime: json['end_time'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'message': message,
      'lecture_id': lectureId,
      'schedule_id': scheduleId,
      'lecture_title': lectureTitle,
      'course_code': courseCode,
      'lecture_status': lectureStatus,
      'schedule_status': scheduleStatus,
      'scheduled_date': scheduledDate,
      'start_time': startTime,
      'end_time': endTime,
    };
  }
}

class LectureDetailResponse {
  final int lectureId;
  final int scheduleId;
  final String title;
  final String courseCode;
  final String currentFileUrl;
  final String currentFileName;
  final String scheduledDate;
  final String startTime;
  final String endTime;
  final String status;

  LectureDetailResponse({
    required this.lectureId,
    required this.scheduleId,
    required this.title,
    required this.courseCode,
    required this.currentFileUrl,
    required this.currentFileName,
    required this.scheduledDate,
    required this.startTime,
    required this.endTime,
    required this.status,
  });

  factory LectureDetailResponse.fromJson(Map<String, dynamic> json) {
    return LectureDetailResponse(
      lectureId: json['lecture_id'] ?? 0,
      scheduleId: json['schedule_id'] ?? 0,
      title: json['title'] ?? '',
      courseCode: json['course_code'] ?? '',
      currentFileUrl: json['current_file_url'] ?? '',
      currentFileName: json['current_file_name'] ?? '',
      scheduledDate: json['scheduled_date'] ?? '',
      startTime: json['start_time'] ?? '',
      endTime: json['end_time'] ?? '',
      status: json['status'] ?? 'scheduled',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'lecture_id': lectureId,
      'schedule_id': scheduleId,
      'title': title,
      'course_code': courseCode,
      'current_file_url': currentFileUrl,
      'current_file_name': currentFileName,
      'scheduled_date': scheduledDate,
      'start_time': startTime,
      'end_time': endTime,
      'status': status,
    };
  }
}

class LectureUpdateResponse {
  final String message;
  final int lectureId;
  final int scheduleId;
  final String lectureTitle;
  final String courseCode;
  final String lectureStatus;
  final String scheduledDate;
  final String startTime;
  final String endTime;
  final String scheduleStatus;
  final bool fileUpdated;
  final String? fileUrl;
  final bool scheduleChanged;

  LectureUpdateResponse({
    required this.message,
    required this.lectureId,
    required this.scheduleId,
    required this.lectureTitle,
    required this.courseCode,
    required this.lectureStatus,
    required this.scheduledDate,
    required this.startTime,
    required this.endTime,
    required this.scheduleStatus,
    required this.fileUpdated,
    this.fileUrl,
    required this.scheduleChanged,
  });

  factory LectureUpdateResponse.fromJson(Map<String, dynamic> json) {
    return LectureUpdateResponse(
      message: json['message'] ?? '',
      lectureId: json['lecture_id'] ?? 0,
      scheduleId: json['schedule_id'] ?? 0,
      lectureTitle: json['lecture_title'] ?? '',
      courseCode: json['course_code'] ?? '',
      lectureStatus: json['lecture_status'] ?? '',
      scheduledDate: json['scheduled_date'] ?? '',
      startTime: json['start_time'] ?? '',
      endTime: json['end_time'] ?? '',
      scheduleStatus: json['schedule_status'] ?? '',
      fileUpdated: json['file_updated'] ?? false,
      fileUrl: json['file_url'],
      scheduleChanged: json['schedule_changed'] ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'message': message,
      'lecture_id': lectureId,
      'schedule_id': scheduleId,
      'lecture_title': lectureTitle,
      'course_code': courseCode,
      'lecture_status': lectureStatus,
      'scheduled_date': scheduledDate,
      'start_time': startTime,
      'end_time': endTime,
      'schedule_status': scheduleStatus,
      'file_updated': fileUpdated,
      'file_url': fileUrl,
      'schedule_changed': scheduleChanged,
    };
  }
}