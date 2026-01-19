import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/utils/app_state.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'package:hololearn/widgets/text_form_widget.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:io';
import 'package:record/record.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/error_handler_widget.dart';

class TeacherProfileScreen extends StatefulWidget {
  const TeacherProfileScreen({super.key});

  @override
  State<TeacherProfileScreen> createState() => _TeacherProfileScreenState();
}

class _TeacherProfileScreenState extends State<TeacherProfileScreen> {
  final AudioRecorder _audioRecorder = AudioRecorder();
  String userName = AppState.userName;
  String userRole = "Computer Engineering Professor";
  File? profileImage;
  bool isRecording = false;
  String? audioPath;

  @override
  void dispose() {
    _audioRecorder.dispose();
    super.dispose();
  }

  void _changePassword() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Change Password' ,style: AppStyles.h2.copyWith(color: AppColors.lightBlue),),
        content: Text(
          'Are you sure you want to change your password ?',
          style: AppStyles.h3,
        ),
        actions: [
          CustomButton(
            onPressed: () => Navigator.pop(context),
            text:'Cancel',
            buttonType: ButtonType.secondary,
          ),
          CustomButton(
            text: 'Change Password',
            onPressed: () {
              // TODO: Implement password change
            },
          ),
        ],
      ),
    );
  }

  Future<void> _changeAvatarPhoto() async {
    try {
      final ImageSource? source = await showDialog<ImageSource>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('Choose Photo Source',style: AppStyles.h2.copyWith(color: AppColors.lightBlue),),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(Icons.camera_alt, color: AppColors.lightBlue),
                title: const Text('Camera', style: AppStyles.h3),
                onTap: () => Navigator.pop(context, ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(Icons.photo_library,color: AppColors.lightBlue),
                title: const Text('Gallery', style: AppStyles.h3),
                onTap: () => Navigator.pop(context, ImageSource.gallery),
              ),
            ],
          ),
        ),
      );

      if (source != null) {
        final ImagePicker picker = ImagePicker();
        final XFile? image = await picker.pickImage(
          source: source,
          maxWidth: 1920,
          maxHeight: 1080,
          imageQuality: 85,
        );

        if (image != null) {
          setState(() {
            profileImage = File(image.path);
          });

          CustomErrorHandler.show(
            context,
            message: 'Avatar photo updated!',
            type: ErrorType.success,
          );
        }
      }
    } catch (e) {
      CustomErrorHandler.show(
        context,
        message: 'Error: $e',
        type: ErrorType.fail,
      );
    }
  }

  void _changeVoiceSample() {
    showDialog(
      context: context,
      builder: (BuildContext dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title:Text('Change Voice Sample',style: AppStyles.h2.copyWith(color: AppColors.lightBlue)),           
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isRecording ? Colors.red : AppColors.lightBlue,
                      width: 3,
                    ),
                    color: isRecording ? Colors.red.withOpacity(0.1) : null,
                  ),
                  child: Center(
                    child: Icon(
                      isRecording ? Icons.stop : Icons.mic,
                      size: 50,
                      color: isRecording ? Colors.red : AppColors.lightBlue,
                    ),
                  ),
                ),

                const SizedBox(height: AppStyles.spacingL),

                // Record button
                CustomButton(
                  text: isRecording ? 'STOP RECORDING' : 'RECORD VOICE',
                  onPressed: () async {
                    await _recordVoiceInDialog(setDialogState);
                  },
                  buttonType: ButtonType.primary,
                  fullWidth: true,
                ),

                const SizedBox(height: AppStyles.spacingM),

                // Upload button
                CustomButton(
                  text: 'Upload Audio File',
                  onPressed: () async {
                    await _uploadVoiceFile();
                    Navigator.pop(dialogContext);
                  },
                  buttonType: ButtonType.secondary,
                  fullWidth: true,
                ),

                if (audioPath != null)
                  Padding(
                    padding: const EdgeInsets.only(top: AppStyles.spacingS),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.check_circle,
                          color: AppColors.success,
                          size: 16,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          'Voice recorded',
                          style: AppStyles.caption.copyWith(
                            color: AppColors.success,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            actions: [
              CustomButton(
                onPressed: () {
                  if (isRecording) {
                    _audioRecorder.stop();
                  }
                  Navigator.pop(dialogContext);
                },
                text: 'Cancel',
                buttonType: ButtonType.secondary,
              ),
              CustomButton(
                onPressed:() {
                        // TODO: Save voice sample to backend
                        Navigator.pop(dialogContext);
                        CustomErrorHandler.show(
                          context,
                          message: 'Voice sample updated successfully!',
                          type: ErrorType.success,
                        );
                      },
                text: 'Save',
                buttonType: ButtonType.primary,
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _recordVoiceInDialog(StateSetter setDialogState) async {
    try {
      if (await Permission.microphone.request().isGranted) {
        if (isRecording) {
          // Stop recording
          final path = await _audioRecorder.stop();
          setDialogState(() {
            isRecording = false;
            audioPath = path;
          });
          setState(() {
            isRecording = false;
          });

          CustomErrorHandler.show(
            context,
            message: 'Recording saved!',
            type: ErrorType.success,
          );
        } else {
          // Start recording
          if (await _audioRecorder.hasPermission()) {
            await _audioRecorder.start(
              const RecordConfig(),
              path: '${Directory.systemTemp.path}/voice_sample.m4a',
            );
            setDialogState(() {
              isRecording = true;
            });
            setState(() {
              isRecording = true;
            });

            CustomErrorHandler.show(
              context,
              message: 'Recording started... Tap stop to finish',
              type: ErrorType.info,
              duration: const Duration(seconds: 2),
            );
          }
        }
      } else {
        CustomErrorHandler.show(
          context,
          message: 'Microphone permission denied',
          type: ErrorType.fail,
        );
      }
    } catch (e) {
      print('Error recording: $e');
      CustomErrorHandler.show(
        context,
        message: 'Recording error: $e',
        type: ErrorType.fail,
      );
    }
  }

  Future<void> _uploadVoiceFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.audio,
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        setState(() {
          audioPath = result.files.single.path;
        });

        CustomErrorHandler.show(
          context,
          message: 'Audio file uploaded successfully!',
          type: ErrorType.success,
        );
      }
    } catch (e) {
      print('Error picking audio: $e');
      CustomErrorHandler.show(
        context,
        message: 'Error picking file: $e',
        type: ErrorType.fail,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(title: "Teacher Profile", showBackButton: true),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppStyles.spacingL),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppStyles.spacingXL),
              decoration: BoxDecoration(
                color: AppColors.white,
                borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                boxShadow: AppStyles.cardShadow,
              ),
              child: Column(
                children: [
                  // Profile picture
                  Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.lightBlue, width: 3),
                    ),
                    child: CircleAvatar(
                      radius: 48,
                      child: Icon(
                        Icons.person,
                        size: 50,
                        color: AppColors.lightBlue,
                      ),
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingM),

                  // Name
                  Text(
                    userName,
                    style: AppStyles.h2,
                    textAlign: TextAlign.center,
                  ),

                  const SizedBox(height: AppStyles.spacingS),
                  // Role
                  Text(
                    userRole,
                    style: AppStyles.caption,
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppStyles.spacingL),
            // Account Settings Card
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
                    "Account Settings",
                    style: AppStyles.h3.copyWith(color: AppColors.textLight),
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    prefixIcon: Icon(
                      Icons.lock_outline,
                      color: AppColors.lightBlue,
                    ),
                    hintText: 'Password',
                    readOnly: true,
                    suffixIcon: TextButton(
                      onPressed: _changePassword,
                      child: Text(
                        'Change',
                        style: AppStyles.h3.copyWith(
                          color: AppColors.lightBlue,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingL),
                  Text(
                    "Avatar Settings",
                    style: AppStyles.h3.copyWith(color: AppColors.textLight),
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    prefixIcon: Icon(Icons.photo_camera_outlined, color: AppColors.lightBlue),
                    hintText: 'change avatar photo',
                    readOnly: true,
                    suffixIcon: TextButton(
                      onPressed: _changeAvatarPhoto,
                      child: Text(
                        'Change',
                        style: AppStyles.h3.copyWith(
                          color: AppColors.lightBlue,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    prefixIcon: Icon(
                      Icons.mic,
                      color: AppColors.lightBlue,
                    ),
                    hintText: 'change voice sample',
                    readOnly: true,
                    suffixIcon: TextButton(
                      onPressed: _changeVoiceSample,
                      child: Text(
                        'Change',
                        style: AppStyles.h3.copyWith(
                          color: AppColors.lightBlue,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: AppStyles.spacingL,
                  ), // Avatar Settings Card
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
