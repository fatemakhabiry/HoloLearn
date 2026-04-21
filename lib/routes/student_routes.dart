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

      default:
        return null;
    }
  }
}