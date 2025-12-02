import 'package:flutter/material.dart';
import 'login_screen.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/widgets/app_bar_widget.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';
import 'package:hololearn/screens/otp_verification_screen.dart';
import 'package:hololearn/utils.dart/app_state.dart';

class OtpExpiredScreen extends StatelessWidget {
  const OtpExpiredScreen({super.key});

  final String bannerTitle = "Reset Link Expired";
  final String bannerMessage =
      "This password reset link has expired or is invalid. Reset links are valid for10 minutes only.";
  final String imagePath = 'images/time_expired_icon.png';
  final Color imageBackgroundColor = const Color(0xFFFFCDD2);
  final String title = 'OTP Expired';
  final String description =
      "For security reasons, password reset links expire after 10 minutes. Please request a new link to continue.";

  @override
  Widget build(BuildContext context) {
    void _backToLogin() {
      // Back to login
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => const LoginPage()),
      );
    }

    void _resendEmail() {
      // TODO: Implement resend email logic
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => OtpVerficationScreen(
            email: AppState.email,
            linkSentTime: DateTime.now(),
          ),
        ),
      );
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
                  const SizedBox(height: AppStyles.spacingL),
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
