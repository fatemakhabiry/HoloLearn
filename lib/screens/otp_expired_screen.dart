import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'package:provider/provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../state/providers/app_state_provider.dart';
import '../services/password_reset_service.dart';

class OtpExpiredScreen extends StatelessWidget {
  const OtpExpiredScreen({super.key});

  final String bannerTitle = "Reset Link Expired";
  final String bannerMessage =
      "This password reset link has expired or is invalid. Reset links are valid for 10 minutes only.";
  final String imagePath = 'images/time_expired_icon.png';
  final Color imageBackgroundColor = const Color(0xFFFFCDD2);
  final String title = 'OTP Expired';
  final String description =
      "For security reasons, password reset links expire after 10 minutes or you've entered incorrect OTP. Please request a new link to continue.";

  @override
  Widget build(BuildContext context) {
    void _backToLogin() {
      // Back to login
      // Navigator.pushReplacement(
      //   context,
      //   MaterialPageRoute(builder: (context) => const LoginPage()),
      // );
      Navigator.pushReplacementNamed(context, AppRoutes.login);
    }

    void _resendEmail() async {
      final email = Provider.of<AppStateProvider>(context, listen: false).email;

      // Validate email is not empty
      if (email.isEmpty) {
        // Show error and navigate back to forget password
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Email not found. Please try again.'),
            backgroundColor: Colors.red,
          ),
        );
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(builder: (context) => const ForgetPasswordPage()),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.forgetPassword);
        return;
      }

      try {
        await PasswordResetService.resendOTP(email);
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(
        //     builder: (context) => OtpVerficationScreen(
        //       email: email,
        //       linkSentTime: DateTime.now(),
        //     ),
        //   ),
        // );
        Navigator.pushReplacementNamed(
          context,
          AppRoutes.otpVerification,
          arguments: {'email': email, 'linkSentTime': DateTime.now()},
        );
      } catch (e) {
        // Handle error - could show a snackbar or navigate to error screen
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Failed to resend OTP: ${e.toString().replaceFirst('Exception: ', '')}',
            ),
            backgroundColor: Colors.red,
          ),
        );
      }
    }

    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(title: "Reset Password", showBackButton: false),
      body: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // const SizedBox(height: AppStyles.spacingL),
                  // Show state banner (Reset Link Expired)
                  MessageDisplay(
                    isSuccess: false,
                    massegeBanner: bannerTitle,
                    message: bannerMessage,
                  ),
                  const SizedBox(height: AppStyles.spacingM),
                  // Main Content Card
                  Container(
                    padding: const EdgeInsets.all(AppStyles.spacingL),
                    decoration: BoxDecoration(
                      color: AppColors.white,
                      borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                      boxShadow: AppStyles.cardShadow,
                    ),
                    child: Center(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(AppStyles.spacingM),
                        child: Column(
                          children: [
                            //Image
                            CircleAvatar(
                              radius: 60,
                              backgroundColor: Color(0xFFFFCDD2),
                              child: Image.asset(
                                imagePath,
                                width: 80,
                                height: 80,
                              ),
                            ),
                            const SizedBox(height: AppStyles.spacingS),
                            // Title
                            Text(title, style: AppStyles.h2),

                            const SizedBox(height: AppStyles.spacingS),

                            Text(
                              description,
                              style: AppStyles.labelStyle,
                              textAlign: TextAlign.center,
                            ),

                            const SizedBox(height: AppStyles.spacingL),

                            // Request new link Button
                            CustomButton(
                              text: "Request new link",
                              onPressed: _resendEmail,
                              buttonType: ButtonType.primary,
                              fullWidth: true,
                            ),
                            const SizedBox(height: AppStyles.spacingS),
                            // back to login Button
                            CustomButton(
                              text: "Back to Login",
                              onPressed: _backToLogin,
                              buttonType: ButtonType.secondary,
                              fullWidth: true,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
