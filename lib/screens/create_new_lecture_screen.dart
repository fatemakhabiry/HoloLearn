import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import '../services/course_service.dart';
import '../services/lecture_service.dart';
import '../services/avatar_service.dart';
import '../state/providers/app_state_provider.dart';
import '../widgets/app_bar_widget.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../constants/app_fonts.dart';
// import '../widgets/avatar_option_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/file_upload_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../widgets/avatar_option_widget.dart';

class CreateNewLectureScreen extends StatefulWidget {
  const CreateNewLectureScreen({super.key});

  @override
  State<CreateNewLectureScreen> createState() => _CreateNewLectureScreenState();
}

class _CreateNewLectureScreenState extends State<CreateNewLectureScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  // Input Type Selection
  // String selectedInputType = 'document'; // Default to document

  // Form fields
  String? lectureTitle;
  String? courseCode;
  String? lectureUrl;

  // File handling
  String? selectedFilePath;
  String? selectedFileName;
  String selectedInputType = 'document'; // Default to document
  bool isLoading = false;
  bool isFetchingCourses = true;
  String message = "";
  bool showBanner = false;
  bool success = false;
  String? error_message;
  List<String> courseItems = [];

  @override
  void initState() {
    super.initState();
    _fetchCourseCodes();
  }

  Future<void> _fetchCourseCodes() async {
    setState(() {
      isFetchingCourses = true;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final courses = await CourseService.fetchCourseCodes(appState);

      if (!mounted) return;

      setState(() {
        courseItems = courses;
        isFetchingCourses = false;
      });
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      error_message = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (error_message != null) {
        if (mounted) {
          CustomErrorHandler.show(
            context,
            message: error_message!,
            type: ErrorType.fail,
          );
        }
        error_message = null;
      }
      if (mounted) {
        setState(() {
          isFetchingCourses = false;
        });
      }
    }
  }

  Future<void> _handleNext() async {
    // Validate form
    if (!_formKey.currentState!.validate()) {
      if (courseItems.isEmpty) {
        error_message = "No courses available. Contact Admin.";
        CustomErrorHandler.show(
          context,
          message: error_message!,
          type: ErrorType.fail,
        );
        return;
      }
      setState(() {
        showBanner = true;
        success = false;
        message = "Please fill all required fields correctly!";
      });
      return;
    }

    // Save form
    _formKey.currentState!.save();

    // Validate file is selected (for document type)
    // if (selectedInputType == 'document' && selectedFilePath == null) {
    //   error_message = "Please select a lecture file";
    //   CustomErrorHandler.show(
    //     context,
    //     message: error_message!,
    //     type: ErrorType.fail,
    //   );
    //   return;
    // }
    if (selectedFilePath == null &&
        (lectureUrl == null || lectureUrl!.isEmpty)) {
      error_message = "Please provide a lecture file or a URL";
      CustomErrorHandler.show(
        context,
        message: error_message!,
        type: ErrorType.fail,
      );
      return;
    }

    // Start loading
    setState(() {
      isLoading = true;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      // Create lecture draft via API
      final lectureResponse = await LectureService.createLectureDraft(
        appState: appState,
        title: lectureTitle!,
        courseCode: courseCode!,
        filePath: selectedFilePath!,
      );

      appState.setLectureId(lectureResponse.lectureId);

      print('✅ Lecture created with ID: ${appState.lectureId}');

      // Check avatar status
      await AvatarService.checkAvatarStatus(appState);

      if (!mounted) return;

      // Navigate to next screen with lecture_id
      if (appState.isFirstTimeLogin) {
        // Navigator.push(
        //   context,
        //   MaterialPageRoute(builder: (context) => const CreateAvatarScreen()),
        // );
        Navigator.pushNamed(context, AppRoutes.createAvatar);
      } else {
        // Navigator.push(
        //   context,
        //   MaterialPageRoute(
        //     builder: (context) => LectureSetupScreen(
        //     ),
        //   ),
        // );
        Navigator.pushNamed(context, AppRoutes.createAvatar);
      }
    } on http.ClientException {
      error_message = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } catch (e) {
      // Handle API errors
      error_message = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (error_message != null) {
        if (mounted) {
          CustomErrorHandler.show(
            context,
            message: error_message!,
            type: ErrorType.fail,
          );
        }
        error_message = null;
      }
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: const CustomAppBar(title: "Create Lecture", showBackButton: true),
      body: Center(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Container(
              constraints: const BoxConstraints(maxWidth: 600),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Input Type Selection Container
                    Container(
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      decoration: BoxDecoration(
                        color: AppColors.white,
                        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                        boxShadow: AppStyles.cardShadow,
                      ),
                      child: RadioOptionsGroup(
                        sectionTitle: 'LECTURE CONTENT INPUT TYPE',
                        selectedId: selectedInputType,
                        options: LectureInputOptions.options,
                        onOptionSelected: (id) {
                          setState(() {
                            selectedInputType = id;
                          });
                          print('Selected input type: $id');
                        },
                      ),
                    ),
                    const SizedBox(height: AppStyles.spacingL),

                    // Conditional Input - Document Upload or URL
                    // if (selectedInputType == 'document')[
                    FileUploadWidget(
                      label: 'Lecture Content',
                      supportedFormats: const ['pdf', 'pptx', 'txt'],
                      isRequired: true,
                      headerText: 'DRAG & DROP OR BROWSE FILES',
                      subheaderText: 'Supported: PDF, PPTX, TXT',
                      onFilesSelected: (files) {
                        if (files.isNotEmpty) {
                          setState(() {
                            selectedFilePath = files.first.path;
                            selectedFileName = files.first.name;
                          });
                          print('File selected: ${files.first.name}');
                          print('File path: ${files.first.path}');
                        }
                      },
                    ),

                    const SizedBox(height: AppStyles.spacingL),

                    if (selectedInputType == 'url') ...[
                    Container(
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      decoration: BoxDecoration(
                        color: AppColors.white,
                        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                        boxShadow: AppStyles.cardShadow,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'LECTURE CONTENT URL',
                            style: AppStyles.labelStyle.copyWith(
                              fontWeight: AppFonts.bold,
                              fontSize: AppFonts.fontSizeXS,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: AppStyles.spacingM),
                          CustomTextFormField(
                            hintText: 'https://example.com/lecture-content',
                            label: 'Content URL',
                            keyboardType: TextInputType.url,
                            prefixIcon: const Icon(Icons.link),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'URL is required';
                              }
                              if (!value.startsWith('http://') &&
                                  !value.startsWith('https://')) {
                                return 'Please enter a valid URL';
                              }
                              return null;
                            },
                            onSaved: (value) => lectureUrl = value,
                          ),
                        ],
                      ),
                    ),
                    ],
                    const SizedBox(height: AppStyles.spacingL),

                    // Lecture Details Container
                    Container(
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      decoration: BoxDecoration(
                        color: AppColors.white,
                        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                        boxShadow: AppStyles.cardShadow,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'LECTURE DETAILS',
                            style: AppStyles.labelStyle.copyWith(
                              fontWeight: AppFonts.bold,
                              fontSize: AppFonts.fontSizeXS,
                              letterSpacing: 1.2,
                            ),
                          ),
                          const SizedBox(height: AppStyles.spacingM),

                          // Lecture Title
                          CustomTextFormField(
                            hintText: 'Enter Lecture Title',
                            label: 'Lecture Title',
                            keyboardType: TextInputType.text,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Lecture title is required';
                              }
                              return null;
                            },
                            onSaved: (value) => lectureTitle = value,
                          ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Course Code Dropdown
                          CustomDropdown(
                            label: courseItems.isEmpty
                                ? "No course available"
                                : "Select Course Code",
                            items: courseItems,
                            onChanged: (value) {
                              setState(() {
                                courseCode = value;
                              });
                            },
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Course code is required';
                              }
                              return null;
                            },
                          ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Next Button
                          CustomButton(
                            text: 'NEXT: AVATAR OPTIONS & SCHEDULING',
                            isLoading: isLoading,
                            fullWidth: true,
                            onPressed: _handleNext,
                          ),
                        ],
                      ),
                    ),

                    // Message Banner
                    if (showBanner) ...[
                      const SizedBox(height: AppStyles.spacingL),
                      MessageDisplay(
                        isSuccess: success,
                        massegeBanner: success
                            ? "Lecture Created Successfully"
                            : "Creation Failed",
                        message: message,
                        onDismiss: () => setState(() => showBanner = false),
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
