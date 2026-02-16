import 'package:flutter/material.dart';
import 'package:hololearn/routes/app_routes.dart';
import 'package:hololearn/services/lecture_service.dart';
import 'package:provider/provider.dart';
import '../state/providers/app_state_provider.dart';
import '../state/providers/lecture_state_provider.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/confirmation_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../models/schedule_models.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';
import '../services/schedule_service.dart';

class TeacherLecturesScreen extends StatefulWidget {
  const TeacherLecturesScreen({super.key});

  @override
  State<TeacherLecturesScreen> createState() => _TeacherLecturesScreenState();
}

class _TeacherLecturesScreenState extends State<TeacherLecturesScreen> {
  List<ScheduleSlot> myLectures = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    loadTokenAndFetchData();
  }

  Future<void> fetchData() async {
    final appState = Provider.of<AppStateProvider>(context, listen: false);

    setState(() {
      isLoading = true;
    });

    try {
      // Fetch lectures using the token - backend identifies teacher from token
      final lecturesData = await ScheduleService.fetchMyLectureHistory(
        appState,
      );

      if (!mounted) return;

      setState(() {
        myLectures = lecturesData;
        isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message:
              'Failed to load lectures: ${e.toString().replaceAll('Exception: ', '')}',
          type: ErrorType.fail,
        );
      }
      setState(() {
        isLoading = false;
      });
    }
  }

  Future<void> loadTokenAndFetchData() async {
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      if (appState.accessToken.isEmpty) {
        throw Exception('No authentication token found. Please login again.');
      }

      await fetchData();
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Authentication error: ${e.toString()}',
          type: ErrorType.fail,
        );
      }
      setState(() {
        isLoading = false;
      });
    }
  }

  void _handleDelete(int index) {
    CustomConfirmationDialog.show(
      context,
      title: 'Delete Lecture',
      message:
          'Are you sure you want to delete this lecture along with all its saved data?',
      confirmButtonText: 'Yes, Delete',
      cancelButtonText: 'No',
      onConfirm: () {
        try {
          final appState = Provider.of<AppStateProvider>(
            context,
            listen: false,
          );
          // Call delete lecture API with the specific lecture ID
          LectureService.deleteLecture(
                appState: appState,
                lectureId: myLectures[index].lectureId!,
              )
              .then((_) {
                // Refresh data after deletion
                fetchData();
                CustomErrorHandler.show(
                  context,
                  message: 'Lecture deleted successfully.',
                  type: ErrorType.success,
                );
                Future.delayed(const Duration(seconds: 1), () {
                  if (mounted) {
                    Navigator.pushNamedAndRemoveUntil(
                      context,
                      AppRoutes.teacherDashboard,
                      (route) => false,
                    );
                  }
                });
              })
              .catchError((e) {
                CustomErrorHandler.show(
                  context,
                  message: 'Failed to delete lecture: ${e.toString()}',
                  type: ErrorType.fail,
                );
              });
        } catch (e) {
          CustomErrorHandler.show(
            context,
            message: 'Error: ${e.toString()}',
            type: ErrorType.fail,
          );
        } finally {
          CustomConfirmationDialog.dismiss(context);
        }
        //Apilcancel
      },
    );
  }

  void _handleReschedule(int index) {
    // ✅ Validate lecture data before showing dialog
    if (myLectures[index].lectureId == null) {
      CustomErrorHandler.show(
        context,
        message: 'Cannot reschedule: Lecture ID is missing',
        type: ErrorType.fail,
      );
      return;
    }

    CustomConfirmationDialog.show(
      context,
      title: 'Reschedule Lecture',
      message: 'Are you sure you want to reschedule this lecture?',
      confirmButtonText: 'Yes, Reschedule',
      cancelButtonText: 'No',
      onConfirm: () async {
        print(
          '✅ Starting reschedule for lecture ID: ${myLectures[index].lectureId}',
        );

        try {
          // ✅ Get the lecture state provider
          final lectureState = Provider.of<LectureStateProvider>(
            context,
            listen: false,
          );

          // ✅ Set lecture data for rescheduling
          await lectureState.setFromScheduleSlot(myLectures[index]);

          // ✅ Dismiss dialog first
          if (mounted) {
            Navigator.pop(context); // Close confirmation dialog
          }

          // ✅ Small delay to ensure dialog is closed
          await Future.delayed(const Duration(milliseconds: 200));

          // ✅ Navigate to lecture setup screen
          if (mounted) {
            // Navigator.push(
            //   context,
            //   MaterialPageRoute(
            //     builder: (context) => const LectureSetupScreen(),
            //   ),
            // )
            Navigator.pushNamed(context, AppRoutes.lectureSetup).then((_) {
              lectureState.clearLectureState();
              fetchData();
            });
          }
        } catch (e) {
          print('❌ Error during reschedule: $e');

          if (mounted) {
            // ✅ Dismiss dialog if still open
            Navigator.pop(context);

            CustomErrorHandler.show(
              context,
              message:
                  'Error preparing lecture for rescheduling: ${e.toString()}',
              type: ErrorType.fail,
            );
          }
        }
      },
    );
  }

  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(title: 'My Lecture History'),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: loadTokenAndFetchData,
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                child: Padding(
                  padding: const EdgeInsets.all(AppStyles.spacingL),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Display My Lectures from API
                          if (myLectures.isEmpty)
                            Text(
                              'No lecture history available.',
                              style: AppStyles.bodyMedium.copyWith(
                                color: AppColors.textLight,
                              ),
                              textAlign: TextAlign.center,
                            )
                          else
                            ...myLectures.asMap().entries.map((entry) {
                              final index = entry.key;
                              final lecture = entry.value;
                              return Padding(
                                padding: const EdgeInsets.only(
                                  bottom: AppStyles.spacingM,
                                ),
                                child: LectureScheduleCard(
                                  lectureTitle: lecture.lectureTitle,
                                  date: lecture.formattedDate == ''
                                      ? 'Drafted'
                                      : lecture.formattedDate,
                                  timeRange: lecture.timeRange == ''
                                      ? ''
                                      : lecture.timeRange,
                                  editButtonText: 'RESCHEDULE',
                                  cancelButtonText: 'DELETE RECORD',
                                  onEdit: () => _handleReschedule(index),
                                  onCancel: () => _handleDelete(index),
                                ),
                              );
                            }).toList(),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
    );
  }
}
