import 'package:flutter/material.dart';
import 'package:hololearn/screens/create_new_lecture_screen.dart';
import '../utils/app_state.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/confirmation_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../utils/schedule_slot.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';
import '../services/schedule_service.dart';

import 'edit_lecture_screen.dart';
import 'lecture_options_screen.dart';

class TeacherDashboardScreen extends StatefulWidget {
  const TeacherDashboardScreen({super.key});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen> {
  List<ScheduleSlot> myLectures = [];
  bool isLoading = true;
  String? authToken;

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
          message: 'Failed to load lectures: ${e.toString().replaceAll('Exception: ', '')}',
          type: ErrorType.fail,
        );
      }
      setState(() {
        isLoading = false;
      });
    }
  }
void _handleCancel() {
  CustomConfirmationDialog.show(
    context,
    title: 'Cancel Lecture',
    message: 'Are you sure you want to cancel this lecture?',
    confirmButtonText: 'Yes, Cancel',
    cancelButtonText: 'No',
    onConfirm: () {
      //Apilcancel
    },
  );
}

void _handleEdit(){
  CustomConfirmationDialog.show(
    context,
    title: 'Edit Lecture',
    message: 'Are you sure you want to edit this lecture?',
    confirmButtonText: 'Yes, Edit',
    cancelButtonText: 'No',
    onConfirm: () {
      // Navigator.push(
      //   context,
      //   MaterialPageRoute(
      //     builder: (context) => EditLectureScreen(),
      //   ),
      // );
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
                                  onEdit: _handleEdit,
                                  onCancel: _handleCancel
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
