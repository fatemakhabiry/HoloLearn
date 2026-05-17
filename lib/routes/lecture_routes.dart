import 'package:flutter/material.dart';
import '../models/schedule_models.dart';
import '../routes/app_routes.dart';
import '../screens/screens.dart';

class LectureRoutes {
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.lectureSetup:
        return MaterialPageRoute(builder: (_) => const LectureSetupScreen());

      case AppRoutes.insertQueries:
        return MaterialPageRoute(builder: (_) => const InsertQueriesScreen());

      case AppRoutes.lectureprocessing:
        final args = settings.arguments as Map<String, dynamic>;
        return MaterialPageRoute(
          builder: (_) => LectureProcessingScreen(
            sessionId: args['sessionId'] as int,
            lectureType: args['lectureType'] as String? ?? 'generated',
          ),
        );

      case AppRoutes.lecturepreview:
        final iscontent = settings.arguments as bool;
        return MaterialPageRoute(
          builder: (_) => LecturePreviewScreen(isContent: iscontent),
        );

      case AppRoutes.refinecontent:
        return MaterialPageRoute(builder: (_) => const RefineContentScreen());
      case AppRoutes.lectureContent:
        final lecture = settings.arguments as ScheduleSlot;
        return MaterialPageRoute(
          builder: (_) => LectureContentScreen(lecture: lecture),
        );
      case AppRoutes.researchAgent:
        return MaterialPageRoute(
          builder: (_) => const ResearchAgentScreen(),
        );
      default:
        return null;
    }
  }
}
