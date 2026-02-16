import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../constants/app_fonts.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../services/auth_service.dart';
import '../state/providers/app_state_provider.dart';
import 'forget_pass_screen.dart';
import 'teacher_dashboard_screen.dart';
import 'student_dashboard_screen.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _emailController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  
  Map<String, dynamic>? data;
  String? email;
  String? password;
  String message = "";
  bool _obscureText = true;
  bool _loginSucess = false;
  bool _showbanner = false;
  bool is_loading = false;
  String? error_message = null;
  bool _rememberMe = false; // NEW: Remember Me checkbox state

  @override
  void initState() {
    super.initState();
    _loadSavedEmail(); // NEW: Load saved email on init
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // NEW: Load saved email from storage
  Future<void> _loadSavedEmail() async {
    final appState = Provider.of<AppStateProvider>(context, listen: false);
    await appState.init(); // Load from storage
    
    if (appState.email.isNotEmpty && mounted) {
      setState(() {
        _emailController.text = appState.email;
        _rememberMe = appState.rememberMe; // Load remember me state
      });
    }
  }

  Future<void> _handleLogin() async {
    setState(() {
      is_loading = true;
    });
    try {
      data = await AuthService.login(email: email!, password: password!);

      // Set app state
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await appState.setEmail(data!['user']['email']);
      await appState.setUserName(data!['user']['full_name']);
      await appState.setUserRole(data!['user']['role']);
      await appState.setAccessToken(data!['access_token']);
      await appState.setRememberMe(_rememberMe); // NEW: Save Remember Me preference
      
      print('🔑 Access Token: ${appState.accessToken}');
      print('✅ Remember Me: $_rememberMe'); // NEW: Debug log
      
      // Show success message
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Login successful',
          type: ErrorType.success,
        );
        // Wait 3 seconds
        await Future.delayed(const Duration(seconds: 3));

        if (appState.userRole == 'teacher') {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => const TeacherDashboardScreen(),
            ),
          );
        } else {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => const StudentDashboardScreen(),
            ),
          );
        }
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
                  // Logo Badge
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppStyles.spacingM,
                      vertical: AppStyles.spacingS,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.lightBlue,
                      borderRadius: BorderRadius.circular(AppStyles.radiusPill),
                    ),
                    child: Text(
                      'HOLOGRAPHIC LEARNING',
                      style: AppStyles.caption.copyWith(
                        color: AppColors.white,
                        fontWeight: AppFonts.semiBold,
                        letterSpacing: 1.2,
                      ),
                    ),
                  ),
                  const SizedBox(
                    height: AppStyles.spacingM,
                  ),
                  // HoloLearn Title
                  Text('HoloLearn', style: AppStyles.logo),

                  const SizedBox(
                    height: AppStyles.spacingXS,
                  ),
                  // Subtitle
                  Text(
                    'Next-generation virtual education',
                    style: AppStyles.bodyMedium.copyWith(
                      color: AppColors.textLight,
                    ),
                  ),
                  const SizedBox(height: AppStyles.spacingXL),
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
                            controller: _emailController, // NEW: Add controller
                            hintText: 'Enter your email',
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
                            onSaved: (value) => email = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          CustomTextFormField(
                            controller: _passwordController, // NEW: Add controller
                            suffixIcon: IconsButton(
                              size: 24,
                              iconColor: Colors.grey,
                              backgroundColor: Colors.transparent,
                              icon: _obscureText
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                              onPressed: () {
                                setState(() => _obscureText = !_obscureText);
                              },
                            ),
                            hintText: 'Enter your password',
                            label: "Password",
                            obscureText: _obscureText,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Password is required';
                              }
                              return null;
                            },
                            onSaved: (value) => password = value,
                          ),
                          const SizedBox(height: AppStyles.spacingM),
                          
                          // NEW: Remember Me Checkbox Row
                          Row(
                            children: [
                              Checkbox(
                                value: _rememberMe,
                                onChanged: (value) {
                                  setState(() {
                                    _rememberMe = value ?? false;
                                  });
                                },
                                activeColor: AppColors.lightBlue,
                                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                visualDensity: VisualDensity.compact,
                              ),
                              Text(
                                'Remember me',
                                style: AppStyles.bodyMedium.copyWith(
                                  color: AppColors.textBlack,
                                ),
                              ),
                              const Spacer(),
                              // Forgot Password Link (moved to row)
                              TextButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) =>
                                          const ForgetPasswordPage(),
                                    ),
                                  );
                                },
                                style: TextButton.styleFrom(
                                  padding: EdgeInsets.zero,
                                  minimumSize: Size.zero,
                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                child: Text(
                                  'Forgot Password?',
                                  style: AppStyles.link.copyWith(
                                    color: AppColors.lightBlue,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppStyles.spacingL),

                          // Login Button
                          CustomButton(
                            text: 'LOG IN',
                            fullWidth: true,
                            isLoading: is_loading,
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                _showbanner = false;
                                await _handleLogin();
                              } else {
                                // Form is not valid
                                setState(() {
                                  _showbanner = true;
                                  _loginSucess = false;
                                  message = "Please fill all fields correctly!";
                                });
                              }
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                  if (_showbanner) ...[
                    const SizedBox(height: AppStyles.spacingL),
                    MessageDisplay(
                      isSuccess: _loginSucess,
                      massegeBanner: _loginSucess ? "" : "Error",
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