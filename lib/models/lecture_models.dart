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


enum ContentType {
  script,
  worksheet,
  quiz,
  summary,
  knowledgeGraph,
  unknown;

  static ContentType fromString(String? value) {
    switch (value) {
      case 'script':
        return ContentType.script;
      case 'worksheet':
        return ContentType.worksheet;
      case 'quiz':
        return ContentType.quiz;
      case 'summary':
        return ContentType.summary;
      case 'knowledge_graph':
        return ContentType.knowledgeGraph;
      default:
        return ContentType.unknown;
    }
  }
}

// ── Start Session ─────────────────────────────────────────────────────────────

class LectureResource {
  final String
  resourceType; // pdf · docx · pptx · audio · video · website · image · txt
  final String filePath;
  final String query;

  const LectureResource({
    required this.resourceType,
    required this.filePath,
    required this.query,
  });

  Map<String, dynamic> toJson() => {
    'resource_type': resourceType,
    'file_path': filePath,
    'query': query,
  };
}

class StartSessionRequest {
  final String title;
  final String courseCode;
  final List<LectureResource> resources;

  const StartSessionRequest({
    required this.title,
    required this.courseCode,
    required this.resources,
  });

  Map<String, dynamic> toJson() => {
    'title': title,
    'course_code': courseCode,
    'resources': resources.map((r) => r.toJson()).toList(),
  };
}

class StartSessionResponse {
  final int sessionId;
  final int lectureId;
  final String threadId;
  final String status;

  const StartSessionResponse({
    required this.sessionId,
    required this.lectureId,
    required this.threadId,
    required this.status,
  });

  factory StartSessionResponse.fromJson(Map<String, dynamic> json) =>
      StartSessionResponse(
        sessionId: json['session_id'] as int,
        lectureId: json['lecture_id'] as int,
        threadId: json['thread_id'] as String,
        status: json['status'] as String,
      );
}

// ── Session Status ────────────────────────────────────────────────────────────

class LectureVersion {
  final int versionNumber;
  final String pdfPath;
  final String status; // pending · approved · rejected

  const LectureVersion({
    required this.versionNumber,
    required this.pdfPath,
    required this.status,
  });

  factory LectureVersion.fromJson(Map<String, dynamic> json) => LectureVersion(
    versionNumber: json['version_number'] as int,
    pdfPath: json['pdf_path'] as String,
    status: json['status'] as String,
  );
}


// ── SSE Stream Event ──────────────────────────────────────────────────────────

class LecturePaths {
  final String? pdf;
  final String? txt;
  final String? json;

  const LecturePaths({this.pdf, this.txt, this.json});

  factory LecturePaths.fromJson(Map<String, dynamic> json) => LecturePaths(
    pdf: json['pdf'] as String?,
    txt: json['txt'] as String?,
    json: json['json'] as String?,
  );
}

// ── Content ───────────────────────────────────────────────────────────────────

class ContentItem {
  final ContentType type;
  final String filePath;
  final String? answersPath;
  final String? extraPath;

  const ContentItem({
    required this.type,
    required this.filePath,
    this.answersPath,
    this.extraPath,
  });

  factory ContentItem.fromJson(Map<String, dynamic> json) => ContentItem(
    type: ContentType.fromString(json['type'] as String?),
    filePath: json['file_path'] as String,
    answersPath: json['answers_path'] as String?,
    extraPath: json['extra_path'] as String?,
  );
}

class SessionContent {
  final int lectureId;
  final List<ContentItem> content;

  const SessionContent({required this.lectureId, required this.content});

  factory SessionContent.fromJson(Map<String, dynamic> json) => SessionContent(
    lectureId: json['lecture_id'] as int,
    content: (json['content'] as List<dynamic>)
        .map((e) => ContentItem.fromJson(e as Map<String, dynamic>))
        .toList(),
  );
}
enum ProcessingLifecycle {
  idle,
  starting,
  processing,
  awaitingApproval,
  completed,
  failed,
}

class LectureProcessingModel {
  final String? sessionId;
  final String currentStepKey;
  final ProcessingLifecycle lifecycle;
  final double progress;
  final int currentStep;
  final int totalSteps;
  final String stageTitle;
  final String stageDescription;
  final String estimatedTimeLabel;
  final String? errorMessage;

