import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/processing_notifier.dart';
import '../../providers/lecture_state_provider.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../providers/app_state_provider.dart';

class LectureProcessingScreen extends StatefulWidget {
  final int sessionId;
  final String lectureType; // ← add

  const LectureProcessingScreen({
    super.key,
    required this.sessionId,
    this.lectureType = 'generated', // ← default to generated
  });
  @override
  State<LectureProcessingScreen> createState() =>
      _LectureProcessingScreenState();
}

class _LectureProcessingScreenState extends State<LectureProcessingScreen>
    with TickerProviderStateMixin {
  late final AnimationController _gearController;
  late final AnimationController _progressBarController;
  late Animation<double> _progressBarAnimation;
  double _previousBarValue = 0.0;
  String _previousStepKey = '';

  late final AnimationController _fadeController;
  late final Animation<double> _fadeAnimation;

  int _dotCount = 1;
  Timer? _dotsTimer;

  @override
  void initState() {
    super.initState();

    _gearController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat();

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 350),
      value: 1.0,
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeInOut,
    );

    _progressBarController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _progressBarAnimation = Tween<double>(begin: 0.0, end: 0.0).animate(
      CurvedAnimation(parent: _progressBarController, curve: Curves.easeOut),
    );

    _dotsTimer = Timer.periodic(const Duration(milliseconds: 500), (_) {
      if (!mounted) return;
      setState(() => _dotCount = (_dotCount % 3) + 1);
    });

    // Start polling via notifier
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      Provider.of<ProcessingNotifier>(
        context,
        listen: false,
      ).startForSession(widget.sessionId, appState);
    });
  }

  void _animateProgressTo(double target) {
    _progressBarAnimation = Tween<double>(begin: _previousBarValue, end: target)
        .animate(
          CurvedAnimation(
            parent: _progressBarController,
            curve: Curves.easeOut,
          ),
        );
    _previousBarValue = target;
    _progressBarController
      ..reset()
      ..forward();
  }

  @override
  void dispose() {
    _gearController.dispose();
    _fadeController.dispose();
    _progressBarController.dispose();
    _dotsTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final dots = '.' * _dotCount;

    return Consumer<ProcessingNotifier>(
      builder: (context, notifier, _) {
        final job = notifier.job;
        // final percent = (job.progress * 100).round().clamp(0, 100);

        // Animate progress bar
        if (job.progress != _previousBarValue) {
          WidgetsBinding.instance.addPostFrameCallback(
            (_) => _animateProgressTo(job.progress),
          );
        }

        // Fade card on step change
        if (job.currentStepKey != _previousStepKey) {
          _previousStepKey = job.currentStepKey;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _fadeController.reverse().then((_) {
              if (mounted) _fadeController.forward();
            });
          });
        }
        if (job.isTerminal && _gearController.isAnimating) {
          _gearController.stop();
        }
        if (job.isTerminal) {
          _dotsTimer?.cancel();
        }

        if (job.isDone) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) {
              context
                  .read<LectureStateProvider>()
                  .clearOngoingSession();
            }
          });
        }

        return Scaffold(
          backgroundColor: Theme.of(context).scaffoldBackgroundColor,
          appBar: CustomAppBar(
            title: 'Lecture Processing',
            showBackButton: false,
          ),
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(AppStyles.spacingL),
              child: Column(
                children: [
                  const SizedBox(height: AppStyles.spacingL),

                  // Gear
                  RotationTransition(
                    turns: _gearController,
                    child: Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        color: Theme.of(context).scaffoldBackgroundColor,
                        borderRadius: BorderRadius.circular(AppStyles.radiusM),
                      ),
                      child: const Center(
                        child: Icon(
                          Icons.settings,
                          size: 44,
                          color: AppColors.primaryColor,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingXXL),

                  // Progress bar
                  AnimatedBuilder(
                    animation: _progressBarController,
                    builder: (context, _) => CustomProgressBar(
                      progress: _progressBarAnimation.value,
                      progressColor: AppColors.primaryColor,
                      height: 8,
                      showPercentage: job.progress > 0,
                      percentageStyle: AppStyles.h2.copyWith(
                        color: AppColors.primaryColor,
                      ),
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingM),

                  // Step title
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: Text(
                      job.isTerminal
                          ? job.stageTitle.isEmpty
                                ? ''
                                : 'Step ${job.currentStep} of ${job.totalSteps}: ${job.title}'
                          : job.stageTitle.isEmpty
                          ? 'Your request is being processed$dots'
                          : 'Step ${job.currentStep} of ${job.totalSteps}: ${job.title}$dots',
                      key: job.stageTitle.isEmpty
                          ? const ValueKey('processing')
                          : ValueKey(job.stageTitle),
                      style: AppStyles.h3.copyWith(
                        color: AppColors.primaryColor,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),

                  const SizedBox(height: AppStyles.spacingS),

                  // Estimated time
                  if (job.estimatedTimeLabel.isNotEmpty)
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 300),
                      child: Text(
                        'ESTIMATED TIME: ${job.estimatedTimeLabel.toUpperCase()}',
                        key: ValueKey(job.estimatedTimeLabel),
                        style: AppStyles.caption.copyWith(letterSpacing: 1.2),
                        textAlign: TextAlign.center,
                      ),
                    ),

                  const SizedBox(height: AppStyles.spacingXL),

                  // Stage card
                  FadeTransition(
                    opacity: _fadeAnimation,
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      decoration: BoxDecoration(
                        color: Theme.of(context).cardColor,
                        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                        boxShadow: AppStyles.cardShadow,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            _iconForStep(job.currentStepKey),
                            size: 22,
                            color: AppColors.primaryColor,
                          ),
                          const SizedBox(width: AppStyles.spacingM),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Text(job.stageTitle, style: AppStyles.h3),
                                // const SizedBox(height: AppStyles.spacingS),
                                if (job.stageDescription.isNotEmpty)
                                  Text(
                                    job.stageDescription,
                                    style: AppStyles.bodyMedium.copyWith(
                                      color: AppColors.textLight,
                                      height: 1.5,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  if (job.errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(top: AppStyles.spacingM),
                      child: Text(
                        job.errorMessage!,
                        style: AppStyles.bodySmall.copyWith(
                          color: AppColors.error,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),

                  const Spacer(),
                  CustomButton(
                    text: 'Back to Dashboard',
                    fullWidth: true,
                    buttonType: ButtonType.primary,
                    onPressed: () => Navigator.pushNamed(
                      context,
                      AppRoutes.teacherDashboard,
                    ),
                  ),

                  // Review / View button on awaiting approval or done
                  // if (job.isAwaitingApproval || job.isDone)
                  //   Padding(
                  //     padding: const EdgeInsets.only(
                  //       bottom: AppStyles.spacingM,
                  //     ),
                  //     child: CustomButton(
                  //       text: job.isAwaitingApproval
                  //           ? 'Review Lecture'
                  //           : 'View Lecture',
                  //       fullWidth: true,
                  //       onPressed: ()=>Navigator.pushNamed(context, AppRoutes.lecturepreview)),
                  //     ),
                  // if (widget.lectureType == 'generated') ...[
                    if (job.isAwaitingApproval) ...[
                      const SizedBox(height: AppStyles.spacingM),
                      CustomButton(
                        text: 'Review Lecture',
                        fullWidth: true,
                        buttonType: ButtonType.secondary,
                        onPressed: () => Navigator.pushNamed(
                          context,
                          AppRoutes.lecturepreview,
                          arguments: false,
                         // draft review
                        ),
                      ),
                    ] else if (job.isDone) ...[
                      const SizedBox(height: AppStyles.spacingM),
                      CustomButton(
                        text: 'View Content',
                        fullWidth: true,
                        buttonType: ButtonType.secondary,
                        onPressed: () => Navigator.pushNamed(
                          context,
                          AppRoutes.lecturepreview,
                          arguments: true, // content ready
                        ),
                      ),
                    ],
                  // ] 
                //   else if (widget.lectureType == 'prepared' &&
                //       job.isDone) ...[
                //     const SizedBox(height: AppStyles.spacingM),
                //     CustomButton(
                //       text: 'Schedule Lecture',
                //       fullWidth: true,
                //       buttonType: ButtonType.secondary,
                //       onPressed: () => Navigator.pushNamedAndRemoveUntil(
                //         context,
                //         AppRoutes.lectureSetup,
                //         (route) =>
                //             route.settings.name == AppRoutes.teacherDashboard,
                //       ),
                //     ),
                //   ],
                //   const SizedBox(height: AppStyles.spacingL),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  IconData _iconForStep(String stepKey) {
    switch (stepKey) {
      case 'starting':
        return Icons.hourglass_empty_outlined;
      case 'generating_lecture':
        return Icons.description_outlined;
      case 'awaiting_approval':
        return Icons.rate_review_outlined;
      case 'regenerating':
        return Icons.refresh_outlined;
      case 'generating_content':
        return Icons.format_list_bulleted_outlined;
      case 'done':
        return Icons.check_circle_outline;
      case 'failed':
        return Icons.error_outline;
      default:
        return Icons.settings_outlined;
    }
  }

  // void _handlepreview() async {
  //   final appState = Provider.of<AppStateProvider>(context, listen: false);
  //   final lectureState = Provider.of<LectureStateProvider>(
  //     context,
  //     listen: false,
  //   );
  //   try {
  //     final response = await LectureService.getLecturePdfBytes(
  //       lectureState.sessionId,
  //       appState,
  //     );
  //     Navigator.pushNamed(context, AppRoutes.lecturepreview, arguments:response);
  //   } catch (e) {}
  // }
}
