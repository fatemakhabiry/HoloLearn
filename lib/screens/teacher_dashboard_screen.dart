import 'package:flutter/material.dart';
import '../utils/app_state.dart';
import 'create_new_lecture_screen.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../utils/schedule_slot.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';
import '../services/schedule_service.dart';
import '../services/storage_service.dart';

class TeacherDashboardScreen extends StatefulWidget {
  const TeacherDashboardScreen({super.key});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen> {
  List<ScheduleSlot> myLectures = [];
  bool isLoading = true;
  String? authToken;
  StorageService? storageService;

  @override
  void initState() {
    super.initState();
    loadTokenAndFetchData();
  }

  /// Load token from storage and fetch schedule data
  Future<void> loadTokenAndFetchData() async {
    try {
      authToken = AppState.accessToken;
      if (authToken == null || authToken!.isEmpty) {
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
    if (authToken == null) return;

    setState(() {
      isLoading = true;
    });

    try {
      // Fetch lectures using the token - backend identifies teacher from token
      final lecturesData = await ScheduleService.fetchMyLectures(authToken!);

      if (!mounted) return;

      setState(() {
        myLectures = lecturesData;
        isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Failed to load lectures: ${e.toString()}',
          type: ErrorType.fail,
        );
      }
      setState(() {
        isLoading = false;
      });
    }
  }

  /// Cancel a lecture
  // Future<void> cancelLecture(int scheduleId) async {
  //   if (authToken == null) return;

  //   try {
  //     final message = await ScheduleService.cancelLecture(authToken!, scheduleId);

  //     if (mounted) {
  //       CustomErrorHandler.show(
  //         context,
  //         message: message,
  //         type: ErrorType.success,
  //       );

  //       // Refresh the data
  //       fetchScheduleData();
  //     }
  //   } catch (e) {
  //     if (mounted) {
  //       CustomErrorHandler.show(
  //         context,
  //         message: 'Failed to cancel lecture: ${e.toString()}',
  //         type: ErrorType.fail,
  //       );
  //     }
  //   }
  // }

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
                                  onEdit: () {
                                    // TODO: Navigate to edit lecture screen
                                    // Pass the lecture object to pre-fill the form
                                    print(
                                      'Edit lecture: ${lecture.scheduleId}',
                                    );
                                  },
                                  onCancel: () {
                                    // Show confirmation dialog
                                    showDialog(
                                      context: context,
                                      builder: (context) => AlertDialog(
                                        title: const Text('Cancel Lecture'),
                                        content: const Text(
                                          'Are you sure you want to cancel this lecture?',
                                        ),
                                        actions: [
                                          TextButton(
                                            onPressed: () =>
                                                Navigator.pop(context),
                                            child: const Text('No'),
                                          ),
                                          TextButton(
                                            onPressed: () {
                                              Navigator.pop(context);
                                              // cancelLecture(lecture.scheduleId);
                                            },
                                            child: const Text('Yes, Cancel'),
                                          ),
                                        ],
                                      ),
                                    );
                                  },
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
