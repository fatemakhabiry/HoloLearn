import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../widgets/file_upload_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../utils/app_state.dart';
import '../services/avatar_data_service.dart';
import './lecture_options_screen.dart';
import 'create_avatar_screen.dart';

class CreateNewLectureScreen extends StatefulWidget {
  const CreateNewLectureScreen({super.key});

  @override
  State<CreateNewLectureScreen> createState() => _CreateNewLectureScreenState();
}

class _CreateNewLectureScreenState extends State<CreateNewLectureScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  String? lecture_title;
  String? course_code;
  bool is_loading = false;
  String message = "";
  bool _showbanner = false;
  bool _success = false;
  String? error_message = null;

  final List<String> _items = ['CS101', 'CS102', 'CS103', 'CS104'];
  // Future<List<String>> _getItems() async {}
  Future<void> _handleNext() async {
    // Start loading
    setState(() {
      is_loading = true;
    });

    try {
      await AvatarService.checkAvatarStatus();
      if (AppState.isFirstTimeLogin) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => const CreateAvatarScreen()),
        );
      } else {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => const LectureSetupScreen()),
        );
      }
    } on ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      error_message = e.toString().replaceFirst('Exception: ',  '');
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
      appBar: CustomAppBar(title: "Create Lecture", showBackButton: true),
      body: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 400),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  FileUploadWidget(
                    label: 'Lecture Content',
                    supportedFormats: ['pdf', 'pptx', 'txt'],
                    isRequired: true,
                    headerText: 'DRAG & DROP OR BROWSE FILES ', // Optional
                    subheaderText: 'Supported: PDF, PPTX, TXT', // Optional
                    onFilesSelected: (files) {
                      print('Selected ${files.length} files');
                      for (var file in files) {
                        print('File: ${file.name}');
                      }
                    },
                  ),
                  SizedBox(height: AppStyles.spacingL),
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
                            hintText: 'Enter Lecture Title',
                            label: "Lecture Title",
                            keyboardType: TextInputType.text,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Lecture title is required';
                              }
                              return null;
                            },
                            onSaved: (value) => lecture_title = value,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          CustomDropdown(
                            label: "Course Code",
                            items: _items,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Course code is required';
                              }
                            },
                            onChanged: (value) {
                              course_code = value;
                            },
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                          CustomButton(
                            text: 'NEXT: AVATAR OPTIONS & SCHEDULING',
                            isLoading: is_loading,
                            fullWidth: true,
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();

                                await _handleNext();
                              } else {
                                // Form is not valid
                                setState(() {
                                  _showbanner = true;
                                  _success = false;
                                  message =
                                      "Please fill all required fields correctly!";
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
                      isSuccess: _success,
                      massegeBanner: _success
                          ? "Lecture Created Successfully"
                          : "Creation Failed",
                      message: message,
                      onDismiss: () => setState(() => _showbanner = false),
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
