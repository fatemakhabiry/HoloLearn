import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/constants.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../providers/app_state_provider.dart';
import '../../services/password_reset_service.dart';

class OtpExpiredScreen extends StatelessWidget {
  const OtpExpiredScreen({super.key});

  final String bannerTitle = "Reset Link Expired";
  final String bannerMessage =
      "This password reset link has expired or is invalid. Reset links are valid for 10 minutes only.";
  final String imagePath = 'assets/images/time_expired_icon.png';
  final Color imageBackgroundColor = const Color(0xFFFFCDD2);
  final String title = 'OTP Expired';
  final String description =
      "For security reasons, password reset links expire after 10 minutes or you've entered incorrect OTP. Please request a new link to continue.";

  @override
  Widget build(BuildContext context) {
    void _backToLogin() {
      Navigator.pushReplacementNamed(context, AppRoutes.login);
    }

    void _resendEmail() async {
      final email = Provider.of<AppStateProvider>(context, listen: false).email;

      // Validate email is not empty
      if (email.isEmpty) {
        CustomErrorHandler.show(
          context,
          message: 'Email not found. Please try again.',
          type: ErrorType.fail,
        );

        Navigator.pushReplacementNamed(context, AppRoutes.forgetPassword);
        return;
      }

      try {
        await PasswordResetService.resendOTP(email);

        Navigator.pushReplacementNamed(
          context,
          AppRoutes.otpVerification,
          arguments: {'email': email, 'linkSentTime': DateTime.now()},
        );
      } catch (e) {
        CustomErrorHandler.show(
          context,
          message:
              'Failed to resend OTP: ${e.toString().replaceFirst('Exception: ', '')}',
          type: ErrorType.fail,
        );
      }
    }

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
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
                      color:context.cardColor,
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
