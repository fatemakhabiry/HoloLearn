import 'package:flutter/material.dart';
import 'package:provider/provider.dart' ;

import '../routes/app_routes.dart';
import '../constants/constants.dart';
import '../providers/app_state_provider.dart';
import '../providers/lecture_state_provider.dart';
import '../state/processing_notifier.dart';


class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
        // Show splash for 2 seconds
    Future.delayed(const Duration(seconds: 2), () async {
      await _initializeApp(); // restore session state first
      _checkAutoLogin();      // then check login and navigate
    });

  }
Future<void> _checkAutoLogin() async {
  try {
    final appState = Provider.of<AppStateProvider>(context, listen: false);
    await appState.init();

    final success = await appState.tryAutoLogin();

    if (!mounted) return;

    if (success && appState.isLoggedIn) {
      switch (appState.userRole) {
        case 'teacher':
          Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
          break;
        case 'student':
          Navigator.pushReplacementNamed(context, AppRoutes.studentDashboard);
          break;
        default:
          Navigator.pushReplacementNamed(context, AppRoutes.login);
      }
    } else {
      Navigator.pushReplacementNamed(context, AppRoutes.login);
    }
  } catch (_) {
    if (mounted) Navigator.pushReplacementNamed(context, AppRoutes.login);
  }
}
  Future<void> _initializeApp() async {
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final lectureState = Provider.of<LectureStateProvider>(context, listen: false);
      final processingNotifier = Provider.of<ProcessingNotifier>(context, listen: false);

      // Restore lecture state (including ongoingSessionId) from storage
      await lectureState.init();

      // If a session was in progress when the app was killed, resume polling
      if (lectureState.hasOngoingSession) {
        await processingNotifier.resumeIfNeeded(appState);
      }
    } catch (e) {
      // Non-fatal — app can still function without resumed session
      debugPrint('_initializeApp error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
  return Scaffold(
    backgroundColor: AppColors.primaryColor,
    body: Stack(
      children: [
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Logo
              Container(
                width: 300,
                height: 300,
                child: Image(
                image: AssetImage("images/vertical logo-02.png"),
              )
              ),
              const SizedBox(height: AppStyles.spacingS),

              // Tagline
              Text(
                'AI-Powered Holographic learning',
                style: AppStyles.h2.copyWith(color: AppColors.textLight),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),

        // Bottom loading
        Positioned(
          bottom: 60,
          left: 0,
          right: 0,
          child: Column(
            children: [
              const CircularProgressIndicator(
                color: Colors.white,
                strokeWidth: 3,
              ),
              const SizedBox(height: AppStyles.spacingS),
              Text(
                'Loading...',
                style: AppStyles.bodySmall.copyWith(
                  color: AppColors.textLight,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}
}