  const LectureProcessingModel({
    this.sessionId,
    this.currentStepKey = 'starting',
    this.lifecycle = ProcessingLifecycle.idle,
    this.progress = 0.0,
    this.currentStep = 1,
    this.totalSteps = 3,
    this.stageTitle = '',
    this.stageDescription = '',
    this.estimatedTimeLabel = '',
    this.errorMessage,
  });

  bool get isTerminal =>
      lifecycle == ProcessingLifecycle.completed ||
      lifecycle == ProcessingLifecycle.failed;

  bool get isAwaitingApproval =>
      lifecycle == ProcessingLifecycle.awaitingApproval;
  bool get isDone => lifecycle == ProcessingLifecycle.completed;
  String get Title => _title(stageTitle);

  // Add to LectureProcessingJob
  static ProcessingLifecycle parseLifecycle(String? s) => _parseLifecycle(s);
  LectureProcessingModel copyWith({
    String? sessionId,
    String? currentStepKey,
    ProcessingLifecycle? lifecycle,
    double? progress,
    int? currentStep,
    int? totalSteps,
    String? stageTitle,
    String? stageDescription,
    String? estimatedTimeLabel,
    String? errorMessage,
  }) {
    return LectureProcessingModel(
      sessionId: sessionId ?? this.sessionId,
      currentStepKey: currentStepKey ?? this.currentStepKey,
      lifecycle: lifecycle ?? this.lifecycle,
      progress: progress ?? this.progress,
      currentStep: currentStep ?? this.currentStep,
      totalSteps: totalSteps ?? this.totalSteps,
      stageTitle: stageTitle ?? this.stageTitle,
      stageDescription: stageDescription ?? this.stageDescription,
      estimatedTimeLabel: estimatedTimeLabel ?? this.estimatedTimeLabel,
      errorMessage: errorMessage,
    );
  }

  factory LectureProcessingModel.fromApi(Map<String, dynamic> json) {
    final rawProgress = json['progress_percent'] ?? json['progress'];
    final normalizedProgress = rawProgress is num
        ? (rawProgress > 1 ? rawProgress / 100.0 : rawProgress.toDouble())
        : 0.0;

    final currentStepKey =
        json['current_step']?.toString() ??
        json['status']?.toString() ??
        'starting';

    return LectureProcessingModel(
      sessionId: json['session_id']?.toString(),
      currentStepKey: currentStepKey,
      lifecycle: _parseLifecycle(
        json['step_label']?.toString() ?? currentStepKey,
      ),
      progress: normalizedProgress.clamp(0.0, 1.0),
      currentStep: (json['step_number'] as num?)?.toInt() ?? 1,
      totalSteps: (json['total_steps'] as num?)?.toInt() ?? 3,
      stageTitle: json['step_label']?.toString() ?? '',
      stageDescription: json['description']?.toString() ?? '',
      estimatedTimeLabel: _estimateLabel(json),
      errorMessage: json['error']?.toString(),
    );
  }

  static ProcessingLifecycle _parseLifecycle(String? status) {
    switch (status?.toLowerCase()) {
      case 'starting':
        return ProcessingLifecycle.starting;
      case 'generating_lecture':
      case 'regenerating':
      case 'generating_content':
        return ProcessingLifecycle.processing;
      case 'awaiting_approval':
        return ProcessingLifecycle.awaitingApproval;
      case 'done':
      case 'completed':
        return ProcessingLifecycle.completed;
      case 'failed':
      case 'error':
        return ProcessingLifecycle.failed;
      default:
        return ProcessingLifecycle.idle;
    }
  }

  String _title(String stageTitle) {
    switch (stageTitle) {
      case 'starting':
        return 'Starting';
      case 'generating_lecture':
        return 'Generating Lecture';
      case 'awaiting_approval':
        return 'Awaiting Approval';
      case 'regenerating':
        return 'Regenerating';
      case 'generating_content':
        return 'Generating Content';
      case 'done':
        return 'Done';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  }

  static String _estimateLabel(Map<String, dynamic> json) {
    if (json['current_step']?.toString() == 'done') return '0s';
    final seconds = (json['eta_seconds'] as num?)?.toInt();
    if (seconds == null || seconds <= 0) return '';
    if (seconds < 60) return '${seconds}s';
    final mins = (seconds / 60).ceil();
    return '$mins min${mins == 1 ? '' : 's'}';
  }
}


