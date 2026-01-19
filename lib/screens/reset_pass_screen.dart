import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../screens/login_screen.dart';
import '../screens/reset_pass_success_screen.dart';
import '../widgets/button_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/app_bar_widget.dart';
import '../services/password_reset_service.dart';
import '../utils/app_state.dart';

class ResetPasswordPage extends StatefulWidget {
  const ResetPasswordPage({super.key});

  @override
  State<ResetPasswordPage> createState() => _ResetPasswordPageState();
}

class _ResetPasswordPageState extends State<ResetPasswordPage> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  // String? password1;
  final _newPasswordController = TextEditingController();
  String? password2;
  String message = ""; //not required
  bool _obscureText1 = true;
  bool _obscureText2 = true;
  bool is_loading = false;
  bool status = false;
  @override
  void dispose() {
    _newPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: "Reset Password", showBackButton: false),
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
                          // New Password textfield
                          CustomTextFormField(
                            controller: _newPasswordController,
                            suffixIcon: IconsButton(
                              size: 24,
                              iconColor: Colors.grey,
                              backgroundColor: Colors.transparent,
                              icon: _obscureText1
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                              onPressed: () {
                                setState(() => _obscureText1 = !_obscureText1);
                              },
                            ),
                            hintText: ' ',
                            label: "New Password",
                            keyboardType: TextInputType.emailAddress,
                            obscureText: _obscureText1,
                            validator: (value) {
                              if (value == null ||
                                  value.isEmpty ||
                                  value.length < 8) {
                                return 'Password must be at least 8 characters';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          // Confirm password textfield
                          CustomTextFormField(
                            suffixIcon: IconsButton(
                              size: 24,
                              iconColor: Colors.grey,
                              backgroundColor: Colors.transparent,
                              icon: _obscureText2
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                              onPressed: () {
                                setState(() => _obscureText2 = !_obscureText2);
                              },
                            ),
                            hintText: ' ',
                            label: "Confirm Password",
                            obscureText: _obscureText2,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please confirm your password';
                              }
                              if (value != _newPasswordController.text) {
                                return 'Passwords do not match';
                              }
                              return null;
                            },
                            onSaved: (value) => password2 = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          // Reset Button
                          CustomButton(
                            text: 'Reset Password',
                            fullWidth: true,
                            isLoading: is_loading,
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                status = true;
                                message = "";

                                // 1️⃣ Start loading
                                setState(() {
                                  is_loading = true;
                                });

                                try {
                                  // 2️⃣ Do async work OUTSIDE setState
                                  var data =
                                      await PasswordResetService.resetPassword(
                                        email: AppState.email,
                                        otpCode: AppState.otp,
                                        newPassword: password2!,
                                      );

                                  print("Password set successfully");

                                  // 3️⃣ Navigate (no setState needed)
                                  if (mounted) {
                                    Navigator.pushReplacement(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) =>
                                            ResetPassSuccessPage(),
                                      ),
                                    );
                                  }
                                } catch (e) {
                                  // 4️⃣ Update UI for error
                                  setState(() {
                                    status = false;
                                    message = 'Failed to set new password $e';
                                  });
                                } finally {
                                  // 5️⃣ Stop loading
                                  if (mounted) {
                                    setState(() {
                                      is_loading = false;
                                    });
                                  }
                                }
                              } else {
                                setState(() {
                                  status = false;
                                  message = "Please fill all fields correctly!";
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
                          const SizedBox(height: AppStyles.spacingS),
                          // Display message
                          if (message.isNotEmpty) ...[
                            const SizedBox(height: AppStyles.spacingL),
                            MessageDisplay(
                              isSuccess: status,
                              massegeBanner: status ? "L" : "Error",
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
