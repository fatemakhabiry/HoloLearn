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

  // The live-capture frame that backs `selectedImage` for identity
  // verification. For gallery uploads this comes from a dedicated
  // verification shot. For direct camera capture, the captured selfie
  // itself doubles as the live capture (no second shot needed), since
  // it's already proof-of-liveness.
  File? liveCaptureFile;

  // True once `selectedImage` has already been verified AND saved on the
  // backend via /upload-photo (from either _uploadPhoto or _takePhoto).
  // _finishAndGenerate() uses this to skip a redundant re-upload of the
  // same photo + live capture pair.
  bool _photoAlreadySaved = false;

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

  /// "UPLOAD PHOTO" — pick a photo from the gallery, then require a fresh
  /// front-camera live shot to verify the picked photo is really this
  /// person. Calls `AvatarService.uploadPhoto` directly — this both
  /// verifies AND saves the photo on the backend in one call, so there's
  /// no separate stateless pre-check step here.
  Future<void> _uploadPhoto() async {
    try {
      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );

      if (image == null) return;

      final pickedFile = File(image.path);

      File liveShotFile;

      // Gallery pick — require a fresh front-camera shot to verify
      // the picked photo is really this person.
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

      liveShotFile = File(liveShot.path);

      setState(() => isLoading = true);

      final appState = Provider.of<AppStateProvider>(context, listen: false);

      // uploadPhoto() only returns normally on a 200 response — any
      // mismatch (422), no-face-detected, or other failure throws and is
      // caught below. Reaching this line without an exception already
      // means the backend verified and saved the photo successfully.
      // (Its return value is the response body Map, not a bool — never
      // compare it against `true`.)
      await AvatarService.uploadPhoto(
        appState: appState,
        photoFile: pickedFile,
        liveCaptureFile: liveShotFile,
      );

      if (!mounted) return;
      setState(() => isLoading = false);

      setState(() {
        selectedImage = pickedFile;
        liveCaptureFile = liveShotFile;
        hasUploadedPhoto = true;
        _photoAlreadySaved = true;
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

  /// "TAKE PHOTO" — direct front-camera capture. This is already a live
  /// capture, so no separate verification shot is required. The same
  /// image is kept as the live-capture reference for the final upload,
  /// since the backend requires a `live_capture` field on every call.
  Future<void> _takePhoto() async {
    try {
      final status = await Permission.camera.request();
      if (!status.isGranted) {
        CustomErrorHandler.show(
          context,
          message: 'Camera permission denied',
          type: ErrorType.fail,
        );
        return;
      }

      final ImagePicker picker = ImagePicker();
      final XFile? image = await picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        maxWidth: 1920,
        maxHeight: 1080,
        imageQuality: 85,
      );

      if (image == null) return;

      final capturedFile = File(image.path);

      setState(() => isLoading = true);

      final appState = Provider.of<AppStateProvider>(context, listen: false);

      // Same reasoning as _uploadPhoto: this is the real save call, and
      // it only returns normally on success. The captured selfie is
      // already a live capture, so it's sent as both `photo` and
      // `live_capture` — there's nothing else to verify it against.
      await AvatarService.uploadPhoto(
        appState: appState,
        photoFile: capturedFile,
        liveCaptureFile: capturedFile,
      );

      if (!mounted) return;
      setState(() => isLoading = false);

      setState(() {
        selectedImage = capturedFile;
        liveCaptureFile = capturedFile;
        hasUploadedPhoto = true;
        _photoAlreadySaved = true;
      });

      CustomErrorHandler.show(
        context,
        message: 'Photo captured and uploaded!',
        type: ErrorType.success,
      );
    } catch (e) {
      print('Error taking photo: $e');
      if (mounted) setState(() => isLoading = false);
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
          // Default avatars are bundled assets, not a real person, so
          // there's nothing to verify against. The backend still requires
          // a live_capture field on every call, so we send the same
          // asset image for both — it will trivially match itself.
          liveCaptureFile: imageFile,
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
          final appState = Provider.of<AppStateProvider>(
            context,
            listen: false,
          );

          File? voiceFile;
          if (audioPath != null) {
            voiceFile = File(audioPath!);
          }

          // The photo was already verified and saved on the backend by
          // _uploadPhoto/_takePhoto, which call /upload-photo directly.
          // Sending it again here would just re-verify and re-save the
          // identical photo + live capture, re-triggering background
          // preprocessing for no reason — so skip it when already saved.
          final result = await AvatarService.uploadAvatar(
            appState: appState,
            photoFile: _photoAlreadySaved ? null : selectedImage,
            voiceFile: voiceFile,
            liveCaptureFile: _photoAlreadySaved ? null : liveCaptureFile,
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
  // (unchanged — left exactly as in the original file)

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
            style: AppStyles.bodyMedium.copyWith(color: context.textSecondary),
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