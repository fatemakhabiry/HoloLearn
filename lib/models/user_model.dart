class User {
  final String email;
  final String fullName;
  final String role;
  final bool isFirstTimeLogin;
  final String? photoUrl;
  final String? voiceUrl;

  User({
    required this.email,
    required this.fullName,
    required this.role,
    this.isFirstTimeLogin = false,
    this.photoUrl,
    this.voiceUrl,
  });

  // Create User from JSON (matches backend response)
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: json['role'] as String,
      isFirstTimeLogin: json['FirstTimeLogin'] ?? false,
      photoUrl: json['photo_url'] as String?,
      voiceUrl: json['voice_url'] as String?,
    );
  }

  // Convert User to JSON
  Map<String, dynamic> toJson() {
    return {
      'email': email,
      'full_name': fullName,
      'role': role,
      'FirstTimeLogin': isFirstTimeLogin,
      if (photoUrl != null) 'photo_url': photoUrl,
      if (voiceUrl != null) 'voice_url': voiceUrl,
    };
  }

  // Helper methods for role checking
  bool get isStudent => role == 'student';
  bool get isTeacher => role == 'teacher';

  // Helper to check if profile is complete
  bool get hasPhoto => photoUrl != null && photoUrl!.isNotEmpty;
  bool get hasVoice => voiceUrl != null && voiceUrl!.isNotEmpty;
  bool get isProfileComplete => hasPhoto && hasVoice;

  // Copy with method for updating user
  User copyWith({
    String? email,
    String? fullName,
    String? role,
    bool? isFirstTimeLogin,
    String? photoUrl,
    String? voiceUrl,
  }) {
    return User(
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      isFirstTimeLogin: isFirstTimeLogin ?? this.isFirstTimeLogin,
      photoUrl: photoUrl ?? this.photoUrl,
      voiceUrl: voiceUrl ?? this.voiceUrl,
    );
  }

  @override
  String toString() {
    return 'User(email: $email, fullName: $fullName, role: $role, isFirstTimeLogin: $isFirstTimeLogin)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is User && other.email == email;
  }

  @override
  int get hashCode => email.hashCode;
}