import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/file_upload_widget.dart';
import '../widgets/text_form_widget.dart';
import '../utils/app_state.dart';

class CreateNewLectureScreen extends StatefulWidget {
  const CreateNewLectureScreen({super.key});

  @override
  State<CreateNewLectureScreen> createState() => _CreateNewLectureScreenState();
}

class _CreateNewLectureScreenState extends State<CreateNewLectureScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  String? lecture_title;
  String? course_code;
  //hshil de w a7ot get items mn el backend
  // Future<List<String>> _items = Future.value([
  //   'CS101',
  //   'CS102',
  //   'CS103',
  //   'CS104',
  // ]);
  final List<String> _items = ['CS101', 'CS102', 'CS103', 'CS104'];
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
                            onPressed: () {
                              if (_formKey.currentState!.validate()) {
                                _formKey.currentState!.save();
                                if (course_code != null) {
                                  // LectureState.lectureTitle = lecture_title!;
                                  // LectureState.courseCode = course_code!;
                                }
                              }
                            },
                          ),
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
