import 'dart:io';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';

import '../../services/biometric_service.dart';
import '../../utils/storage_helper.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/course_service.dart';
import '../../services/lecture_service.dart';
import '../../providers/app_state_provider.dart';
import '../../providers/lecture_state_provider.dart';
import '../../providers/resource_state_provider.dart';

class CreateNewLectureScreen extends StatefulWidget {
  const CreateNewLectureScreen({super.key});

  @override
  State<CreateNewLectureScreen> createState() => _CreateNewLectureScreenState();
}

class _CreateNewLectureScreenState extends State<CreateNewLectureScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  // Form values
  String? lectureTitle;
  String? courseCode;
  String selectedInputType = 'prepared';

  // URL controllers — fixed size, pre-initialized
  final List<TextEditingController> _urlControllers = [
    TextEditingController(),
    TextEditingController(),
  ];
  final List<String> _lectureUrls = ['', ''];
  bool _showSecondUrl = false;

  // File state
  List<PlatformFile> _selectedFiles = [];
  final FileUploadController _fileUploadController = FileUploadController();

  // UI state
  bool _isLoading = false;
  bool _isFetchingCourses = true;
  bool _showBanner = false;
  bool _isSuccess = false;
  String _bannerMessage = '';
  List<String> _courseItems = [];

  // ─── Lifecycle ────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _fetchCourseCodes();
  }

  @override
  void dispose() {
    for (final c in _urlControllers) {
      c.dispose();
    }
    super.dispose();
  }

  // ─── Data fetching ────────────────────────────────────────────────────────

  Future<void> _fetchCourseCodes() async {
    setState(() => _isFetchingCourses = true);
    try {
      final appState = context.read<AppStateProvider>();
      final courses = await CourseService.fetchCourseCodes(appState);
      if (!mounted) return;
      setState(() => _courseItems = courses);
    } on SocketException {
      _showError('No internet connection.');
    } on TimeoutException {
      _showError('Request timed out.');
    } catch (e) {
      _showError(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _isFetchingCourses = false);
    }
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  void _showError(String message) {
    if (!mounted) return;
    CustomErrorHandler.show(context, message: message, type: ErrorType.fail);
  }

  void _resetInputState() {
    _selectedFiles = [];
    _fileUploadController.reset();
    for (final c in _urlControllers) {
      c.clear();
    }
    _lectureUrls.fillRange(0, _lectureUrls.length, '');
    _showSecondUrl = false;
  }

  // ─── Validation ───────────────────────────────────────────────────────────

  bool _validateInputs() {
    if (!_formKey.currentState!.validate()) {
      setState(() {
        _showBanner = true;
        _isSuccess = false;
        _bannerMessage = 'Please fill all required fields correctly!';
      });
      return false;
    }

    final hasFile = _selectedFiles.isNotEmpty;
    final hasUrl = _urlControllers.any(
      (controller) => controller.text.trim().isNotEmpty,
    );

    if (selectedInputType == 'prepared' && !hasFile) {
      _showError('Please upload a file for the prepared lecture.');
      return false;
    }

    if (selectedInputType == 'generated' && !hasFile && !hasUrl) {
      _showError('Please upload at least one file or provide a URL.');
      return false;
    }

    return true;
  }

  Future<void> _handlePreparedFlow() async {
    final appState = context.read<AppStateProvider>();
    final lectureState = context.read<LectureStateProvider>();
    final lectureResponse = await LectureService.createLectureDraft(
      appState: appState,
      title: lectureTitle!,
      courseCode: courseCode!,
      filePath: _selectedFiles.first.path!,
    );
    appState.setLectureId(lectureResponse.lectureId);

    // Start prepared session to get sessionId
    final sessionResponse = await LectureService.startPreparedSession(
      appState,
      lectureResponse.lectureId,
    );
    lectureState.startOngoingSession(sessionResponse.sessionId);
    lectureState.setLectureId(appState.lectureId);
    lectureState.setLectureType('prepared');

    // ← Save the mapping for both types
    await StorageHelper.saveLectureSessionId(
      lectureResponse.lectureId,
      sessionResponse.sessionId,
    );
    await StorageHelper.saveOngoingSessionId(sessionResponse.sessionId);
    await StorageHelper.saveLectureType(lectureResponse.lectureId, 'prepared');

    if (!mounted) return;
    Navigator.pushNamed(
      context,
      AppRoutes.lectureprocessing,
      arguments: {
        'sessionId': lectureState.ongoingSessionId,
        'lectureType': 'prepared',
      },
    );

    // await AvatarService.checkAvatarStatus(appState);
    // if (!mounted) return;
    // Navigator.pushNamed(
    //   context,
    //   // appState.isFirstTimeLogin
    //   //     ?
    //   AppRoutes.createAvatar,
    //   // : AppRoutes.lectureSetup,
    // );
  }

  void _handleGeneratedFlow() {
    final resourceProvider = Provider.of<ResourceStateProvider>(
      context,
      listen: false,
    );
    final lectureState = Provider.of<LectureStateProvider>(
      context,
      listen: false,
    );
    lectureState.setLectureTitle(lectureTitle!);
    lectureState.setCourseCode(courseCode!);
    lectureState.setLectureType('generated');

    final items = [
      ..._selectedFiles.map(
        (f) => ResourceItem(
          fileName: f.name,
          filePath: f.path ?? '',
          fileSize: f.size,
          resourceType: ResourceItem.typeFromExtension(f.name),
        ),
      ),
      ..._lectureUrls
          .where((url) => url.trim().isNotEmpty)
          .map(
            (url) =>
                ResourceItem(fileName: url, filePath: url, resourceType: 'url'),
          ),
    ];

    resourceProvider.clear();
    try {
      resourceProvider.setResources(
        resources: items,
        lectureTitle: lectureTitle!,
        courseCode: courseCode!,
      );

      Navigator.pushNamed(context, AppRoutes.insertQueries);
    } catch (e) {
      _showError(e.toString().replaceFirst("Exception: ", ""));
      print(e);
    }
  }

  Future<void> _handleNext() async {
    if (!_validateInputs()) return;
    _formKey.currentState!.save();
    setState(() => _isLoading = true);
    final available = await BiometricService.isAvailable();
    if (available) {
      try {
        final authenticated = await BiometricService.authenticate(
          reason: 'Authenticate to generate this lecture',
        );
        if (!authenticated) {
          if (mounted)
            setState(() => _isLoading = false); //  reset before returning
          return;
        }
      } on BiometricException catch (e) {
        if (mounted) {
          setState(() => _isLoading = false);
          CustomErrorHandler.show(
            context,
            message: e.message,
            type: ErrorType.fail,
          );
        }
        return;
      }
    }
    try {
      if (selectedInputType == 'prepared') {
        await _handlePreparedFlow();
      } else {
        _handleGeneratedFlow();
      }
    } on http.ClientException {
      _showError('Cannot connect to server.');
    } on SocketException {
      _showError('No internet connection.');
    } on TimeoutException {
      _showError('Request timed out.');
    } catch (e) {
      _showError(e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // ─── File selection ───────────────────────────────────────────────────────

  void _onFilesSelected(List<PlatformFile> files) {
    if (files.isEmpty) return;

    if (selectedInputType == 'prepared' && files.length > 1) {
      _showError('Only one file is allowed for prepared lectures.');
      setState(() => _selectedFiles = [files.first]);
    } else {
      setState(() => _selectedFiles = files);
    }
  }

  // ─── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      resizeToAvoidBottomInset: true,
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: const CustomAppBar(title: 'Create Lecture', showBackButton: true),
      body: LoadingOverlay(
        isLoading: _isLoading,
        child: Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.all(AppStyles.spacingL),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 600),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildInputTypeSelector(),
                      const SizedBox(height: AppStyles.spacingL),
                      _buildFileUpload(
                        selectedInputType == 'generated' ? true : false,
                      ),
                      const SizedBox(height: AppStyles.spacingL),
                      if (selectedInputType == 'generated') ...[
                        _buildUrlSection(),
                        const SizedBox(height: AppStyles.spacingL),
                      ],
                      _buildLectureDetails(),
                      if (_showBanner) ...[
                        const SizedBox(height: AppStyles.spacingL),
                        MessageDisplay(
                          isSuccess: _isSuccess,
                          massegeBanner: _isSuccess
                              ? 'Lecture Created Successfully'
                              : 'Creation Failed',
                          message: _bannerMessage,
                          onDismiss: () => setState(() => _showBanner = false),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ─── Section widgets ──────────────────────────────────────────────────────

  Widget _buildInputTypeSelector() {
    return _card(
      child: RadioOptionsGroup(
        sectionTitle: 'LECTURE CONTENT INPUT TYPE',
        selectedId: selectedInputType,
        options: LectureInputOptions.options,
        onOptionSelected: (id) {
          _resetInputState();
          setState(() => selectedInputType = id);
        },
      ),
    );
  }

  Widget _buildFileUpload(bool allowMultiple) {
    return FileUploadWidget(
      controller: _fileUploadController,
      label: 'Lecture Content',
      supportedFormats: const [
        'pdf',
        'pptx',
        'ppt',
        'jpg',
        'jpeg',
        'png',
        'gif',
        'webp',
        'mp4',
        'mov',
        'avi',
        'mkv',
        'webm',
        'mpeg',
      ],
      isRequired: selectedInputType == 'prepared',
      headerText: 'DRAG & DROP OR BROWSE FILES',
      subheaderText:
          'PDF, PPTX, PPT, JPG, JPEG, PNG, GIF, WEBP, MP4, MOV, AVI, MKV, WEBM, MPEG',
      onFilesSelected: _onFilesSelected,
      allowMultiple: allowMultiple,
    );
  }

  Widget _buildUrlSection() {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          _buildUrlField(index: 0, label: 'Content URL'),
          if (_showSecondUrl) ...[
            const SizedBox(height: AppStyles.spacingS),
            _buildUrlField(index: 1, label: 'Content URL'),
          ] else
            IconButton(
              onPressed: () => setState(() => _showSecondUrl = true),
              icon: const Icon(
                Icons.add_circle_outline_sharp,
                color: AppColors.primaryColor,
                size: 30,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildUrlField({required int index, required String label}) {
    return CustomTextFormField(
      controller: _urlControllers[index],
      hintText: 'https://example.com/lecture-content',
      label: label,
      isFieldRequired: false,
      keyboardType: TextInputType.url,
      prefixIcon: const Icon(Icons.link),
      validator: (value) {
        if (value == null || value.isEmpty) return null;
        if (!value.startsWith('http://') && !value.startsWith('https://')) {
          return 'Please enter a valid URL';
        }
        return null;
      },
      onSaved: (value) => _lectureUrls[index] = value ?? '',
    );
  }

  Widget _buildLectureDetails() {
    return _card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'LECTURE DETAILS',
            style: AppStyles.labelStyle.copyWith(
              fontWeight: AppFonts.bold,
              fontSize: AppFonts.fontSizeXS,
              letterSpacing: 1.2,
              color: context.textPrimary,
            ),
          ),
          const SizedBox(height: AppStyles.spacingM),
          CustomTextFormField(
            hintText: 'Enter Lecture Title',
            label: 'Lecture Title',
            keyboardType: TextInputType.text,
            validator: (value) => (value == null || value.isEmpty)
                ? 'Lecture title is required'
                : null,
            onSaved: (value) => lectureTitle = value,
          ),
          const SizedBox(height: AppStyles.spacingL),
          CustomDropdown(
            label: _courseItems.isEmpty
                ? 'No course available'
                : 'Select Course Code',
            items: _courseItems,
            onChanged: (value) => setState(() => courseCode = value),
            validator: (value) => (value == null || value.isEmpty)
                ? 'Course code is required'
                : null,
          ),
          const SizedBox(height: AppStyles.spacingL),
          CustomButton(
            text: selectedInputType == 'prepared'
                ? 'AVATAR OPTIONS & SCHEDULING'
                : 'NEXT:INSERT RESOURCES QUERIES',
            fullWidth: true,
            onPressed: _handleNext,
          ),
        ],
      ),
    );
  }

  // ─── Shared card decorator ────────────────────────────────────────────────

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
}
