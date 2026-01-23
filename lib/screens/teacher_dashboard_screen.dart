import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../screens/create_new_lecture_screen.dart';
import '../state/providers/app_state_provider.dart';
import '../models/schedule_models.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/confirmation_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';
import '../services/schedule_service.dart';

import 'edit_lecture_screen.dart';

class TeacherDashboardScreen extends StatefulWidget {
  const TeacherDashboardScreen({super.key});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen> with WidgetsBindingObserver {
  List<ScheduleSlot> myLectures = [];
  bool isLoading = true;
  bool _needsReload = false;

  @override
  void initState() {
    super.initState();
    loadTokenAndFetchData();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Check if we need to reload data when dependencies change
    if (_needsReload) {
      _needsReload = false;
      _reloadDataIfNeeded();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    // Reload data when app comes back to foreground
    if (state == AppLifecycleState.resumed) {
      _reloadDataIfNeeded();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void deactivate() {
    // Mark that we need to reload when coming back
    _needsReload = true;
    super.deactivate();
  }

  @override
  void activate() {
    // Reload data when screen becomes active again
    super.activate();
    if (_needsReload) {
      _needsReload = false;
      _reloadDataIfNeeded();
    }
  }

  /// Reload data only if screen is visible and not already loading
  void _reloadDataIfNeeded() {
    if (mounted && !isLoading) {
      // Small delay to ensure navigation is complete
      Future.delayed(const Duration(milliseconds: 100), () {
        if (mounted && !isLoading) {
          fetchScheduleData();
        }
      });
    }
  }

  /// Public method to manually refresh data (can be called from other screens)
  void refreshData() {
    if (mounted && !isLoading) {
      fetchScheduleData();
    }
  }

  /// Load token from storage and fetch schedule data
  Future<void> loadTokenAndFetchData() async {
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      if (appState.accessToken.isEmpty) {
        throw Exception('No authentication token found. Please login again.');
      }

      await fetchScheduleData();
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

  /// Fetch schedule data from API using the token
  Future<void> fetchScheduleData() async {
    final appState = Provider.of<AppStateProvider>(context, listen: false);
    if (appState.accessToken.isEmpty) return;

    setState(() {
      isLoading = true;
    });

    try {
      // Fetch lectures using the token - backend identifies teacher from token
      final lecturesData = await ScheduleService.fetchMyLectures(appState);

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

  void _handleCancel(ScheduleSlot lecture) {
    CustomConfirmationDialog.show(
      context,
      title: 'Cancel Lecture',
      message: 'Are you sure you want to cancel this lecture?',
      confirmButtonText: 'Yes, Cancel',
      cancelButtonText: 'No',
      onConfirm: () async {
        // Call API to cancel lecture
        await _cancelLecture(lecture.scheduleId ?? 0);
      },
    );
  }

  /// Cancel lecture by sending schedule_id to API
  Future<void> _cancelLecture(int scheduleId) async {
    if (scheduleId == 0) {
      CustomErrorHandler.show(
        context,
        message: 'Invalid lecture ID',
        type: ErrorType.fail,
      );
      return;
    }

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await ScheduleService.cancelLecture(
        appState: appState,
        scheduleId: scheduleId,
      );

      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Lecture cancelled successfully',
          type: ErrorType.success,
        );
        // Refresh the lecture list
        await fetchScheduleData();
      }
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message:
              'Failed to cancel lecture: ${e.toString().replaceAll('Exception: ', '')}',
          type: ErrorType.fail,
        );
      }
    }finally {
      // Ensure loading state is reset
      if (mounted) {
        setState(() {
          isLoading = false;
          CustomConfirmationDialog.dismiss(context);
        });
      }
    }
  }

  void _handleEdit(ScheduleSlot lecture) {
    CustomConfirmationDialog.show(
      context,
      title: 'Edit Lecture',
      message: 'Are you sure you want to edit this lecture?',
      confirmButtonText: 'Yes, Edit',
      cancelButtonText: 'No',
      onConfirm: () async {
        // Navigate to edit screen with scheduleId
        final result = await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) =>
                EditLectureScreen(scheduleId: lecture.scheduleId ?? 0),
          ),
        );

        // Refresh data if lecture was updated
        if (result == true) {
          await fetchScheduleData();
        }
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(
        title: "Hologram Sessions",
        showBackButton: false,
        showProfile: true,
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: fetchScheduleData,
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
                          // Section Header with Add Button
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                'MY SCHEDULED LECTURES',
                                style: AppStyles.h3,
                              ),
                              // Add Button
                              Container(
                                width: 40,
                                height: 40,
                                decoration: const BoxDecoration(
                                  color: AppColors.lightBlue,
                                  shape: BoxShape.circle,
                                ),
                                child: IconsButton(
                                  onPressed: () async {
                                    final result = await Navigator.push(
                                      context,
                                      MaterialPageRoute(
                                        builder: (context) =>
                                            const CreateNewLectureScreen(),
                                      ),
                                    );
                                    // Refresh data if a lecture was created
                                    if (result == true) {
                                      fetchScheduleData();
                                    }
                                  },
                                  icon: Icons.add,
                                  iconColor: AppColors.white,
                                  backgroundColor: AppColors.lightBlue,
                                  size: 40,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: AppStyles.spacingM),

                          // Display My Lectures from API
                          if (myLectures.isEmpty)
                            Text(
                              'No scheduled lectures',
                              style: AppStyles.bodyMedium.copyWith(
                                color: AppColors.textLight,
                              ),
                            )
                          else
                            ...myLectures.map((lecture) {
                              return Padding(
                                padding: const EdgeInsets.only(
                                  bottom: AppStyles.spacingM,
                                ),
                                child: LectureScheduleCard(
                                  lectureTitle: lecture.lectureTitle,
                                  date: lecture.formattedDate,
                                  timeRange: lecture.timeRange,
                                  onEdit: () => _handleEdit(lecture),
                                  onCancel: () => _handleCancel(lecture),
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
