import 'package:flutter/material.dart';
import 'package:provider/provider.dart' ;

import '../routes/app_routes.dart';
import '../constants/constants.dart';
import '../state/providers/app_state_provider.dart';


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
    Future.delayed(const Duration(seconds: 2), () {
      _checkAutoLogin();
      _initializeApp();
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
// 7agat alsessions

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
                width: 120,
                height: 120,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.school,
                  size: 60,
                  color: AppColors.primaryColor,
                ),
              ),
              const SizedBox(height: AppStyles.spacingM),

              // App Name
              Text(
                'HoloLearn',
                style: AppStyles.logo.copyWith(color: AppColors.white),
              ),
              const SizedBox(height: AppStyles.spacingS),

              // Tagline
              Text(
                'Holographic Learning Platform',
                style: AppStyles.h1.copyWith(color: AppColors.textLight),
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