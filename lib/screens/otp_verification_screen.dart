import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_fonts.dart';
import 'package:hololearn/screens/otp_expired_screen.dart';
import 'package:hololearn/utils.dart/app_state.dart';
import 'dart:async';
import 'login_screen.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/widgets/app_bar_widget.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';
import 'package:hololearn/widgets/otp_widget.dart';

class OtpVerficationScreen extends StatefulWidget {
  final String email;
  final DateTime linkSentTime;

  const OtpVerficationScreen({
    Key? key,
    required this.email,
    required this.linkSentTime,
  }) : super(key: key);

  @override
  State<OtpVerficationScreen> createState() => _OtpVerficationScreenState();
}

class _OtpVerficationScreenState extends State<OtpVerficationScreen> {
  Timer? _timer;
  DateTime? currentLinkTime;

  final String bannerTitle = "Check Your Email";
  final String bannerMessage =
      "We've sent a Verification code to your email address.";
  final String imagePath = 'images/email_sent_icon.png';
  final Color imageBackgroundColor = Color(0xFFCDF1CD);
  final String title = 'Email Sent!';
  final String subtitle = "We've sent a reset link to:";
  final String description =
      "The code will expire in 10 minutes. Didn't receive the email? Check your spam folder or ";

  @override
  void initState() {
    super.initState();
    currentLinkTime = widget.linkSentTime;
    _checkLinkExpiration();
    _startExpirationTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _checkLinkExpiration() {
    final now = DateTime.now();
    final difference = now.difference(widget.linkSentTime);

    // Link expires after 10 mins (using 1 minute for testing)
    if (difference.inMinutes >= 1) {
      setState(() {
        // TODO: Implement resend email logic
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => const OtpExpiredScreen()),
        );
      });
    }
  }

  void _startExpirationTimer() {
    // Check every minute if link has expired
    _timer = Timer.periodic(Duration(minutes: 1), (timer) {
      _checkLinkExpiration();
    });
  }

  void _backToLogin() {
    // Back to login
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => const LoginPage()),
    );
  }

  void _verifyCode() {
    // TODO: Implement resend email logic
    setState(() {});
  }

  void _resendEmail() {
    // TODO: Implement resend email logic
    setState(() {});
  }

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
                  const SizedBox(height: AppStyles.spacingL),

                  // Show state banner (Check Your Email / Reset Link Expired)
                  MessageDisplay(
                    isSuccess: true,
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
                              backgroundColor: imageBackgroundColor,
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
                            Text(subtitle, style: AppStyles.labelStyle),
                            const SizedBox(height: AppStyles.spacingS),
                            Text(
                              AppState.email,
                              style: AppStyles.link.copyWith(
                                color: AppColors.lightBlue,
                                fontWeight: AppFonts.semiBold,
                              ),
                            ),
                            const SizedBox(height: AppStyles.spacingS),
                            Wrap(
                              alignment: WrapAlignment.center,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                Text(
                                  description,
                                  style: AppStyles.labelStyle,
                                  textAlign: TextAlign.center,
                                ),
                                TextButton(
                                  onPressed: _resendEmail,
                                  style: TextButton.styleFrom(
                                    padding: EdgeInsets.zero,
                                    minimumSize: Size.zero,
                                    tapTargetSize:
                                        MaterialTapTargetSize.shrinkWrap,
                                  ),
                                  child: Text(
                                    'Resend the Email.',
                                    style: AppStyles.labelStyle.copyWith(
                                      color: AppColors.lightBlue,
                                      fontWeight: AppFonts.semiBold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            // OTP Input Fields
                            const SizedBox(height: AppStyles.spacingL),
                            OtpInputWidget(
                              onCompleted: (otp) {
                                print("OTP entered: $otp");
                                // You can store it or instantly verify
                              },
                            ),

                            const SizedBox(height: AppStyles.spacingL),

                            // Action Button
                            CustomButton(
                              text: 'Verify Code',
                              onPressed: _verifyCode,
                              buttonType: ButtonType.primary,
                              fullWidth: true,
                            ),
                            // Back to login link (for expired state)
                            const SizedBox(height: AppStyles.spacingS),
                            CustomButton(
                              text: "Back To Login",
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
