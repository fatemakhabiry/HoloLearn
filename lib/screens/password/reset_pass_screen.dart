import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart';
import 'package:provider/provider.dart';

import '../../constants/constants.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../providers/app_state_provider.dart';
import '../../services/password_reset_service.dart';

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
  bool isloading = false;
  bool status = false;
  String? error_message = null;
  @override
  void dispose() {
    _newPasswordController.dispose();
    super.dispose();
  }

  void _backToLogin() {
    // Navigator.pushReplacement(
    //   context,
    //   MaterialPageRoute(builder: (context) => LoginPage()),
    // );
    Navigator.pushReplacementNamed(context, AppRoutes.login);
  }

  Future<void> _handleResetPassword() async {
    status = true;
    message = "";
    // 1️⃣ Start loading
    setState(() {
      isloading = true;
      message = '';
    });
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      // 2️⃣ Do async work OUTSIDE setState
      await PasswordResetService.resetPassword(
        email: appState.email,
        otpCode: appState.otp,
        newPassword: password2!,
      );

      // 3️⃣ Navigate (no setState needed)
      if (mounted) {
        setState(() {
          isloading = false;
          message = '';
        });
        Navigator.pushReplacementNamed(context, AppRoutes.resetPassSuccess);
      }
    } on ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      e.toString().replaceFirst('Exception: ', '');
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
          isloading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: "Reset Password", showBackButton: false),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: LoadingOverlay(
        isLoading: isloading,
        child: Center(
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
                        color: Theme.of(context).cardColor,
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
                                  setState(
                                    () => _obscureText1 = !_obscureText1,
                                  );
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
                                  setState(
                                    () => _obscureText2 = !_obscureText2,
                                  );
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
                              isLoading: isloading,
                              onPressed: () async {
                                if (_formKey.currentState!.validate()) {
                                  _formKey.currentState!.save();
                                  await _handleResetPassword();
                                } else {
                                  setState(() {
                                    status = false;
                                    message =
                                        "Please fill all fields correctly!";
                                  });
                                }
                              },
                            ),
                            // Back to login Link
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
          ),
        ),
      ),
    );
  }
}
