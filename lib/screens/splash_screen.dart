import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'package:provider/provider.dart';
import '../state/providers/app_state_provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import 'login_screen.dart';
import 'teacher_dashboard_screen.dart';
import 'student_dashboard_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // Show splash for 2 seconds
    await Future.delayed(const Duration(seconds: 2));

    if (!mounted) return;

    try {
      // Initialize app state from storage
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await appState.init();

      // Check if should auto-login
      final shouldAutoLogin = await appState.shouldAutoLogin();

      if (!mounted) return;

      if (shouldAutoLogin && appState.isLoggedIn) {
        // User has valid session and Remember Me checked
        print('✅ Auto-login successful');
        print('👤 Role: ${appState.userRole}');

        final role = appState.userRole;

        if (role == 'teacher') {
          // Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(
          //     builder: (context) => const TeacherDashboardScreen(),
          //   ),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
        } else if (role == 'student') {
          // Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(
          //     builder: (context) => const StudentDashboardScreen(),
          //   ),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.studentDashboard);
        } else {
          // Unknown role, go to login
          print('⚠️ Unknown role: $role');
          // Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(builder: (context) => const LoginPage()),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.login);
        }
      } else {
        // Not logged in or Remember Me not checked
        print('ℹ️ No saved login found, going to login screen');
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(builder: (context) => const LoginPage()),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.login);
      }
    } catch (e) {
      print('❌ Error during splash: $e');
      if (mounted) {
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(
        //     builder: (context) => const LoginPage(),
        //   ),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.login);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBlue,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Logo Container
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.2),
                    blurRadius: 20,
                    offset: const Offset(0, 10),
                  ),
                ],
              ),
              child: const Icon(
                Icons.school,
                size: 60,
                color: AppColors.lightBlue,
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
            ),
            const SizedBox(height: AppStyles.spacingL),

            // Loading Indicator
            const CircularProgressIndicator(
              color: Colors.white,
              strokeWidth: 3,
            ),
            const SizedBox(height: AppStyles.spacingS),

            Text(
              'Loading...',
              style: AppStyles.bodySmall.copyWith(color: AppColors.textLight),
            ),
          ],
        ),
      ),
    );
  }
}
