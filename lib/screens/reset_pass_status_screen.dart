import 'package:flutter/material.dart';
import 'dart:async';
import 'login_screen.dart';

import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/constants/app_fonts.dart';

import 'package:hololearn/widgets/app_bar_widget.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';

enum ResetPasswordState { emailSent, linkExpired }

// State configuration class
class StateConfig {
  final String bannerTitle;
  final String bannerMessage;
  final String imagePath;
  final Color imageBackgroundColor;
  final String title;
  final String subtitle;
  final String? emailPrefix;
  final String description;
  final String buttonText;
  final ButtonType buttonType;
  final VoidCallback buttonFunction;
  final bool showResendLink;

  StateConfig({
    required this.bannerTitle,
    required this.bannerMessage,
    required this.imagePath,
    required this.imageBackgroundColor,
    required this.title,
    required this.subtitle,
    this.emailPrefix,
    required this.description,
    required this.buttonText,
    required this.buttonType,
    required this.buttonFunction,
    this.showResendLink = false,
  });
}

class ResetPassStatusPage extends StatefulWidget {
  final String email;
  final DateTime linkSentTime;

  const ResetPassStatusPage({
    Key? key,
    required this.email,
    required this.linkSentTime,
  }) : super(key: key);

  @override
  State<ResetPassStatusPage> createState() => _ResetPassStatusPageState();
}

class _ResetPassStatusPageState extends State<ResetPassStatusPage> {
  Timer? _timer;
  DateTime? currentLinkTime;
  ResetPasswordState currentState = ResetPasswordState.emailSent;

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

    // Link expires after 1 hour (using 1 minute for testing)
    if (difference.inMinutes >= 1) {
      setState(() {
        currentState = ResetPasswordState.linkExpired;
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

  void _resendEmail() {
    // TODO: Implement resend email logic
    setState(() {
      currentLinkTime = DateTime.now();
      currentState = ResetPasswordState.emailSent;
    });
  }

  // Map of state configurations
  late final Map<ResetPasswordState, StateConfig> stateConfigs = {
    ResetPasswordState.emailSent: StateConfig(
      bannerTitle: "Check Your Email",
      bannerMessage:
          "Success! We've sent a password reset link to your email address.",
      imagePath: 'images/email_sent_icon.png',
      imageBackgroundColor: Color(0xFFCDF1CD),
      title: 'Email Sent!',
      subtitle: "We've sent a reset link to:",
      emailPrefix: widget.email,
      description:
          "The link will expire in 1 hour. Didn't receive the email? Check your spam folder or ",
      buttonText: "BACK TO LOGIN",
      buttonType: ButtonType.outlined,
      buttonFunction: _backToLogin,
      showResendLink: true,
    ),
    ResetPasswordState.linkExpired: StateConfig(
      bannerTitle: "Reset Link Expired",
      bannerMessage:
          "This password reset link has expired or is invalid. Reset links are valid for 1 hour only.",
      imagePath: 'images/time_expired_icon.png',
      imageBackgroundColor: Color(0xFFFFCDD2),
      title: 'Link Expired',
      subtitle: '',
      emailPrefix: null,
      description:
          "For security reasons, password reset links expire after 1 hour. Please request a new link to continue.",
      buttonText: "REQUEST NEW LINK",
      buttonType: ButtonType.primary,
      buttonFunction: _resendEmail,
      showResendLink: false,
    ),
  };

  @override
  Widget build(BuildContext context) {
    final config = stateConfigs[currentState]!;

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
                      massegeBannerSuccess: config.bannerTitle,
                      massegeBannerFail: config.bannerTitle,
                      message: config.bannerMessage,
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
                              backgroundColor: config.imageBackgroundColor,
                              child: Image.asset(
                                config.imagePath,
                                width: 80,
                                height: 80,
                              ),
                            ),
                            const SizedBox(height: AppStyles.spacingS),
                            // Title
                            Text(config.title, style: AppStyles.h2),

                            const SizedBox(height: AppStyles.spacingS),

                            // Subtitle (if exists)
                            if (config.subtitle.isNotEmpty) ...[
                              Text(
                                config.subtitle,
                                style: AppStyles.labelStyle,
                              ),
                              const SizedBox(height: AppStyles.spacingS),
                            ],
                            if (config.emailPrefix != null) ...[
                              Text(
                                config.emailPrefix!,
                                style: AppStyles.link.copyWith(
                                  color: AppColors.lightBlue,
                                  fontWeight: AppFonts.semiBold,
                                ),
                              ),
                              const SizedBox(height: AppStyles.spacingS),
                            ],
                            // Description with optional resend link
                            if (config.showResendLink)
                              Wrap(
                                alignment: WrapAlignment.center,
                                crossAxisAlignment: WrapCrossAlignment.center,
                                children: [
                                  Text(
                                    config.description,
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
                              )
                            else
                              Text(
                                config.description,
                                style: AppStyles.labelStyle,
                                textAlign: TextAlign.center,
                              ),

                            const SizedBox(height: AppStyles.spacingL),

                            // Action Button
                            CustomButton(
                              text: config.buttonText,
                              onPressed: config.buttonFunction,
                              buttonType: config.buttonType,
                              fullWidth: true,
                            ),

                            // Back to login link (for expired state)
                            if (currentState ==
                                ResetPasswordState.linkExpired) ...[
                              const SizedBox(height: AppStyles.spacingS),
                              CustomButton(
                                text: "BACK TO LOGIN",
                                onPressed: _backToLogin,
                                buttonType: ButtonType.secondary,
                                fullWidth: true,
                              ),
                            ],
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
