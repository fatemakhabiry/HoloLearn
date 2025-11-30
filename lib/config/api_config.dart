class ApiConfig {
  // UPDATE THIS WITH YOUR NGROK URL
  static const String baseUrl = 'https://unflinchingly-effortful-deacon.ngrok-free.dev/api/v1';
  
  // Authentication Endpoints
  static const String loginEndpoint = '/auth/login';
  
  // User Endpoints
  static const String userProfileEndpoint = '/users/me';
  static const String updateProfileEndpoint = '/users/me';
  
  // Teacher Endpoints
  static const String teacherProfileEndpoint = '/teachers/profile';
  static const String teacherUploadPhotoEndpoint = '/teachers/upload-photo';
  static const String teacherUploadVoiceEndpoint = '/teachers/upload-voice';
  
  // Storage Keys
  static const String accessTokenKey = 'access_token';
  static const String userIdKey = 'user_id';
  static const String userEmailKey = 'user_email';
  static const String userRoleKey = 'user_role';
  static const String userNameKey = 'user_name';
  
  // Token Settings
  static const Duration tokenExpiry = Duration(minutes: 30);
  
  // API Timeouts
  static const Duration connectionTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  
  // Build full URL
  static String getUrl(String endpoint) => baseUrl + endpoint;
}
