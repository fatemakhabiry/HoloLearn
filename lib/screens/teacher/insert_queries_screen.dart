import 'dart:io';
import 'dart:async';
import 'package:provider/provider.dart';
import 'package:flutter/material.dart';

import '../../utils/storage_helper.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../models/lecture_models.dart';
import '../../services/lecture_service.dart';
import '../../state/providers/app_state_provider.dart';
import '../../state/providers/lecture_state_provider.dart';
import '../../state/providers/resource_state_provider.dart';

class InsertQueriesScreen extends StatefulWidget {
  const InsertQueriesScreen({super.key});

  @override
  State<InsertQueriesScreen> createState() => _InsertQueriesScreenState();
}

class _InsertQueriesScreenState extends State<InsertQueriesScreen> {
  List<ResourceItem> resources = [];
  final _formKey = GlobalKey<FormState>();
  late List<TextEditingController> _controllers;

  bool isFetchingResources = true;
  bool isGenerating = false;
  String? error_message;

  @override
  void initState() {
    super.initState();
    // Use addPostFrameCallback so context is available
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadResources());
  }

  void _loadResources() {
    final resourceProvider = Provider.of<ResourceStateProvider>(
      context,
      listen: false,
    );

    setState(() {
      resources = List<ResourceItem>.from(resourceProvider.allResources);
      _controllers = resources
          .map((r) => TextEditingController(text: r.query))
          .toList();
      isFetchingResources = false;
    });
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  void _deleteResource(int index) {
    final resourceProvider = Provider.of<ResourceStateProvider>(
      context,
      listen: false,
    );

    resourceProvider.removeAt(index);

    setState(() {
      resources.removeAt(index);
      _controllers[index].dispose();
      _controllers.removeAt(index);
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  IconData _iconForType(String type) {
    switch (type) {
      case 'pdf':
        return Icons.picture_as_pdf;
      case 'pptx':
        return Icons.slideshow;
      case 'video':
        return Icons.video_file;
      case 'url':
        return Icons.link;
      default:
        return Icons.image;
    }
  }

  Color _colorForType(String type) {
    switch (type) {
      case 'pdf':
        return const Color(0xFFE53935);
      case 'pptx':
        return const Color(0xFFFF8F00);
      case 'image':
        return const Color.fromARGB(255, 202, 187, 48);
      case 'url':
        return const Color(0xFF43A047);
      default:
        return AppColors.primaryColor;
    }
  }

  String _labelForType(String type) {
    switch (type) {
      case 'pdf':
        return 'EXTRACTION INSTRUCTIONS';
      case 'pptx':
        return 'FOCUS AREAS';
      case 'image':
        return 'IMAGE CAPTION';
      case 'video':
        return 'VIDEO QUERY';
      case 'url':
        return 'URL QUERY';
      default:
        return 'QUERY';
    }
  }

  String _hintForType(String type) {
    switch (type) {
      case 'pdf':
        return 'e.g. Take from page 10 to 15';
      case 'pptx':
        return 'e.g. Focus on the Sustainability section';
      default:
        return 'e.g. Describe the diagram in this image';
    }
  }

  String _formatSize(int? bytes) {
    if (bytes == null) return '';
    if (bytes < 1024 * 1024) {
      return '${(bytes / 1024).toStringAsFixed(1)} KB';
    }
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  // ── Actions ──────────────────────────────────────────────────────────────

  Future<void> _handleGenerate() async {
    // Sync typed queries back into resource objects
    for (int i = 0; i < resources.length; i++) {
      resources[i].query = _controllers[i].text.trim();
    }

    // final resourceProvider = Provider.of<ResourceStateProvider>(
    //   context,
    //   listen: false,
    // );
    final appState = Provider.of<AppStateProvider>(context, listen: false);
    final lectureState = Provider.of<LectureStateProvider>(
      context,
      listen: false,
    );

    setState(() => isGenerating = true);

    try {
      final lectureResources = resources
          .map(
            (r) => LectureResource(
              resourceExtension: r.resourceType,
              filePath: r.filePath,
              query: r.query,
            ),
          )
          .toList();

      final response = await LectureService.startSession(
        StartSessionRequest(
          title: lectureState.lectureTitle,
          courseCode: lectureState.courseCode,
          resources: lectureResources,
        ),
        appState,
      );
      print('Response: $response');
      print("5rgt mlservice");

      lectureState.setSessionId(response.sessionId);
      lectureState.setLectureId(response.lectureId);
      lectureState.setLectureType('generated');

      await StorageHelper.saveLectureSessionId(
        response.lectureId,
        response.sessionId,
      );
      await StorageHelper.saveLectureType(response.lectureId, 'generated');
      if (!mounted) return;
      Navigator.pushNamed(
        context,
        AppRoutes.lectureprocessing,
        arguments: {
          'sessionId': lectureState.sessionId,
          'lectureType': 'generated',
        },
      );
    } on SocketException {
      error_message = 'No internet connection.';
    } on TimeoutException {
      error_message = 'Request timed out.';
    } on ApiException catch (e) {
      error_message = e.message;
    } catch (e) {
      error_message = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (error_message != null && mounted) {
        print(error_message);
        CustomErrorHandler.show(
          context,
          message: error_message!,
          type: ErrorType.fail,
        );
        error_message = null;
      }
      if (mounted) setState(() => isGenerating = false);
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: const CustomAppBar(title: "Insert Queries", showBackButton: true),
      body: LoadingOverlay(
        isLoading: isFetchingResources || isGenerating,
        child: Center(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // ── Scrollable content ─────────────────────────────────────
              Expanded(
                child: RefreshIndicator(
                  onRefresh: () async => _loadResources(),
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(AppStyles.spacingL),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // ── Heading ──────────────────────────────────────
                        Text(
                          'Specify your\nlecture\nrequirements',
                          style: AppStyles.h1,
                        ),
                        const SizedBox(height: AppStyles.spacingS),
                        Container(
                          width: 48,
                          height: 3,
                          decoration: BoxDecoration(
                            color: AppColors.primaryColor,
                            borderRadius: BorderRadius.circular(
                              AppStyles.radiusPill,
                            ),
                          ),
                        ),
                        const SizedBox(height: AppStyles.spacingL),

                        // ── Empty state ───────────────────────────────────
                        if (resources.isEmpty)
                          Center(
                            child: Padding(
                              padding: const EdgeInsets.symmetric(
                                vertical: AppStyles.spacingXXL,
                              ),
                              child: Text(
                                'No resources found.\nGo back and upload files.',
                                textAlign: TextAlign.center,
                                style: AppStyles.bodyMedium.copyWith(
                                  color: AppColors.gray,
                                ),
                              ),
                            ),
                          ),
                        Form(
                          key: _formKey,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              // ── Resource cards ────────────────────────────────
                              ...resources.asMap().entries.map((entry) {
                                final index = entry.key;
                                final resource = entry.value;
                                final typeColor = _colorForType(
                                  resource.resourceType,
                                );

                                return Padding(
                                  padding: const EdgeInsets.only(
                                    bottom: AppStyles.spacingM,
                                  ),
                                  child: Container(
                                    padding: const EdgeInsets.all(
                                      AppStyles.spacingL,
                                    ),
                                    decoration: BoxDecoration(
                                      color: AppColors.white,
                                      borderRadius: BorderRadius.circular(
                                        AppStyles.radiusXL,
                                      ),
                                      boxShadow: AppStyles.cardShadow,
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        // File info row
                                        Row(
                                          children: [
                                            Container(
                                              width: 48,
                                              height: 48,
                                              decoration: BoxDecoration(
                                                color: typeColor.withOpacity(
                                                  0.12,
                                                ),
                                                borderRadius:
                                                    BorderRadius.circular(
                                                      AppStyles.radiusM,
                                                    ),
                                              ),
                                              child: Icon(
                                                _iconForType(
                                                  resource.resourceType,
                                                ),
                                                color: typeColor,
                                                size: 24,
                                              ),
                                            ),
                                            const SizedBox(
                                              width: AppStyles.spacingM,
                                            ),
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment:
                                                    CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    resource.fileName,
                                                    style: AppStyles.bodyMedium
                                                        .copyWith(
                                                          fontWeight:
                                                              AppFonts.semiBold,
                                                        ),
                                                    overflow:
                                                        TextOverflow.ellipsis,
                                                  ),
                                                  const SizedBox(height: 2),
                                                  Text(
                                                    resource.fileSize != null
                                                        ? 'Added just now • ${_formatSize(resource.fileSize)}'
                                                        : 'Added just now',
                                                    style: AppStyles.caption,
                                                  ),
                                                ],
                                              ),
                                            ),
                                            const SizedBox(
                                              width: AppStyles.spacingL,
                                            ),
                                            IconButton(
                                              onPressed: () {
                                                _deleteResource(index);
                                              },
                                              icon: const Icon(
                                                Icons.delete_outline,
                                                color: AppColors.primaryColor,
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(
                                          height: AppStyles.spacingM,
                                        ),

                                        // Query label
                                        Text(
                                          _labelForType(resource.resourceType),
                                          style: AppStyles.labelStyle.copyWith(
                                            fontWeight: AppFonts.bold,
                                            fontSize: AppFonts.fontSizeXS,
                                            letterSpacing: 1.2,
                                          ),
                                        ),
                                        const SizedBox(
                                          height: AppStyles.spacingS,
                                        ),

                                        // Query field
                                        CustomTextFormField(
                                          controller: _controllers[index],
                                          maxLines: 2,
                                          isFieldRequired: true,
                                          hintText: _hintForType(
                                            resource.resourceType,
                                          ),
                                          validator: (value) {
                                            if (value == null ||
                                                value.trim().isEmpty) {
                                              return 'This field cannot be empty';
                                            }
                                            return null;
                                          },
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                        const SizedBox(height: AppStyles.spacingXXL),
                        CustomButton(
                          text: 'GENERATE LECTURE',
                          fullWidth: true,
                          prefixIcon: Icon(
                            Icons.auto_awesome_outlined,
                            color: AppColors.white,
                          ),
                          onPressed: resources.isEmpty
                              ? () {}
                              : _handleGenerate,
                        ),
                      ],
                    ),
                  ),
                ),
              ),

              // ── S
            ],
          ),
        ),
      ),
    );
  }
}
