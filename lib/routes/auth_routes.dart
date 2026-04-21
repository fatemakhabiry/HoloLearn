import 'package:flutter/material.dart';
import 'app_routes.dart';
import '../screens/screens.dart';

class AuthRoutes {
  static Route<dynamic>? generate(RouteSettings settings) {
    switch (settings.name) {
      case AppRoutes.login:
        return MaterialPageRoute(builder: (_) => const LoginPage());

      case AppRoutes.forgetPassword:
        return MaterialPageRoute(builder: (_) => const ForgetPasswordPage());

      case AppRoutes.resetPassword:
        return MaterialPageRoute(builder: (_) => const ResetPasswordPage());

      case AppRoutes.resetPassSuccess:
        return MaterialPageRoute(builder: (_) => const ResetPassSuccessPage());

      case AppRoutes.changePassword:
        return MaterialPageRoute(builder: (_) => const ChangePasswordScreen());

      case AppRoutes.otpVerification:
        final args = settings.arguments as Map<String, dynamic>;
        return MaterialPageRoute(
          builder: (_) => OtpVerficationScreen(
            email: args['email'],
            linkSentTime: args['linkSentTime'],
          ),
        );

      case AppRoutes.otpExpired:
        return MaterialPageRoute(builder: (_) => const OtpExpiredScreen());

      default:
        return null;
    }
  }
}