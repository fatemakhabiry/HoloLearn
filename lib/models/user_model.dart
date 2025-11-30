class User {
  // final int id;
  final String email;
  final String fullName;
  final String role;
  // final bool isActive;
  // final DateTime createdAt;
  // final String? photoUrl;
  // final String? voiceUrl;

  User({
    // required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    // required this.isActive,
    // required this.createdAt,
    // this.photoUrl,
    // this.voiceUrl,
  });

  // Create User from JSON (matches UserBase from backend)
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      // id: json['id'] as int,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: json['role'] as String,
      // isActive: json['is_active'] as bool,
      // createdAt: DateTime.parse(json['created_at'] as String),
      // photoUrl: json['photo_url'] as String?,
      // voiceUrl: json['voice_url'] as String?,
    );
  }

  // Convert User to JSON
  Map<String, dynamic> toJson() {
    return {
      // 'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      // 'is_active': isActive,
      // 'created_at': createdAt.toIso8601String(),
      // if (photoUrl != null) 'photo_url': photoUrl,
      // if (voiceUrl != null) 'voice_url': voiceUrl,
    };
  }

  // Helper methods for role checking
  bool get isStudent => role == 'student';
  bool get isTeacher => role == 'teacher';
  bool get isAdmin => role == 'admin';

  // Copy with method for updating user
  User copyWith({
    // int? id,
    String? email,
    String? fullName,
    String? role,
    // bool? isActive,
    // DateTime? createdAt,
    // String? photoUrl,
    // String? voiceUrl,
  }) {
    return User(
      // id: id ?? this.id,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      // isActive: isActive ?? this.isActive,
      // createdAt: createdAt ?? this.createdAt,
      // photoUrl: photoUrl ?? this.photoUrl,
      // voiceUrl: voiceUrl ?? this.voiceUrl,
    );
  }

  @override
  String toString() {
    // return 'User(id: $id, email: $email, fullName: $fullName, role: $role)';
    return 'User(email: $email, fullName: $fullName, role: $role)';
  }

  // @override
  // bool operator ==(Object other) {
  //   if (identical(this, other)) return true;
  //   return other is User && other.id == id && other.email == email;
  // }

  // @override
  // int get hashCode => id.hashCode ^ email.hashCode;
}
