import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'dart:io';
import 'package:record/record.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:provider/provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/error_handler_widget.dart';
import '../widgets/button_widget.dart';
import '../services/avatar_service.dart';
import '../state/providers/app_state_provider.dart';
import '../widgets/message_handler_widget.dart';
import '../widgets/upload_card_widget.dart';

class CreateAvatarScreen extends StatefulWidget {
  const CreateAvatarScreen({super.key});

  @override
  State<CreateAvatarScreen> createState() => _CreateAvatarScreenState();
}

class _CreateAvatarScreenState extends State<CreateAvatarScreen> {
  final AudioRecorder _audioRecorder = AudioRecorder();

  bool isRecording = false;
  bool hasRecordedVoice = false;
  bool hasUploadedPhoto = false;
  bool isLoading = false;

  String? audioPath;
  File? selectedImage;
  String? message;

  @override
  void dispose() {
    _audioRecorder.dispose();
    super.dispose();
  }

  // ========== VOICE RECORDING ==========

  Future<void> _recordVoice() async {
    try {
      // Request microphone permission
      if (await Permission.microphone.request().isGranted) {
        if (isRecording) {
          // Stop recording
          final path = await _audioRecorder.stop();
          setState(() {
            isRecording = false;
            hasRecordedVoice = true;
            audioPath = path;
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
              path: '${Directory.systemTemp.path}/voice_recording.m4a',
            );
            setState(() {
              isRecording = true;
            });

            CustomErrorHandler.show(
              context,
              message: 'Recording started... Tap again to stop',
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

  Future<void> _uploadRecord() async {
    try {
      // Pick audio file
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.audio,
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        setState(() {
          audioPath = result.files.single.path;
          hasRecordedVoice = true;
        });

        CustomErrorHandler.show(
          context,
          message: 'Audio file uploaded!',
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

  // ========== IMAGE PICKING ==========

  Future<void> _uploadPhoto() async {
    try {
      // Show dialog to choose camera or gallery
      final ImageSource? source = await showDialog<ImageSource>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Choose Photo Source'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(
                  Icons.camera_alt,
                  color: AppColors.lightBlue,
                ),
                title: const Text('Camera', style: AppStyles.h3),
                onTap: () => Navigator.pop(context, ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(
                  Icons.photo_library,
                  color: AppColors.lightBlue,
                ),
                title: const Text('Gallery', style: AppStyles.h3),
                onTap: () => Navigator.pop(context, ImageSource.gallery),
              ),
            ],
          ),
        ),
      );

      if (source != null) {
        // Request camera permission if needed
        if (source == ImageSource.camera) {
          final status = await Permission.camera.request();
          if (!status.isGranted) {
            CustomErrorHandler.show(
              context,
              message: 'Camera permission denied',
              type: ErrorType.fail,
            );
            return;
          }
        }

        // Pick image
        final ImagePicker picker = ImagePicker();
        final XFile? image = await picker.pickImage(
          source: source,
          maxWidth: 1920,
          maxHeight: 1080,
          imageQuality: 85,
        );

        if (image != null) {
          setState(() {
            selectedImage = File(image.path);
            hasUploadedPhoto = true;
          });

          CustomErrorHandler.show(
            context,
            message: 'Photo uploaded!',
            type: ErrorType.success,
          );
        }
      }
    } catch (e) {
      print('Error picking image: $e');
      CustomErrorHandler.show(
        context,
        message: 'Error picking image: $e',
        type: ErrorType.fail,
      );
    }
  }

  Future<void> _finishAndGenerate() async {
    if (hasRecordedVoice && hasUploadedPhoto) {
      try {
        setState(() {
          isLoading = true;
        });
        // Get app state
        final appState = Provider.of<AppStateProvider>(context, listen: false);

        // Prepare files
        File? voiceFile;
        if (audioPath != null) {
          voiceFile = File(audioPath!);
        }

        // Upload avatar
        final result = await AvatarService.uploadAvatar(
          appState: appState,
          photoFile: selectedImage,
          voiceFile: voiceFile,
        );

        print('Upload result: $result');

        CustomErrorHandler.show(
          context,
          message: 'Avatar uploaded successfully! Generating...',
          type: ErrorType.success,
        );

        if (!mounted) return;

        // Navigator.push(
        //   context,
        //   MaterialPageRoute(builder: (context) => const LectureSetupScreen()),
        // );
        Navigator.pushNamed(context, AppRoutes.lectureSetup);
      } catch (e) {
        print('Error uploading avatar: $e');
        CustomErrorHandler.show(
          context,
          message: 'Failed to upload avatar: $e',
          type: ErrorType.fail,
        );
      } finally {
        setState(() {
          isLoading = false;
        });
      }
    } else {
      if (!hasRecordedVoice && !hasUploadedPhoto) {
        message = 'Please complete both steps';
      } else if (!hasRecordedVoice) {
        message = 'Please record or upload voice';
      } else {
        message = 'Please upload a photo';
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(
        title: "Create Hologram Avatar",
        showBackButton: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppStyles.spacingL),
        child: Column(
          children: [
            // Two step cards
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // STEP 1 Card
                Expanded(
                  child: UpoladCard(
                    stepNumber: '1',
                    icon: Icons.mic,
                    primaryButtonText: 'RECORD VOICE',
                    onPrimaryPressed: _recordVoice,
                    secondaryButtonText: 'UPLOAD RECORD',
                    onSecondaryPressed: _uploadRecord,
                    subtext: 'Used only for avatar voice synthesis',
                    hasFile: hasRecordedVoice,
                  ),
                ),
                const SizedBox(width: AppStyles.spacingM),

                // STEP 2 Card
                Expanded(
                  child: UpoladCard(
                    stepNumber: '2',
                    icon: Icons.photo,
                    iconLabel: 'PHOTO',
                    primaryButtonText: 'UPLOAD PHOTO',
                    onPrimaryPressed: _uploadPhoto,
                    subtext: 'Used as basis for 3D avatar model',
                    hasFile: hasUploadedPhoto,
                    isDashed: true,
                  ),
                ),
              ],
            ),

            const SizedBox(height: AppStyles.spacingXL),

            // Finish button
            CustomButton(
              text: 'FINISH & GENERATE AVATAR',
              onPressed: _finishAndGenerate,
              buttonType: ButtonType.primary,
              fullWidth: true,
              isLoading: isLoading,
            ),
            const SizedBox(height: AppStyles.spacingXL),

            if (message != null) ...[
              const SizedBox(height: AppStyles.spacingL),
              MessageDisplay(
                isSuccess: false,
                massegeBanner: "Error",
                message: message!,
                onDismiss: () => setState(() => message = null),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
