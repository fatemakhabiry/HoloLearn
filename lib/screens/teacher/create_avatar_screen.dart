import 'dart:io';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/avatar_service.dart';
import '../../providers/app_state_provider.dart';

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

  // 'reuse' | 'upload' | 'default' — set based on isFirstTimeLogin in initState
  String selectedInputType = 'upload';

  String? audioPath;
  File? selectedImage;
  String? message;
  DefaultAvatarOption? _selectedDefaultAvatar;

  @override
  void initState() {
    super.initState();
    final appState = context.read<AppStateProvider>();
    // Returning users default to "reuse" so they're not forced to re-upload
    selectedInputType = appState.isFirstTimeLogin ? 'upload' : 'reuse';
  }

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
    final ImageSource? source = await showDialog<ImageSource>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Choose Photo Source'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.primaryColor),
              title: Text('Camera', style: AppStyles.h3.copyWith(color: context.textPrimary)),
              onTap: () => Navigator.pop(context, ImageSource.camera),
            ),
            ListTile(
              leading: const Icon(Icons.photo_library, color: AppColors.primaryColor),
              title: Text('Gallery', style: AppStyles.h3.copyWith(color: context.textPrimary)),
              onTap: () => Navigator.pop(context, ImageSource.gallery),
            ),
          ],
        ),
      ),
    );

    if (source == null) return;

    if (source == ImageSource.camera) {
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        CustomErrorHandler.show(context, message: 'Camera permission denied', type: ErrorType.fail);
        return;
      }
    }

    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(
      source: source,
      maxWidth: 1920,
      maxHeight: 1080,
      imageQuality: 85,
    );

    if (image == null) return;

    final pickedFile = File(image.path);

    // ── Identity verification step ──────────────────────────────────────
    final cameraStatus = await Permission.camera.request();
    if (!cameraStatus.isGranted) {
      CustomErrorHandler.show(
        context,
        message: 'Camera access is required to verify your identity.',
        type: ErrorType.fail,
      );
      return;
    }

    if (!mounted) return;
    CustomErrorHandler.show(
      context,
      message: 'Please look at the camera to verify your identity',
      type: ErrorType.info,
      duration: const Duration(seconds: 2),
    );

    final ImagePicker verifyPicker = ImagePicker();
    final XFile? liveShot = await verifyPicker.pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: CameraDevice.front,
      maxWidth: 1280,
      maxHeight: 720,
      imageQuality: 85,
    );

    if (liveShot == null) {
      CustomErrorHandler.show(
        context,
        message: 'Identity verification was cancelled.',
        type: ErrorType.fail,
      );
      return;
    }

    setState(() => isLoading = true);

    final appState = Provider.of<AppStateProvider>(context, listen: false);
    final verified = await AvatarService.verifyPhotoIdentity(
      appState: appState,
      selectedPhoto: pickedFile,
      liveCapture: File(liveShot.path),
    );

    if (!mounted) return;
    setState(() => isLoading = false);

    if (!verified) {
      CustomErrorHandler.show(
        context,
        message: 'Verification failed — face does not match. Please retake both photos.',
        type: ErrorType.fail,
      );
      setState(() {
        selectedImage = null;
        hasUploadedPhoto = false;
      });
      return;
    }

    setState(() {
      selectedImage = pickedFile;
      hasUploadedPhoto = true;
    });

    CustomErrorHandler.show(
      context,
      message: 'Photo verified and uploaded!',
      type: ErrorType.success,
    );
  } catch (e) {
    print('Error picking image: $e');
    if (mounted) setState(() => isLoading = false);
    CustomErrorHandler.show(
      context,
      message: 'Error verifying photo: $e',
      type: ErrorType.fail,
    );
  }
}
 Future<void> _takePhoto() async {
    try {
      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );

      if (image == null) return;

      setState(() {
        selectedImage = File(image.path);
        hasUploadedPhoto = true;
      });

      CustomErrorHandler.show(
        context,
        message: 'Photo captured and uploaded!',
        type: ErrorType.success,
      );
    } catch (e) {
      print('Error taking photo: $e');
      CustomErrorHandler.show(
        context,
        message: 'Error taking photo: $e',
        type: ErrorType.fail,
      );
    }
  }
  Future<void> _finishAndGenerate() async {
    // ── Reuse existing avatar — skip upload entirely ────────────────────────
    if (selectedInputType == 'reuse') {
      if (!mounted) return;
      Navigator.pushNamed(context, AppRoutes.lectureSetup);
      return;
    }

    // ── Default avatar path — skip the record/upload requirement ───────────
    if (selectedInputType == 'default' && _selectedDefaultAvatar != null) {
      try {
        setState(() => isLoading = true);
        final appState = Provider.of<AppStateProvider>(context, listen: false);

        final imageFile = await _assetToFile(_selectedDefaultAvatar!.imagePath);
        final voiceFile = await _assetToFile(
          'assets/${_selectedDefaultAvatar!.audioPath}',
        );

        final result = await AvatarService.uploadAvatar(
          appState: appState,
          photoFile: imageFile,
          voiceFile: voiceFile,
        );

        print('Upload result: $result');

        CustomErrorHandler.show(
          context,
          message: 'Default avatar selected! Generating...',
          type: ErrorType.success,
        );

        if (!mounted) return;
        Navigator.pushNamed(context, AppRoutes.lectureSetup);
      } catch (e) {
        CustomErrorHandler.show(
          context,
          message: 'Failed to select default avatar: $e',
          type: ErrorType.fail,
        );
      } finally {
        if (mounted) setState(() => isLoading = false);
      }
      return;
    }

    if (selectedInputType == 'default' && _selectedDefaultAvatar == null) {
      setState(() => message = 'Please select a default avatar');
      return;
    }

    // ── Custom upload flow ───────────────────────────────────────────────────
    if (selectedInputType == 'upload') {
      if (hasRecordedVoice && hasUploadedPhoto) {
        try {
          setState(() {
            isLoading = true;
          });
          final appState =
              Provider.of<AppStateProvider>(context, listen: false);

          File? voiceFile;
          if (audioPath != null) {
            voiceFile = File(audioPath!);
          }

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
          setState(() => message = 'Please complete both steps');
        } else if (!hasRecordedVoice) {
          setState(() => message = 'Please record or upload voice');
        } else {
          setState(() => message = 'Please upload a photo');
        }
      }
    }
  }

  /// Copies a bundled asset to a temp file so it can be sent as a File upload.
  Future<File> _assetToFile(String assetPath) async {
    final byteData = await rootBundle.load(assetPath);
    final tempDir = await getTemporaryDirectory();
    final fileName = assetPath.split('/').last;
    final file = File('${tempDir.path}/$fileName');
    await file.writeAsBytes(
      byteData.buffer.asUint8List(
        byteData.offsetInBytes,
        byteData.lengthInBytes,
      ),
    );
    return file;
  }

  // ========== BUILDERS ==========

  Widget _card({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(AppStyles.spacingL),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: AppStyles.cardShadow,
      ),
      child: child,
    );
  }

  Widget _buildAvatarSourceSelector() {
    final appState = context.read<AppStateProvider>();
    final isFirstTime = appState.isFirstTimeLogin;

    return _card(
      child: RadioOptionsGroup(
        sectionTitle: 'Choose your avatar',
        selectedId: selectedInputType,
        options: PhotoVoiceInputOptions.options(isFirstTime: isFirstTime),
        onOptionSelected: (id) {
          setState(() {
            selectedInputType = id;
            message = null;
          });
        },
      ),
    );
  }

  Widget _buildReuseCard() {
    return _card(
      child: Column(
        children: [
          const Icon(
            Icons.check_circle_outline,
            size: 48,
            color: AppColors.primaryColor,
          ),
          const SizedBox(height: AppStyles.spacingM),
          Text(
            'Your existing avatar will be reused',
            style: AppStyles.h3.copyWith(color: context.textPrimary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppStyles.spacingS),
          Text(
            'No need to re-record your voice or re-upload a photo.',
            style: AppStyles.bodyMedium.copyWith(
              color: context.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildUploadSection() {
    return Column(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // STEP 1 Card
            Expanded(
              child: UpoladCard(
                stepNumber: '1',
                icon: Icons.mic,
                primaryButtonText: 'RECORD\n VOICE',
                onPrimaryPressed: _recordVoice,
                secondaryButtonText: 'UPLOAD\n RECORD',
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
                secondaryButtonText: 'UPLOAD\n PHOTO',
                onSecondaryPressed: _uploadPhoto,
                onPrimaryPressed: _takePhoto,
                primaryButtonText: 'TAKE\n PHOTO',
                subtext: 'Used as basis for 3D avatar model',
                hasFile: hasUploadedPhoto,
                isDashed: true,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppStyles.spacingXL),
      ],
    );
  }

  Widget _buildDefaultAvatarSelector() {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Choose from default avatars',
            style: AppStyles.labelStyle.copyWith(
              fontWeight: AppFonts.bold,
              fontSize: AppFonts.fontSizeXS,
              letterSpacing: 1.2,
              color: context.textSecondary,
            ),
          ),
          const SizedBox(height: AppStyles.spacingM),
          Row(
            children: DefaultAvatars.all.map((avatar) {
              final isSelected = _selectedDefaultAvatar?.name == avatar.name;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppStyles.spacingS,
                  ),
                  child: DefaultAvatarCard(
                    avatar: avatar,
                    isSelected: isSelected,
                    onSelected: () {
                      setState(() {
                        _selectedDefaultAvatar = isSelected
                            ? null
                            : avatar; // tap again to deselect
                      });
                    },
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    Widget content;
    switch (selectedInputType) {
      case 'reuse':
        content = _buildReuseCard();
        break;
      case 'default':
        content = _buildDefaultAvatarSelector();
        break;
      case 'upload':
      default:
        content = _buildUploadSection();
        break;
    }

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: CustomAppBar(
        title: "Create Hologram Avatar",
        showBackButton: true,
      ),
      body: LoadingOverlay(
        isLoading: isLoading,
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Column(
              children: [
                _buildAvatarSourceSelector(),
                const SizedBox(height: AppStyles.spacingL),
                content,
                const SizedBox(height: AppStyles.spacingL),

                // Finish button
                CustomButton(
                  text: 'FINISH & GENERATE\nAVATAR',
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
        ),
      ),
    );
  }
}