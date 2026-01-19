import 'package:flutter/material.dart';
import'dart:io';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import 'package:record/record.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';
import '../widgets/error_handler_widget.dart';
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
  
  String? audioPath;
  File? selectedImage;

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

  void _finishAndGenerate() {
    if (hasRecordedVoice && hasUploadedPhoto) {
      // TODO: Send audioPath and selectedImage to your backend/API
      print('Audio path: $audioPath');
      print('Image path: ${selectedImage?.path}');
      
      CustomErrorHandler.show(
        context,
        message: 'Generating avatar...',
        type: ErrorType.success,
      );
      
      // TODO: Navigate to next screen
      // Navigator.pushNamed(context, '/lecture-setup');
    } else {
      String message = '';
      if (!hasRecordedVoice && !hasUploadedPhoto) {
        message = 'Please complete both steps';
      } else if (!hasRecordedVoice) {
        message = 'Please record or upload voice';
      } else {
        message = 'Please upload a photo';
      }
      
      CustomErrorHandler.show(
        context,
        message: message,
        type: ErrorType.fail,
      );
    }
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(title:   "Create Hologram Avatar", showBackButton: true),
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
                  child: _buildStepCard(
                    stepNumber: '1',
                    icon: Icons.mic,
                    primaryButtonText: 'RECORD VOICE',
                    primaryButtonOnPressed: _recordVoice,
                    secondaryButtonText: 'UPLOAD RECORD',
                    secondaryButtonOnPressed: _uploadRecord,
                    description: 'Used only for avatar voice synthesis',
                    isCompleted: hasRecordedVoice,
                  ),
                ),
                const SizedBox(width: AppStyles.spacingM),
                
                // STEP 2 Card
                Expanded(
                  child: _buildStepCard(
                    stepNumber: '2',
                    icon: Icons.photo,
                    primaryButtonText: 'UPLOAD PHOTO',
                    primaryButtonOnPressed: _uploadPhoto,
                    description: 'Used as basis for 3D avatar model',
                    isCompleted: hasUploadedPhoto,
                    showDashedBorder: true,
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
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStepCard({
    required String stepNumber,
    required IconData icon,
    required String primaryButtonText,
    required VoidCallback primaryButtonOnPressed,
    String? secondaryButtonText,
    VoidCallback? secondaryButtonOnPressed,
    required String description,
    required bool isCompleted,
    bool showDashedBorder = false,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppStyles.spacingL),
      height: 500,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: AppStyles.cardShadow,
      ),
      child: Column(
        children: [
          // Step header
          Text(
            'STEP $stepNumber',
            style: AppStyles.h3.copyWith(
              fontSize: AppStyles.spacingM,
              fontWeight: FontWeight.bold,
            ),
          ),
          
          const SizedBox(height: AppStyles.spacingL),
          
          // Icon circle or dashed box
          if (showDashedBorder)
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                border: Border.all(
                  color: AppColors.gray.withOpacity(0.5),
                  width: 2,
                  style: BorderStyle.solid,
                ),
                borderRadius: BorderRadius.circular(AppStyles.radiusM),
              ),
              child: Center(
                child: Text(
                  'PHOTO',
                  style: AppStyles.bodyMedium.copyWith(
                    color: AppColors.gray,
                  ),
                ),
              ),
            )
          else
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppColors.lightBlue,
                  width: 3,
                ),
              ),
              child: Center(
                child: Icon(
                  icon,
                  size: 40,
                  color: AppColors.lightBlue,
                ),
              ),
            ),
          
          const SizedBox(height: AppStyles.spacingL),
          
          // Primary button
          CustomButton(
            text: primaryButtonText,
            onPressed: primaryButtonOnPressed,
            buttonType: ButtonType.primary,
            fullWidth: true,
          ),
          
          // Secondary button (if exists)
          if (secondaryButtonText != null && secondaryButtonOnPressed != null) ...[
            const SizedBox(height: AppStyles.spacingM),
            CustomButton(
              onPressed: secondaryButtonOnPressed,
              text:secondaryButtonText,
              buttonType: ButtonType.secondary,
              fullWidth: true,
              ),
          ]
          else...[          
            const SizedBox(height: AppStyles.spacingXL),
          ],
          
          const SizedBox(height: AppStyles.spacingM),
          
          // Description
          Text(
            description,
            textAlign: TextAlign.center,
            style: AppStyles.caption.copyWith(
              color: AppColors.gray,
            ),
          ),
        ],
      ),
    );
  }
}