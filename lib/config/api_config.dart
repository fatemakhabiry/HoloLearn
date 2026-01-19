class ApiConfig {
  // UPDATE THIS WITH YOUR NGROK URL OR LOCAL IP
  static const String baseUrl =
      'https://unflinchingly-effortful-deacon.ngrok-free.dev/api/v1';

  // ===== Authentication Endpoints =====
  static const String loginEndpoint = '/auth/login';

  // ===== User Endpoints =====
  static const String userProfileEndpoint = '/users/me';
  static const String updateProfileEndpoint = '/users/me';

  // ===== Teacher Endpoints =====
  static const String teacherProfileEndpoint = '/teachers/profile';
  static const String avatarStatusEndpoint =
      '/teachers/profile-status';
  static const String teacherUploadPhotoEndpoint = '/teachers/upload-photo';
  static const String teacherUploadVoiceEndpoint = '/teachers/upload-voice';

  // ===== Password Reset / OTP Endpoints =====
  static const String forgotPasswordEndpoint =
      '/password_reset/forgot-password';
  static const String verifyOtpEndpoint = '/password_reset/verify-otp';
  static const String resetPasswordEndpoint = '/password_reset/reset-password';
  static const String changePasswordEndpoint = '/password_reset/change-password';
  static const String resendOtpEndpoint = '/password_reset/resend-otp';

  // ===== Storage Keys =====
  static const String accessTokenKey = 'access_token';
  static const String userIdKey = 'user_id';
  static const String userEmailKey = 'user_email';
  static const String userRoleKey = 'user_role';
  static const String userNameKey = 'user_name';

  // ===== Token Settings =====
  static const Duration tokenExpiry = Duration(minutes: 30);

  // ===== API Timeouts =====
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // ===== Helper Methods =====

  // Build full URL
  static String getUrl(String endpoint) => baseUrl + endpoint;

  // Schedule Endpoints
  static const String reservedSlotsEndpoint = '/schedules/all-reserved-slots';
  // static const String createLectureEndpoint = '/schedule/create';
  // static const String updateLectureEndpoint = '/schedule/update';
  // static const String deleteLectureEndpoint = '/schedule/delete';
  static const String availabilitySlotsEndpoint = '/schedules/available-slots';

  // // Get full OTP URLs
  // static String get forgotPasswordUrl => getUrl(forgotPasswordEndpoint);
  // static String get verifyOtpUrl => getUrl(verifyOtpEndpoint);
  // static String get resetPasswordUrl => getUrl(resetPasswordEndpoint);
  // static String get resendOtpUrl => getUrl(resendOtpEndpoint);
}
