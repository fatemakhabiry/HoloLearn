import 'package:flutter/material.dart';
import '../routes/app_routes.dart';
import '../screens/screens.dart';

class TeacherRoutes {
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.teacherDashboard:
        return MaterialPageRoute(
          builder: (_) => const TeacherDashboardScreen(),
        );

      case AppRoutes.teacherLectures:
        return MaterialPageRoute(
          builder: (_) => const TeacherLecturesScreen(),
        );

      case AppRoutes.createNewLecture:
        return MaterialPageRoute(
          builder: (_) => const CreateNewLectureScreen(),
        );

      case AppRoutes.editLecture:
        final args = settings.arguments as Map<String, dynamic>;
        return MaterialPageRoute(
          builder: (_) =>
              EditLectureScreen(scheduleId: args['scheduleId'] as int),
        );

      default:
        return null;
    }
  }
}