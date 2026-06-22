import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:record/record.dart';
import 'package:file_picker/file_picker.dart';
import 'package:permission_handler/permission_handler.dart';

import '../providers/theme_provider.dart';
import '../widgets/widgets.dart';
import '../routes/app_routes.dart';
import '../constants/constants.dart';
import '../services/avatar_service.dart';
import '../providers/app_state_provider.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final AudioRecorder _audioRecorder = AudioRecorder();
  late String userName;
  String userRole = "Computer Engineering Professor";
  File? profileImage;
  bool isRecording = false;
  bool isUploading = false;
  bool isLoading = false;
  String? audioPath;
  late AppStateProvider appState = Provider.of<AppStateProvider>(
    context,
    listen: false,
  );

  @override
  void initState() {
    super.initState();
    final appState = Provider.of<AppStateProvider>(context, listen: false);
    userName = appState.userName;
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    super.dispose();
  }

  /// Converts a raw PlatformException from image_picker's camera into a
  /// clear, actionable message. Camera permission denials in particular
  /// surface as `PlatformException(camera_access_denied, ...)`, which
  /// looks cryptic if shown to the user as-is.
  String _describeCameraError(Object e) {
    if (e is PlatformException) {
      switch (e.code) {
        case 'camera_access_denied':
          return 'Camera access is turned off for this app. Please enable it in your device Settings to take a photo.';
        case 'no_available_camera':
          return 'No camera was found on this device.';
        case 'already_active':
          return 'The camera is already in use. Please try again.';
        default:
          return e.message ?? 'Could not access the camera. Please try again.';
      }
    }
    return e.toString();
  }

  void _changePassword() {
    CustomConfirmationDialog.show(
      context,
      title: 'Change Password',
      message: 'Are you sure you want to change your password?',
      confirmButtonText: 'Change Password',
      onConfirm: () {
        Navigator.pop(context); // Close dialog
        // Navigator.push(
        //   context,
        //   MaterialPageRoute(builder: (context) => ChangePasswordScreen()),
        // );
        Navigator.pushNamed(context, AppRoutes.changePassword);
      },
    );
  }
  void _logout(){
        CustomConfirmationDialog.show(
      context,
      title: 'Log Out',
      message: 'Are you sure you want to Log Out from your Account?',
      confirmButtonText: 'yes',
      onConfirm: () {
        Navigator.pop(context);
        final appState = Provider.of<AppStateProvider>(context, listen: false);
        appState.clearAuth();
        // appState.setRememberMe(false);
        Navigator.pushNamed(context, AppRoutes.login);
      },
    );

  }
  void _lectureHistory() {
    // Navigator.push(
    //   context,
    //   MaterialPageRoute(builder: (context) => TeacherLecturesScreen()),
    // );
    Navigator.pushNamed(context, AppRoutes.lectureHistory);
  }

  void _changeVoiceSample() {
    // Save the outer context
    final outerContext = context;

    showDialog(
      context: context,
      builder: (BuildContext dialogContext) => StatefulBuilder(
        builder: (_, setDialogState) {
          return AlertDialog(
            title: Text(
              'Change Voice Sample',
              style: AppStyles.h2.copyWith(color: AppColors.primaryColor),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isRecording ? Colors.red : AppColors.primaryColor,
                      width: 3,
                    ),
                    color: isRecording ? Colors.red.withOpacity(0.1) : null,
                  ),
                  child: Center(
                    child: Icon(
                      isRecording ? Icons.stop : Icons.mic,
                      size: 50,
                      color: isRecording ? Colors.red : AppColors.primaryColor,
                    ),
                  ),
                ),
                const SizedBox(height: AppStyles.spacingL),

                CustomButton(
                  text: isRecording ? 'STOP RECORDING' : 'RECORD VOICE',
                  onPressed: () => _recordVoiceInDialog(setDialogState),
                  buttonType: ButtonType.primary,
                  fullWidth: true,
                ),
                const SizedBox(height: AppStyles.spacingM),

                CustomButton(
                  text: 'Upload Audio File',
                  onPressed: () async {
                    try {
                      FilePickerResult? result = await FilePicker.platform
                          .pickFiles(
                            type: FileType.audio,
                            allowMultiple: false,
                          );

                      if (result == null || result.files.single.path == null)
                        return;

                      final selectedFile = File(result.files.single.path!);

                      // Update both states
                      setState(() {
                        audioPath = result.files.single.path;
                      });

                      setDialogState(() {
                        isUploading = true;
                      });

                      // Use the outer context for provider
                      final appState = Provider.of<AppStateProvider>(
                        outerContext,
                        listen: false,
                      );

                      await AvatarService.uploadVoiceSample(
                        appState: appState,
                        voiceFile: selectedFile,
                      );

                      if (!mounted) return;

                      Navigator.pop(dialogContext);

                      CustomErrorHandler.show(
                        outerContext,
                        message: 'Voice file uploaded successfully!',
                        type: ErrorType.success,
                      );
                    } catch (e) {
                      if (!mounted) return;

                      setDialogState(() {
                        isUploading = false;
                      });

                      CustomErrorHandler.show(
                        outerContext,
                        message: e.toString(),
                        type: ErrorType.fail,
                      );
                    }
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
                onPressed: () async {
                  if (audioPath == null) {
                    CustomErrorHandler.show(
                      outerContext,
                      message: 'Please record or upload a voice sample first',
                      type: ErrorType.fail,
                    );
                    return;
                  }

                  try {
                    setDialogState(() {
                      isUploading = true;
                    });

                    // Use the outer context for provider
                    final appState = Provider.of<AppStateProvider>(
                      outerContext,
                      listen: false,
                    );

                    await AvatarService.uploadVoiceSample(
                      appState: appState,
                      voiceFile: File(audioPath!),
                    );

                    if (!mounted) return;

                    Navigator.pop(dialogContext);

                    CustomErrorHandler.show(
                      outerContext,
                      message: 'Voice sample uploaded successfully!',
                      type: ErrorType.success,
                    );
                  } catch (e) {
                    if (!mounted) return;

                    setDialogState(() {
                      isUploading = false;
                    });

                    CustomErrorHandler.show(
                      outerContext,
                      message: e.toString(),
                      type: ErrorType.fail,
                    );
                  }
                },
                text: isUploading ? 'Uploading...' : 'Save',
                buttonType: ButtonType.primary,
                isLoading: isUploading,
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
          final path = await _audioRecorder.stop();
          setDialogState(() {
            isRecording = false;
            audioPath = path;
          });
          setState(() {
            isRecording = false;
          });

          if (!mounted) return;

          CustomErrorHandler.show(
            context,
            message: 'Recording saved!',
            type: ErrorType.success,
          );
        } else {
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

            if (!mounted) return;

            CustomErrorHandler.show(
              context,
              message: 'Recording started... Tap stop to finish',
              type: ErrorType.info,
              duration: const Duration(seconds: 2),
            );
          }
        }
      } else {
        if (!mounted) return;

        CustomErrorHandler.show(
          context,
          message: 'Microphone permission denied',
          type: ErrorType.fail,
        );
      }
    } catch (e) {
      if (!mounted) return;

      CustomErrorHandler.show(
        context,
        message: 'Recording error: $e',
        type: ErrorType.fail,
      );
    }
  }

  /// Change the saved avatar photo.
  ///
  /// - Gallery pick → requires a fresh front-camera live shot to verify
  ///   identity, since the file could be of anyone.
  /// - Camera pick → the captured frame IS already a live shot, so no
  ///   second verification capture is taken; the same frame is sent as
  ///   both `photo` and `live_capture`.
  ///
  /// The picked photo is resized/compressed via [_processImage] BEFORE
  /// upload, and it's that processed file — not the raw original — that
  /// gets sent to the backend and shown locally on success.
  Future<void> _changeAvatarPhoto() async {
    try {
      // Step 1: Show source selection
      final ImageSource? source = await showDialog<ImageSource>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text(
            'Choose Photo Source',
            style: AppStyles.h2.copyWith(color: AppColors.primaryColor),
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(
                  Icons.camera_alt,
                  color: AppColors.primaryColor,
                ),
                title:  Text('Camera', style: AppStyles.h3.copyWith(color: context.textPrimary)),
                onTap: () => Navigator.pop(dialogContext, ImageSource.camera),
              ),
              ListTile(
                leading: const Icon(
                  Icons.photo_library,
                  color: AppColors.primaryColor,
                ),
                title: Text(
                  'Gallery',
                  style: AppStyles.h3.copyWith(color: context.textPrimary),
                ),
                onTap: () => Navigator.pop(dialogContext, ImageSource.gallery),
              ),
            ],
          ),
        ),
      );

      // User dismissed the dialog (tapped outside / back button) —
      // `source` is null here, so bail out instead of force-unwrapping it.
      if (source == null) return;

      final ImagePicker picker = ImagePicker();
      XFile? image;
      try {
        image = await picker.pickImage(
          source: source,
          maxWidth: 1920,
          maxHeight: 1080,
          imageQuality: 85,
        );
      } on PlatformException catch (e) {
        if (!mounted) return;
        CustomErrorHandler.show(
          context,
          message: _describeCameraError(e),
          type: ErrorType.fail,
        );
        return;
      }

      if (image == null) return;

      final pickedFile = File(image.path);

      File liveShotFile;

      if (source == ImageSource.camera) {
        // Already a live capture — no second selfie needed.
        liveShotFile = pickedFile;
      } else {
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
        XFile? liveShot;
        try {
          liveShot = await verifyPicker.pickImage(
            source: ImageSource.camera,
            preferredCameraDevice: CameraDevice.front,
            maxWidth: 1280,
            maxHeight: 720,
            imageQuality: 85,
          );
        } on PlatformException catch (e) {
          if (!mounted) return;
          CustomErrorHandler.show(
            context,
            message: _describeCameraError(e),
            type: ErrorType.fail,
          );
          return;
        }

        if (liveShot == null) {
          CustomErrorHandler.show(
            context,
            message: 'Identity verification was cancelled.',
            type: ErrorType.fail,
          );
          return;
        }

        liveShotFile = File(liveShot.path);
      }

      // Step 3: Set loading state
      if (!mounted) return;
      setState(() {
        isUploading = true;
        isLoading = true;
      });

      try {
        // Step 4: Process image — resize/compress BEFORE upload, since
        // this is what actually gets sent and kept.
        final File processedImage = await _processImage(pickedFile);

        // Step 5: Get provider
        if (!mounted) return;
        final appState = Provider.of<AppStateProvider>(context, listen: false);

        // Step 6: Upload the PROCESSED file, not the raw original.
        await AvatarService.uploadPhoto(
          appState: appState,
          photoFile: processedImage,
          liveCaptureFile: liveShotFile,
        );

        // Step 7: Update UI on success
        if (!mounted) return;
        setState(() {
          profileImage = processedImage;
        });

        CustomErrorHandler.show(
          context,
          message: 'Avatar photo uploaded successfully!',
          type: ErrorType.success,
        );
      } catch (e) {
        if (!mounted) return;

        setState(() {
          profileImage = null;
        });

        CustomErrorHandler.show(
          context,
          message: e.toString(),
          type: ErrorType.fail,
        );
      } finally {
        if (mounted) {
          setState(() {
            isUploading = false;
            isLoading = false;
          });
        }
      }
    } catch (e) {
      if (!mounted) return;

      if (isUploading) {
        setState(() {
          isLoading = false;
          isUploading = false;
        });
      }

      CustomErrorHandler.show(
        context,
        message: 'Error selecting photo: $e',
        type: ErrorType.fail,
      );
    }
  }

  Future<File> _processImage(File imageFile) async {
    try {
      final bytes = await imageFile.readAsBytes();
      img.Image? originalImage = img.decodeImage(bytes);

      if (originalImage == null) {
        throw 'Failed to decode image';
      }

      const int minDimension = 512;
      img.Image processedImage;

      if (originalImage.width < minDimension ||
          originalImage.height < minDimension) {
        processedImage = img.copyResize(
          originalImage,
          width: minDimension,
          height: minDimension,
          interpolation: img.Interpolation.cubic,
        );
      } else if (originalImage.width > 2048 || originalImage.height > 2048) {
        int targetWidth = originalImage.width;
        int targetHeight = originalImage.height;

        if (targetWidth > targetHeight) {
          targetWidth = 2048;
          targetHeight = (originalImage.height * 2048 / originalImage.width)
              .round();
        } else {
          targetHeight = 2048;
          targetWidth = (originalImage.width * 2048 / originalImage.height)
              .round();
        }

        processedImage = img.copyResize(
          originalImage,
          width: targetWidth,
          height: targetHeight,
          interpolation: img.Interpolation.cubic,
        );
      } else {
        processedImage = originalImage;
      }

      final tempDir = Directory.systemTemp;
      final tempFile = File(
        '${tempDir.path}/avatar_${DateTime.now().millisecondsSinceEpoch}.jpg',
      );
      await tempFile.writeAsBytes(img.encodeJpg(processedImage, quality: 90));

      return tempFile;
    } catch (e) {
      // If image processing fails, return original file
      print('Image processing failed: $e');
      return imageFile;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: CustomAppBar(
        title:
            "${appState.userRole == 'teacher' ? 'Teacher' : 'Student'} Profile",
        showBackButton: true,
      ),
      body:LoadingOverlay(isLoading: isLoading, child: SingleChildScrollView(
        padding: const EdgeInsets.all(AppStyles.spacingL),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(AppStyles.spacingXL),
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                boxShadow: context.cardShadow,
              ),
              child: Column(
                children: [
                  // Profile picture
                  Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: AppColors.primaryColor,
                        width: 3,
                      ),
                    ),
                    child: CircleAvatar(
                      radius: 48,
                      backgroundColor: Colors.transparent,
                      backgroundImage:
                          profileImage != null ? FileImage(profileImage!) : null,
                      child: profileImage == null
                          ? Icon(
                              Icons.person,
                              size: 50,
                              color: AppColors.primaryColor,
                            )
                          : null,
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingM),

                  // Name
                  Text(
                    userName,
                    style: AppStyles.h2.copyWith(color: context.textPrimary),
                    textAlign: TextAlign.center,
                  ),

                  const SizedBox(height: AppStyles.spacingS),
                  // Role
                  Text(
                    appState.userRole == 'teacher' ? userRole : 'Student',
                    style: AppStyles.caption.copyWith(color:context.textSecondary),
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
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                boxShadow:context.cardShadow,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Appearance',
                    style: AppStyles.h3.copyWith(color: context.textPrimary),
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  Consumer<ThemeProvider>(
                    builder: (context, themeProvider, _) {
                      return Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppStyles.spacingM,
                          vertical: AppStyles.spacingS,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(context).cardColor,
                          borderRadius: BorderRadius.circular(
                            AppStyles.radiusM,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              themeProvider.isDark
                                  ? Icons.dark_mode_outlined
                                  : Icons.light_mode_outlined,
                              color: AppColors.primaryColor,
                            ),
                            const SizedBox(width: AppStyles.spacingM),
                            Expanded(
                              child: Text(
                                themeProvider.isDark
                                    ? 'Dark Mode'
                                    : 'Light Mode',
                                style: AppStyles.bodyMedium.copyWith(color: context.textSecondary),
                              ),
                            ),
                            Switch(
                              value: themeProvider.isDark,
                              onChanged: (_) => themeProvider.toggle(),
                              trackOutlineColor: MaterialStateProperty.all(Theme.of(context).cardColor),
                              activeColor: AppColors.primaryColor,
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                  const SizedBox(width: AppStyles.spacingL),
                  if (appState.userRole == 'teacher') ...[
                    Text(
                      "Lecture Settings",
                      style: AppStyles.h3.copyWith(color: context.textPrimary),
                    ),
                    const SizedBox(height: AppStyles.spacingS),
                    CustomTextFormField(
                      prefixIcon: Icon(
                        Icons.history,
                        color: AppColors.primaryColor,
                      ),
                      hintText: 'Lecture History',
                      readOnly: true,
                      onTap: _lectureHistory,
                    ),
                  ],
                  const SizedBox(height: AppStyles.spacingL),
                  Text(
                    "Account Settings",
                    style: AppStyles.h3.copyWith(color: context.textPrimary),
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    prefixIcon: Icon(
                      Icons.lock_outline,
                      color: AppColors.primaryColor,
                    ),
                    hintText: 'Password',
                    readOnly: true,
                    suffixIcon: TextButton(
                      onPressed: _changePassword,
                      child: Text(
                        'Change',
                        style: AppStyles.h3.copyWith(
                          color: AppColors.primaryColor,
                        ),
                      ),
                    ),
                  ),
                                    const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    prefixIcon: Icon(
                      Icons.logout_sharp,
                      color: AppColors.primaryColor,
                    ),
                    hintText: 'Log out',
                    readOnly: true,
                    suffixIcon: TextButton(
                      onPressed: _logout,
                      child: Text(
                        'logout',
                        style: AppStyles.h3.copyWith(
                          color: AppColors.primaryColor,
                        ),
                      ),
                    ),
                  ),
                  if (appState.userRole == 'teacher') ...[
                    const SizedBox(height: AppStyles.spacingL),
                    Text(
                      "Avatar Settings",
                      style: AppStyles.h3.copyWith(color: context.textPrimary),
                    ),
                    const SizedBox(height: AppStyles.spacingS),
                    CustomTextFormField(
                      prefixIcon: Icon(
                        Icons.photo_camera_outlined,
                        color: AppColors.primaryColor,
                      ),
                      hintText: 'change avatar photo',
                      readOnly: true,
                      suffixIcon: TextButton(
                        onPressed: _changeAvatarPhoto,
                        child: Text(
                          'Change',
                          style: AppStyles.h3.copyWith(
                            color: AppColors.primaryColor,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: AppStyles.spacingS),
                    CustomTextFormField(
                      prefixIcon: Icon(
                        Icons.mic,
                        color: AppColors.primaryColor,
                      ),
                      hintText: 'change voice sample',
                      readOnly: true,
                      suffixIcon: TextButton(
                        onPressed: _changeVoiceSample,
                        child: Text(
                          'Change',
                          style: AppStyles.h3.copyWith(
                            color: AppColors.primaryColor,
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: AppStyles.spacingL),
                  ], // Avatar Settings Card
                ],
              ),
            ),
          ],
        ),
      ),)
    );
  }
}