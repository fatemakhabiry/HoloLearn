import 'package:flutter/material.dart';
import 'create_new_lecture_screen.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../utils/schedule_slot.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';

class TeacherDashboardScreen extends StatefulWidget {
  const TeacherDashboardScreen({super.key});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen> {
  List<ScheduleSlot> reservedSlots = [];
  List<ScheduleSlot> myLectures = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchScheduleData();
  }

  /// Fetch schedule data from API
  Future<void> fetchScheduleData() async {
    setState(() {
      isLoading = true;
    });

    try {
      // TODO: Replace with your actual API call
      // final response = await http.get(Uri.parse('your-api-url'));
      // final data = json.decode(response.body);
      // final scheduleResponse = ScheduleResponse.fromJson(data);

      // Simulated API response matching your exact API structure
      final apiResponseJson = {
        "reserved_slots": [
          {
            "start_time": "2025-01-20T10:00:00",
            "end_time": "2025-01-20T11:30:00",
            "schedule_id": 1,
            "teacher_name": "Dr. Ahmed",
            "lecture_title": "Python Basics",
            "status": "scheduled",
          },
          {
            "start_time": "2025-01-20T14:00:00",
            "end_time": "2025-01-20T15:00:00",
            "schedule_id": 2,
            "teacher_name": "Prof.Jones",
            "lecture_title": "Data Structures",
            "status": "scheduled",
          },
        ],
      };

      // Parse using ScheduleResponse model
      final scheduleResponse = ScheduleResponse.fromJson(apiResponseJson);
      if (!mounted) return;
      setState(() {
        reservedSlots = scheduleResponse.reservedSlots;

        // For demo: using same data for my lectures
        // In real app, you'd fetch from a different endpoint
        myLectures = scheduleResponse.reservedSlots;

        isLoading = false;
      });
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Failed to load schedule data. Please try again.',
          type: ErrorType.fail,
        );
      }
      setState(() {
        isLoading = false;
      });
    }
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
          : SingleChildScrollView(
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
                            Text('MY SCHEDULED LECTURES', style: AppStyles.h3),
                            // Add Button
                            Container(
                              width: 40,
                              height: 40,
                              decoration: const BoxDecoration(
                                color: AppColors.lightBlue,
                                shape: BoxShape.circle,
                              ),
                              child: IconsButton(
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (context) =>
                                          const CreateNewLectureScreen(),
                                    ),
                                  );
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
                                  print('Edit lecture: ${lecture.scheduleId}');
                                  // TODO: Navigate to edit the lecture screen
                                },
                                onCancel: () {
                                  print(
                                    'Cancel lecture: ${lecture.scheduleId}',
                                  );
                                  // TODO: remove the lecture via API
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
    );
  }
}
