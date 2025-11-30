import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/screens/login_screen.dart';
import 'package:hololearn/screens/reset_pass_status_screen.dart';
import 'package:hololearn/widgets/button_widget.dart';
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
  String? email;
  String message = ""; //not required

  @override
  Widget build(BuildContext context) {
    return Scaffold(
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
                    massegeBannerSuccess: '',
                    massegeBannerFail: '',
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
                              //more validation will be added
                              if (value == null || value.isEmpty) {
                                // call api to check email format
                                return 'this email is not registered in our system';
                              }
                              return null;
                            },
                            onSaved: (value) => email = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          // Submit Button
                          CustomButton(
                            text: 'SUBMIT',
                            fullWidth: true,
                            onPressed: () {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                Navigator.pushReplacement(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => ResetPassStatusPage(
                                      email: email!,
                                      linkSentTime: DateTime.now(),
                                    ),
                                  ),
                                );
                              } else {
                                setState(() {
                                  message = "Please fill all fields correctly!";
                                  // here we are not go to any page just show the error message
                                });
                              }
                            },
                          ),
                          const SizedBox(height: AppStyles.spacingM),
                          // Back to login Link
                          Align(
                            alignment: Alignment.center,
                            child: TextButton(
                              onPressed: () {
                                Navigator.pushReplacement(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => const LoginPage(),
                                  ),
                                );
                              },
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                minimumSize: Size.zero,
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                              child: Text(
                                'Back to login?',
                                style: AppStyles.link.copyWith(
                                  color: AppColors.lightBlue,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppStyles.spacingM),
                          // Display message
                          if (message.isNotEmpty) ...[
                            const SizedBox(height: AppStyles.spacingL),
                            MessageDisplay(
                              massegeBannerSuccess: "Login Success",
                              massegeBannerFail: "Login Failed",
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
