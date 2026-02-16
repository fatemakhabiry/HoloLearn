import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/button_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../services/password_reset_service.dart';
import '../state/providers/app_state_provider.dart';

class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  // String? password1;
  final _newPasswordController = TextEditingController();
  String? newPassword;
  String? oldPassword;
  String message = ""; //not required
  bool _obscureText1 = true;
  bool _obscureText2 = true;
  bool _obscureText3 = true;
  bool is_loading = false;
  bool status = false;
  String? error_message = null;
  @override
  void dispose() {
    _newPasswordController.dispose();
    super.dispose();
  }

  Future<void> _handleChangePassword() async {
    // 1️⃣ Start loading
    setState(() {
      is_loading = true;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await PasswordResetService.changePassword(
        email: appState.email,
        oldPassword: oldPassword!,
        newPassword: newPassword!,
      );

      // Show success message
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Password changed successfully',
          type: ErrorType.success,
        );

        // Wait 3 seconds
        await Future.delayed(const Duration(seconds: 3));
        if (appState.userRole == 'teacher') {
          // Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(builder: (context) => TeacherDashboardScreen()),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
        } else {
          //  Navigator.pushReplacement(
          //   context,
          //   MaterialPageRoute(builder: (context) => StudentDashboardScreen()),
          // );
          Navigator.pushReplacementNamed(context, AppRoutes.studentDashboard);
        }
      }
    } on ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      error_message = e.toString().replaceAll('Exception: ', '');
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
      appBar: CustomAppBar(title: "Change Password", showBackButton: true),
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
                            suffixIcon: IconsButton(
                              size: 24,
                              iconColor: Colors.grey,
                              backgroundColor: Colors.transparent,
                              icon: _obscureText3
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                              onPressed: () {
                                setState(() => _obscureText3 = !_obscureText3);
                              },
                            ),
                            hintText: ' ',
                            label: "Old Password",
                            keyboardType: TextInputType.emailAddress,
                            obscureText: _obscureText3,
                            validator: (value) {
                              if (value == null ||
                                  value.isEmpty ||
                                  value.length < 8) {
                                return 'Password must be at least 8 characters';
                              }
                              return null;
                            },
                            onSaved: (value) => oldPassword = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
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
                            onSaved: (value) => newPassword = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          // Reset Button
                          CustomButton(
                            text: 'Change Password',
                            fullWidth: true,
                            isLoading: is_loading,
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();

                                await _handleChangePassword();
                              } else {
                                setState(() {
                                  status = false;
                                  message = "Please fill all fields correctly!";
                                });
                              }
                            },
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
    );
  }
}
