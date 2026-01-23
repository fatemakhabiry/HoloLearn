/// Model for course detail information
class CourseDetail {
  final String code;
  final String? name;
  final String? description;
  final String? instructor;
  final int? credits;
  final String? department;

  CourseDetail({
    required this.code,
    this.name,
    this.description,
    this.instructor,
    this.credits,
    this.department,
  });

  factory CourseDetail.fromJson(Map<String, dynamic> json) {
    return CourseDetail(
      code: json['code'] ?? json['course_code'] ?? '',
      name: json['name'] ?? json['course_name'],
      description: json['description'],
      instructor: json['instructor'],
      credits: json['credits'],
      department: json['department'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'code': code,
      'name': name,
      'description': description,
      'instructor': instructor,
      'credits': credits,
      'department': department,
    };
  }
}