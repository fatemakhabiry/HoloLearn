import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../state/providers/app_state_provider.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/confirmation_widget.dart';
import '../widgets/lecture_schedule_card_widget.dart';
import '../models/schedule_models.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/error_handler_widget.dart';
import '../services/schedule_service.dart';
import 'lecture_options_screen.dart';
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
      final lecturesData = await ScheduleService.fetchMyLectureHistory(appState);

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
  void _handleDelete() {
    CustomConfirmationDialog.show(
      context,
      title: 'Delete Lecture',
      message: 'Are you sure you want to delete this lecture along with all its saved data?',
      confirmButtonText: 'Yes, Delete',
      cancelButtonText: 'No',
      onConfirm: () {
        //Apilcancel
      },
    );
  }

  void _handleReschedule() {
    CustomConfirmationDialog.show(
      context,
      title: 'Reschedule Lecture',
      message: 'Are you sure you want to reschedule this lecture?',
      confirmButtonText: 'Yes, Reschedule',
      cancelButtonText: 'No',
      onConfirm: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (context) => const LectureSetupScreen(),
          ),
        );
      },
    );
  }



  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'My Lecture History',
      ),
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
                            ...myLectures.map((lecture) {
                              return Padding(
                                padding: const EdgeInsets.only(
                                  bottom: AppStyles.spacingM,
                                ),
                                child: LectureScheduleCard(
                                  lectureTitle: lecture.lectureTitle,
                                  date: lecture.formattedDate,
                                  timeRange: lecture.timeRange,
                                  editButtonText: 'RESCHEDULE',
                                  cancelButtonText: 'DELETE RECORD',
                                  onEdit: _handleReschedule,
                                  onCancel: _handleDelete,
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
