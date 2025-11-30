import 'package:flutter/material.dart';
import 'login_screen.dart';

import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';

import 'package:hololearn/widgets/app_bar_widget.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';

class ResetPassSuccessPage extends StatefulWidget {
  const ResetPassSuccessPage({super.key});
  @override
  State<ResetPassSuccessPage> createState() => _ResetPassSuccessPage();
}

class _ResetPassSuccessPage extends State<ResetPassSuccessPage> {
  String message =
      '''Your password has been Successfully reset. You can now log in with your new password.''';
  @override
  Widget build(BuildContext context) {
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
                  if (message.isNotEmpty) ...[
                    const SizedBox(height: AppStyles.spacingL),
                    MessageDisplay(
                      massegeBannerSuccess: "Password Reset Successful!",
                      massegeBannerFail: ' ',
                      message: message,
                      onDismiss: () => setState(() => message = ''),
                    ),
                    SizedBox(height: AppStyles.spacingM),
                  ],
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
                            CircleAvatar(
                              radius: 60,
                              backgroundColor: Color(0xFFCDF1CD),
                              child: Image.asset(
                                'images/check_icon.png',
                                width: 80,
                                height: 80,
                              ),
                            ),
                            const SizedBox(height: AppStyles.spacingS),

                            const Text('All Set!', style: AppStyles.h2),

                            const SizedBox(height: AppStyles.spacingS),
                            Text(
                              "Your password has been updated. For security, you'll need to log in again with your new password.",
                              style: AppStyles.labelStyle,
                              textAlign: TextAlign.center,
                            ),

                            const SizedBox(height: AppStyles.spacingL),

                            CustomButton(
                              text: "GO TO LOGIN",
                              onPressed: () {
                                //back to login
                                Navigator.pushReplacement(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => const LoginPage(),
                                  )); 
                              },
                              buttonType: ButtonType.primary,
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
