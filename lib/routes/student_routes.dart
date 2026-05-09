import 'package:flutter/material.dart';
import 'app_routes.dart';
import '../screens/screens.dart';

class StudentRoutes {
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.studentDashboard:
        return MaterialPageRoute(
          builder: (_) => const StudentDashboardScreen(),
        );
      case AppRoutes.studentQAScreen:
        final args = settings.arguments as Map<String, dynamic>;

        return MaterialPageRoute(
          builder: (_) => StudentQAScreen(session: args["session"]),
        );
      default:
        return null;
    }
  }
}
