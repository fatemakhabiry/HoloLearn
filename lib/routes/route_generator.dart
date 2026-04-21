import 'package:flutter/material.dart';
import '../screens/screens.dart';
import 'routes.dart';

class RouteGenerator {
  static Route<dynamic> generateRoute(RouteSettings settings) {
    final routes = [
      AuthRoutes.generate,
      TeacherRoutes.generate,
      StudentRoutes.generate,
      LectureRoutes.generate,
    ];

    for (var route in routes) {
      final result = route(settings);
      if (result != null) return result;
    }

    return MaterialPageRoute(
      builder: (_) => const SplashScreen(), // ✅ correct
    );
  }
}