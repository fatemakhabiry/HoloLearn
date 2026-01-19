import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../screens/login_screen.dart';
import '../screens/otp_verification_screen.dart';
import '../services/password_reset_service.dart';
import '../utils/app_state.dart';
import '../widgets/button_widget.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/text_form_widget.dart';

class ForgetPasswordPage extends StatefulWidget {
  const ForgetPasswordPage({super.key});

  @override
  State<ForgetPasswordPage> createState() => _ForgetPasswordPageState();
}

class _ForgetPasswordPageState extends State<ForgetPasswordPage> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  String? password1;
  String? password2;
  String message = ""; //not required
  bool status = false;
  bool is_loading = false;
  String? error_message = null;

  void _requestotp() async {
    setState(() {
      is_loading = true;
      message = "";
    });
    try {
      await PasswordResetService.requestOTP(AppState.email);
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => OtpVerficationScreen(
            email: AppState.email,
            linkSentTime: DateTime.now(),
          ),
        ),
      ); // Added closing parenthesis and semicolon
    } on ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      error_message = e.toString().replaceFirst('Exception: ',  '');
      status = false;
    } finally {
      if (error_message != null) {
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
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: "Forget Password", showBackButton: false),
      backgroundColor: AppColors.lightBackground,
      body: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  MessageDisplay(
                    massegeBanner: '',
                    message:
                        'To reset your password, please fill out the form below. We will send you a password to your email address within a few minutes.',
                    isInfo: true,
                    showIcon: false,
                  ),
                  const SizedBox(
                    height: AppStyles.spacingM,
                  ), // for space between logo and title
                  // Login Form Card
                  Container(
                    padding: const EdgeInsets.all(AppStyles.spacingL),
                    decoration: BoxDecoration(
                      color: AppColors.white,
                      borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                      boxShadow: AppStyles.cardShadow,
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          CustomTextFormField(
                            hintText: '',
                            label: "Email Address",
                            keyboardType: TextInputType.emailAddress,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Email is required';
                              }
                              if (!value.contains('@')) {
                                return 'Enter a valid email';
                              }
                              return null;
                            },
                            onSaved: (value) => AppState.email = value!,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          // Submit Button
                          CustomButton(
                            text: 'Submit',
                            fullWidth: true,
                            isLoading: is_loading,
                            onPressed: () {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                status = true;
                                _requestotp();
                              } else {
                                setState(() {
                                  status = false;
                                  message = "Please fill all fields correctly!";
                                  // here we are not go to any page just show the error message
                                });
                              }
                            },
                          ),
                          // Back to login Link
                          const SizedBox(height: AppStyles.spacingS),
                          CustomButton(
                            text: "Back To Login",
                            onPressed: () {
                              Navigator.pushReplacement(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => LoginPage(),
                                ),
                              );
                            },
                            buttonType: ButtonType.secondary,
                            fullWidth: true,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: AppStyles.spacingM),
                  // Display message
                  if (message.isNotEmpty) ...[
                    const SizedBox(height: AppStyles.spacingL),
                    MessageDisplay(
                      isSuccess: status,
                      massegeBanner: status
                          ? "Sent Successfuly"
                          : "Failed to Send!",
                      message: message,
                      onDismiss: () => setState(() => message = ''),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
