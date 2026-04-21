import 'package:flutter/material.dart';
import '../routes/app_routes.dart';
import '../screens/screens.dart';

class LectureRoutes {
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.lectureSetup:
        return MaterialPageRoute(
          builder: (_) => const LectureSetupScreen(),
        );

      case AppRoutes.insertQueries:
        return MaterialPageRoute(
          builder: (_) => const InsertQueriesScreen(),
        );

      case AppRoutes.lectureprocessing:
        final sessionId = settings.arguments as int;
        return MaterialPageRoute(
          builder: (_) => LectureProcessingScreen(sessionId: sessionId),
        );

      case AppRoutes.lecturepreview:
      final iscontent = settings.arguments as bool;
        return MaterialPageRoute(
          builder: (_) => LecturePreviewScreen(iscontent: iscontent),
        );

      case AppRoutes.refinecontent:
        return MaterialPageRoute(
          builder: (_) => const RefineContentScreen(),
        );

      default:
        return null;
    }
  }
}