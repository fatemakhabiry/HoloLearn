import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/constants/app_fonts.dart';
import 'package:hololearn/screens/forget_pass_screen.dart';
import 'package:hololearn/widgets/message_handler_widget.dart';
import 'package:hololearn/widgets/text_form_widget.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/services/auth_service.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  Map<String, dynamic>? data;
  String? email;
  String? password;
  String message = ""; //not required
  bool _obscureText = true;
  bool _loginSucess = false;
  bool _showbanner = false;

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
                  ), // for space between logo and title
                  // HoloLearn Title
                  Text('HoloLearn', style: AppStyles.logo),

                  const SizedBox(
                    height: AppStyles.spacingXS,
                  ), //for space between title and subtitle
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
                          // Forgot Password Link
                          Align(
                            alignment: Alignment.center,
                            child: TextButton(
                              onPressed: () {
                                // Handle forgot password
                                // *****go to forgot password page ********
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
                          ),
                          const SizedBox(height: AppStyles.spacingL),

                          // Login Button
                          CustomButton(
                            text: 'LOG IN',
                            fullWidth: true,
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                //call API to login
                                _showbanner = true;
                                try {
                                  data = await AuthService.login(
                                    email: email!,
                                    password: password!,
                                  );
                                  message =
                                      "You've logged in Success! +${data}";
                                  setState(() {
                                    _showbanner = true;
                                    _loginSucess = true;
                                  });
                                } catch (e) {
                                  setState(() {
                                    _showbanner = true;
                                    _loginSucess = false;
                                    message = "Exception as thrown";
                                  });
                                }
                              } else {
                                setState(() {
                                  _showbanner = true;
                                  _loginSucess = false;
                                  message = "Please fill all fields correctly!";
                                });
                              }
                            },
                          ),
                          if (_showbanner) ...[
                            const SizedBox(height: AppStyles.spacingL),
                            MessageDisplay(
                              isSuccess: _loginSucess,
                              massegeBanner: _loginSucess
                                  ? "Login Succesful"
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
