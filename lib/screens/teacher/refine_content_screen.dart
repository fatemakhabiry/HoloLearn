import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

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

    // Populate quick suggestions (prompts that will be sent to the API)
    quickSuggestions.addAll([
      "Make it more engaging and fun",
      "Simplify the language for beginners",
      "Add more real-life examples",
      "Make the tone more professional",
      "Add more visual descriptions",
      "Include practice questions",
      "Make explanations shorter",
      "Focus more on key concepts",
    ]);
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

  void _deleteLecture() {
    // Handle lecture deletion
    print('Lecture deleted');
    LectureService.deleteLecture(appState: context.read<AppStateProvider>(), lectureId: context.read<LectureStateProvider>().lectureId);
  }

  Future<void> _addQuickSuggestion(String prompt) async {
    // Show loading indicator if needed
    setState(() => _isLoading = true);

    try {
      // Simulate API call delay
      // await Future.delayed(const Duration(milliseconds: 1200));

      // Simulated API response - You can replace this with real API call later
      List<String> suggestions = await LectureService.getFeedbackSuggestions(
        context.read<AppStateProvider>(),
        context.read<LectureStateProvider>().sessionId,
      );

      // Add all suggestions to the feedback
      for (String suggestion in suggestions) {
        if (suggestion.isNotEmpty) {
          _feedbackController.text +=
              (_feedbackController.text.isEmpty ? "" : "\n\n") + suggestion;
        }
      }

      // Move cursor to the end
      _feedbackController.selection = TextSelection.fromPosition(
        TextPosition(offset: _feedbackController.text.length),
      );
    } catch (e) {
      print('Error getting suggestions: $e');
      // You can show a snackbar here
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Simulated API function
  Future<String> _getSuggestionsFromApi(String prompt) async {
    // In real app, this would be your actual API call (http, dio, etc.)

    // Fake delay + response based on prompt
    await Future.delayed(const Duration(milliseconds: 800));

    // Default generic suggestions
    return "prompt";
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: "Refine Content", showBackButton: true),
      body: SingleChildScrollView(
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
              style: AppStyles.bodyMedium.copyWith(fontWeight: FontWeight.bold),
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
                      borderRadius: BorderRadius.circular(AppStyles.radiusM),
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
    );
  }
}
