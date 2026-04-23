import 'package:flutter/material.dart';
import 'package:hololearn/services/storage_service.dart';
import 'package:hololearn/utils/storage_helper.dart';
import 'package:provider/provider.dart';

import '../../services/local_file_service.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/lecture_service.dart';
import '../../state/providers/app_state_provider.dart';
import '../../state/providers/lecture_state_provider.dart';

class RefineContentScreen extends StatefulWidget {
  const RefineContentScreen({Key? key});

  @override
  State<RefineContentScreen> createState() => _RefineContentScreenState();
}

class _RefineContentScreenState extends State<RefineContentScreen> {
  final TextEditingController _feedbackController = TextEditingController();
  final List<String> quickSuggestions = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _getsuggestions();
  }

  void dispose() {
    _feedbackController.dispose();
    super.dispose();
  }

  Future<void> _submitFeedback() async {
    if (_feedbackController.text.isNotEmpty) {
      setState(() => _isLoading = true);

      final feedback = _feedbackController.text.trim();
      final appState = context.read<AppStateProvider>();
      final lectureState = context.read<LectureStateProvider>();

      try {
        await LectureService.rejectWithFeedback(
          appState,
          lectureState.sessionId,
          feedback,
        );

        if (!mounted) return;

        Navigator.pushNamed(
          context,
          AppRoutes.lectureprocessing,
          arguments: {
            'sessionId': lectureState.sessionId,
            'lectureType': 'generated',
          },
        );
      } catch (e) {
        if (mounted) {
          CustomErrorHandler.show(
            context,
            message: 'Failed to submit feedback. Please try again.',
            type: ErrorType.fail,
            duration: const Duration(seconds: 4),
          );
        }
      } finally {
        if (mounted) {
          setState(() => _isLoading = false);
        }
      }
    } else {
      CustomErrorHandler.show(
        context,
        message: 'Feedback cannot be empty',
        type: ErrorType.fail,
        duration: const Duration(seconds: 4),
      );
    }
  }

  void _deleteLecture() async {
    setState(() {
      _isLoading = true;
    });
    final appState = context.read<AppStateProvider>();
    final lectureState = context.read<LectureStateProvider>();
    try {
      LectureService.deleteLecture(
        appState: appState,
        lectureId: lectureState.lectureId,
      );
      // Handle lecture deletion
      print('Lecture deleted');

      LocalFileService.clearLecture(lectureState.lectureId);
      await StorageHelper.clearLectureSessionId(lectureState.lectureId);
      await StorageHelper.clearLectureType(lectureState.lectureId);

      setState(() {
        _isLoading = false;
      }); // Refresh data after deletion
      CustomErrorHandler.show(
        context,
        message: 'Lecture deleted successfully.',
        type: ErrorType.success,
        duration: const Duration(seconds: 4),
      );
      Navigator.pushNamedAndRemoveUntil(
        context,
        AppRoutes.teacherDashboard,
        (route) => false,
      );
    } catch (e) {
      print('Error deleting lecture: $e');
      setState(() {
        _isLoading = false;
      });
      CustomErrorHandler.show(
        context,
        message: 'Failed to delete lecture. Please try again.',
        type: ErrorType.fail,
        duration: const Duration(seconds: 4),
      );
    }
  }

  void _addQuickSuggestion(String prompt) {
    setState(() {
      _feedbackController.text +=
          (_feedbackController.text.isEmpty ? "" : '\t') + prompt;

      _feedbackController.selection = TextSelection.fromPosition(
        TextPosition(offset: _feedbackController.text.length),
      );
    });
  }

  Future<void> _getsuggestions() async {
    setState(() => _isLoading = true);

    try {
      List<String> suggestions = await LectureService.getFeedbackSuggestions(
        context.read<AppStateProvider>(),
        context.read<LectureStateProvider>().sessionId,
      );

      setState(() {
        quickSuggestions.clear();
        quickSuggestions.addAll(suggestions);
      });
    } catch (e) {
      print('Error getting suggestions: $e');
      CustomErrorHandler.show(
        context,
        message: 'Failed to get suggestions. Please try again.',
        type: ErrorType.fail,
        duration: const Duration(seconds: 4),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: "Refine Content", showBackButton: true),
      body: LoadingOverlay(
        isLoading: _isLoading,
        child: Center(
          child: RefreshIndicator(
            onRefresh: _getsuggestions,
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppStyles.spacingL),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "EDITOR MODE",
                    style: AppStyles.bodyMedium.copyWith(
                      color: AppColors.primaryColor,
                    ),
                  ),
                  const SizedBox(height: AppStyles.spacingM),

                  Text("Improve your lesson material", style: AppStyles.h1),
                  const SizedBox(height: AppStyles.spacingS),
                  Text(
                    "Provide specific feedback to adjust the complexity, tone, or specific examples used in the generated educational content.",
                    style: AppStyles.labelStyle.copyWith(color: AppColors.gray),
                  ),
                  const SizedBox(height: AppStyles.spacingL),
                  Text(
                    "YOUR FEEDBACK",
                    style: AppStyles.bodyMedium.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  CustomTextFormField(
                    controller: _feedbackController,
                    maxLines: 6,
                    isFieldRequired: true,
                    hintText:
                        """Enter your feedback here to \nimprove the generated content..""",
                    validator: (value) => value == null || value.isEmpty
                        ? "Feedback cannot be empty"
                        : null,
                  ),

                  const SizedBox(height: AppStyles.spacingS),
                  Row(
                    children: [
                      Icon(
                        Icons.lightbulb_outline_rounded,
                        size: 40,
                        color: AppColors.primaryColor,
                      ),
                      const SizedBox(width: AppStyles.spacingXS),
                      Text(
                        "Quick Suggestions",
                        style: AppStyles.bodyMedium.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppStyles.spacingS),

                  Wrap(
                    spacing: AppStyles.spacingS,
                    runSpacing: AppStyles.spacingS,
                    children: quickSuggestions.map((suggestion) {
                      return GestureDetector(
                        onTap: () => _addQuickSuggestion(suggestion),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppStyles.spacingM,
                            vertical: AppStyles.spacingS,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.gray.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(
                              AppStyles.radiusM,
                            ),
                            boxShadow: AppStyles.cardShadow,
                          ),
                          child: Text(suggestion, style: AppStyles.bodyMedium),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: AppStyles.spacingL),
                  CustomButton(
                    text: "Add Feedback & Regenerate",
                    fullWidth: true,
                    prefixIcon: Icon(
                      Icons.auto_awesome_outlined,
                      size: 20,
                      color: AppColors.white,
                    ),

                    onPressed: _submitFeedback,
                  ),
                  const SizedBox(height: AppStyles.spacingS),
                  CustomButton(
                    buttonType: ButtonType.secondary,
                    text: "Delete",
                    fullWidth: true,
                    prefixIcon: Icon(
                      Icons.delete_outline,
                      size: 20,
                      color: AppColors.primaryColor,
                    ),
                    onPressed: _deleteLecture,
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
