import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/screens/login_screen.dart';
import 'package:hololearn/screens/otp_verification_screen.dart';
import 'package:hololearn/utils.dart/app_state.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/app_bar_widget.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';
import 'package:hololearn/widgets/text_form_widget.dart';

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
                            onPressed: () {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                status = true;
                                Navigator.pushReplacement(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => OtpVerficationScreen(
                                      email: AppState.email!,
                                      linkSentTime: DateTime.now(),
                                    ),
                                  ),
                                );
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
                          const SizedBox(height: AppStyles.spacingM),
                          // Display message
                          if (message.isNotEmpty) ...[
                            const SizedBox(height: AppStyles.spacingL),
                            MessageDisplay(
                              isSuccess: status,
                              massegeBanner: status
                                  ? "Login Success"
                                  : "Login Failed",
                              message: message,
                              onDismiss: () => setState(() => message = ''),
                            ),
                          ],
                        ],
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
