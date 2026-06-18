import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';
import 'package:provider/provider.dart';

import '../routes/app_routes.dart';
import '../constants/constants.dart';
import '../providers/app_state_provider.dart';
import '../providers/lecture_state_provider.dart';
import '../services/biometric_service.dart';
import '../state/processing_notifier.dart';
import '../utils/storage_helper.dart';

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
      _startApp();
    });
  }

  Future<void> _startApp() async {
    final bool success = await _checkAutoLogin();

    if (!mounted) return;

    if (success) {
      final appState = Provider.of<AppStateProvider>(context, listen: false);

      if (appState.userRole == 'teacher') {
        await _initializeApp();
        if (!mounted) return;
        Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
      } else {
        Navigator.pushReplacementNamed(context, AppRoutes.studentDashboard);
      }
    } else {
      Navigator.pushReplacementNamed(context, AppRoutes.login);
    }
  }

  Future<bool> _checkAutoLogin() async {
    final appState = Provider.of<AppStateProvider>(context, listen: false);

    await appState.init();

    final shouldAutoLogin = await appState.shouldAutoLogin();

    if (!shouldAutoLogin) {
      return false;
    }

    final biometricEnabled = await StorageHelper.getBiometricEnabled();

    if (biometricEnabled) {
      final available = await BiometricService.isAvailable();

      if (available) {
        final authenticated = await BiometricService.authenticate(
          reason: 'Authenticate to log in to HoloLearn',
        );

        if (!authenticated) {
          return false;
        }
      }
    }

    return await appState.tryAutoLogin();
  }

  Future<void> _initializeApp() async {
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final lectureState = Provider.of<LectureStateProvider>(
        context,
        listen: false,
      );
      final processingNotifier = Provider.of<ProcessingNotifier>(
        context,
        listen: false,
      );

      // Restore lecture state (including ongoingSessionId) from storage
      await lectureState.init();

      // If a session was in progress when the app was killed, resume polling
      if (lectureState.hasOngoingSession) {
        try {
          await processingNotifier
              .resumeIfNeeded(appState)
              .timeout(const Duration(seconds: 3));
        } catch (_) {
          // If resuming fails (e.g. session expired), just continue to dashboard
        }
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
                Lottie.asset('assets/animation/Logo Animation.json'),

                // Tagline
                Text(
                  'AI-Powered Holographic learning',
                  style: AppStyles.h2.copyWith(color: AppColors.gray),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
