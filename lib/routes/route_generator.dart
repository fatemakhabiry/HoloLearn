import 'package:flutter/material.dart';
import 'package:hololearn/screens/otp_expired_screen.dart';
import 'package:hololearn/screens/otp_verification_screen.dart';
import 'package:hololearn/screens/splash_screen.dart';
import 'package:hololearn/screens/teacher_lectures_screen.dart';
import '../routes/app_routes.dart';

import '../screens/change_pass_screen.dart';
import '../screens/create_avatar_screen.dart';
import '../screens/create_new_lecture_screen.dart';
import '../screens/edit_lecture_screen.dart';
import '../screens/login_screen.dart';
import '../screens/forget_pass_screen.dart';
import '../screens/lecture_options_screen.dart';
import '../screens/reset_pass_screen.dart';
import '../screens/reset_pass_success_screen.dart';
import '../screens/student_dashboard_screen.dart';
import '../screens/teacher_dashboard_screen.dart';

class RouteGenerator {
  static Route<dynamic> generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.login:
        return MaterialPageRoute(builder: (_) => const LoginPage());

      case AppRoutes.teacherDashboard:
        return MaterialPageRoute(
          builder: (_) => const TeacherDashboardScreen(),
        );
      case AppRoutes.studentDashboard:
        return MaterialPageRoute(
          builder: (_) => const StudentDashboardScreen(),
        );
      case AppRoutes.forgetPassword:
        return MaterialPageRoute(builder: (_) => const ForgetPasswordPage());

      case AppRoutes.lectureSetup:
        return MaterialPageRoute(builder: (_) => const LectureSetupScreen());

      case AppRoutes.createAvatar:
        return MaterialPageRoute(builder: (_) => const CreateAvatarScreen());

      case AppRoutes.otpVerification:
        final args = settings.arguments as Map<String, dynamic>;
        return MaterialPageRoute(
          builder: (_) => OtpVerficationScreen(
            email: args['email'],
            linkSentTime: args['linkSentTime'],
          ),
        );
      case AppRoutes.resetPassword:
        return MaterialPageRoute(builder: (_) => const ResetPasswordPage());

      case AppRoutes.otpExpired:
        return MaterialPageRoute(builder: (_) => const OtpExpiredScreen());

      case AppRoutes.changePassword:
        return MaterialPageRoute(builder: (_) => const ChangePasswordScreen());

      case AppRoutes.teacherLectures:
        return MaterialPageRoute(builder: (_) => const TeacherLecturesScreen());

      case AppRoutes.resetPassSuccess:
        return MaterialPageRoute(builder: (_) => const ResetPassSuccessPage());

      case AppRoutes.splash:
        return MaterialPageRoute(builder: (_) => const SplashScreen());

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
        return MaterialPageRoute(
          builder: (_) =>
              const Scaffold(body: Center(child: Text('No route found'))),
        );
    }
  }
}
