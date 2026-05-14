import 'dart:io';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import '../../constants/constants.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../providers/app_state_provider.dart';
import '../../services/password_reset_service.dart';

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
  String? otp;
  bool is_loading = false;
  String? error_message = null;
  final String bannerTitle = "Check Your Email";
  final String bannerMessage =
      "We've sent a Verification code to your email address.";
  final String imagePath = 'assets/images/email_sent_icon.png';
  final Color imageBackgroundColor = Color(0xFFCDF1CD);
  final String title = 'Email Sent!';
  final String subtitle = "We've sent a reset link to:";
  final String description =
      "The code will expire in 10 minutes. Didn't receive the email? Check your spam folder or ";

  void _backToLogin() {
    // Back to login
    // Navigator.pushReplacement(
    //   context,
    //   MaterialPageRoute(builder: (context) => const LoginPage()),
    // );
    Navigator.pushReplacementNamed(context, AppRoutes.login);
  }

  void _verifyCode() async {
    // 1️⃣ Start loading
    setState(() {
      is_loading = true;
    });

    try {
      // 2️⃣ Do async work OUTSIDE setState
      await PasswordResetService.verifyOTP(widget.email, otp!);

      // Set in provider
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await appState.setEmail(widget.email);
      appState.setOtp(otp!);

      // 3️⃣ Navigate (no setState needed)
      if (mounted) {
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(builder: (context) => ResetPasswordPage()),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.resetPassword);
      }
    } catch (e) {
      // Set email in provider even on failure so OtpExpiredScreen can access it
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await appState.setEmail(widget.email);

      if (mounted) {
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(builder: (context) => OtpExpiredScreen()),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.otpExpired);
      }
    } finally {
      // 4️⃣ Stop loading
      if (mounted) {
        setState(() {
          is_loading = false;
        });
      }
    }
  }

  void _resendEmail() async {
    // 1️⃣ Start loading
    setState(() {
      is_loading = true;
    });
    try {
      // 2️⃣ Async work outside setState
      await PasswordResetService.resendOTP(widget.email);

      // 3️⃣ Navigate
      if (mounted) {
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(
        //     builder: (context) => OtpVerficationScreen(
        //       email: widget.email,
        //       linkSentTime: DateTime.now(),
        //     ),
        //   ),
        // );
        Navigator.pushReplacementNamed(
          context,
          AppRoutes.otpVerification,
          arguments: {'email': widget.email, 'linkSentTime': DateTime.now()},
        );
      }
    } on ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      error_message = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (error_message != null) {
        if (error_message == 'Invalid or expired OTP') {
          // Ensure email is set in provider before navigating to expired screen
          final appState = Provider.of<AppStateProvider>(
            context,
            listen: false,
          );
          await appState.setEmail(widget.email);

          // Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(builder: (context) => OtpExpiredScreen()),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.otpExpired);
        }
        CustomErrorHandler.show(
          context,
          message: error_message!,
          type: ErrorType.fail,
        );
        error_message = null;
      }
      if (mounted) {
        setState(() {
          is_loading = false;
        });
      }
    }
  }

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
    if (difference.inMinutes >= 10) {
      setState(() {
        // Navigator.pushReplacement(
        //   context,
        //   MaterialPageRoute(builder: (context) => const OtpExpiredScreen()),
        // );
        Navigator.pushReplacementNamed(context, AppRoutes.otpExpired);
      });
    }
  }

  void _startExpirationTimer() {
    // Check every minute if link has expired
    _timer = Timer.periodic(Duration(minutes: 1), (timer) {
      _checkLinkExpiration();
    });
  }

  @override
  Widget build(BuildContext context) {
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
                  // const SizedBox(height: AppStyles.spacingM),

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
                      color:Theme.of(context).scaffoldBackgroundColor,
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
                              widget.email,
                              style: AppStyles.link.copyWith(
                                color:AppColors.primaryColor ,
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
                                // resend link
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
                                      color: AppColors.primaryColor,
                                      fontWeight: AppFonts.semiBold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            // OTP Input Fields
                            const SizedBox(height: AppStyles.spacingL),
                            OtpInputWidget(
                              onCompleted: (value) {
                                otp = value;
                                print("OTP entered: ${otp} ");
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
                              isLoading: is_loading,
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
