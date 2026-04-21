class ApiConfig {
  // UPDATE THIS WITH YOUR NGROK URL OR LOCAL IP
  static const String baseUrl =
      'https://unpointed-lynne-paradingly.ngrok-free.dev/api/v1';

  // ===== Authentication Endpoints =====
  static const String loginEndpoint = '/auth/login';

  // ===== User Endpoints =====
  static const String userProfileEndpoint = '/users/me';
  static const String updateProfileEndpoint = '/users/me';

  // ===== Teacher Endpoints =====
  static const String teacherProfileEndpoint = '/teachers/profile';
  static const String avatarStatusEndpoint = '/teachers/profile-status';
  static const String teacherUploadPhotoEndpoint = '/teachers/upload-photo';
  static const String teacherUploadVoiceEndpoint = '/teachers/upload-voice';

  // ===== Password Reset / OTP Endpoints =====
  static const String forgotPasswordEndpoint =
      '/password_reset/forgot-password';
  static const String verifyOtpEndpoint = '/password_reset/verify-otp';
  static const String resetPasswordEndpoint = '/password_reset/reset-password';
  static const String changePasswordEndpoint =
      '/password_reset/change-password';
  static const String resendOtpEndpoint = '/password_reset/resend-otp';

  // ===== Schedule Endpoints =====
  static const String reservedSlotsEndpoint =
      '/schedules/my-scheduled-lectures';
  static const String availabilitySlotsEndpoint = '/schedules/available-slots';

  // Lecture endpoints
  static const String lecturesEndpoint = '/lecture/';
  //prepared lecture endpoints
  static const String createLectureDraftEndpoint = '/lecture/create-draft';
  static const String startPreparedEndpoint =
      '/sessions/start-prepared/{lecture_id}';
  //Generated lecture endpoints
  static const String uploadGeneratedFileEndpoint ="/session/upload-resource";
  static const String startGeneratedSessionEndpoint =
       '/session/start';
  static const String getSessionStatusEndpoint =
      '/session/{session_id}/status';
  static const String getSessionStreamEndpoint =
      '/session/{session_id}/stream';
  static const String approveSessionEndpoint = '/session/{session_id}/approve';
  static const String rejectWithFeedbackSessionEndpoint =
      '/session/{session_id}/reject';
  static const String getLectureContentEndpoint =
      '/session/{session_id}/content';
  static const String getLecturePdfEndpoint =
      '/session/{session_id}/lecture-pdf';

  static const String publishLectureEndpoint =
      '/lecture/{lecture_id}/confirm-and-publish';
  static const String lectureHistoryendpoint = '/lecture/all-my-lectures';

  // Delete and update endpoints with placeholders
  // Note: {schedule_id} will be replaced with actual ID in the service
  static const String deleteLectureEndpoint = '/schedules/{schedule_id}/cancel';
  static const String updateLectureEndpoint =
      '/lecture/schedule/{schedule_id}/edit';
  static const String getLectureDetailsEndpoint =
      '/lecture/schedule/{schedule_id}/edit-details';
  // ===== Student Endpoints =====
  static const String courseListEndpoint = '/courses/';
  static const String studentLectureEndpoint = '/student/upcoming-lectures';

  // ===== Token Settings =====
  static const Duration tokenExpiry = Duration(minutes: 30);

  // ===== API Timeouts =====
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // ===== Helper Methods =====

  // Build full URL
  static String getUrl(String endpoint) => baseUrl + endpoint;
}
