import 'dart:async';
import 'dart:io';
import 'package:http/http.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';


import '../../widgets/widgets.dart';
import '../../constants/constants.dart';
import '../../models/schedule_models.dart';
import '../../services/schedule_service.dart';
import '../../state/providers/app_state_provider.dart';


class StudentDashboardScreen extends StatefulWidget {
  const StudentDashboardScreen({super.key});
  @override
  State<StudentDashboardScreen> createState() => _StudentDashboardScreenState();
}

class _StudentDashboardScreenState extends State<StudentDashboardScreen> {
  List<ScheduleSlot> fetchedLectures = [];
  bool isLoading = true;
  String? authToken;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    fetchScheduleData();
  }

  void sortSessions() {
    fetchedLectures.sort((a, b) {
      // Sort by date (start time) in ascending order
      return a.startDateTime.compareTo(b.startDateTime);
    });
  }

  List<ScheduleSlot> getDummySessions() {
    final now = DateTime.now();

    return [
      ScheduleSlot(
        teacherName: 'Dr. Smith',
        courseCode: 'CS101',
        lectureTitle: 'Intro to Computing',
        startTime: now.add(const Duration(minutes: 30)).toIso8601String(),
        endTime: now
            .add(const Duration(hours: 1, minutes: 30))
            .toIso8601String(),
        scheduleId: 1,
      ),
      ScheduleSlot(
        teacherName: 'Dr. Ahmed',
        courseCode: 'CS202',
        lectureTitle: 'Data Structures',
        startTime: now.subtract(const Duration(minutes: 15)).toIso8601String(),
        endTime: now.add(const Duration(minutes: 45)).toIso8601String(),
        scheduleId: 2,
      ),
      ScheduleSlot(
        teacherName: 'Dr. Mona',
        courseCode: 'CS303',
        lectureTitle: 'Operating Systems',
        startTime: now.subtract(const Duration(hours: 2)).toIso8601String(),
        endTime: now.subtract(const Duration(hours: 1)).toIso8601String(),
        scheduleId: 3,
      ),
    ];
  }

  Future<void> fetchScheduleData() async {
    List<ScheduleSlot> data = [];
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      // fetchedLectures = getDummySessions();
    data = await ScheduleService.fetchStudentLectures(appState);
    } on ClientException {
      errorMessage = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      errorMessage = 'No internet connection.';
    } on TimeoutException {
      errorMessage = 'Request timed out.';
    } catch (e) {
      errorMessage = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (errorMessage != null) {
        CustomErrorHandler.show(
          context,
          message: errorMessage!,
          type: ErrorType.fail,
          duration: const Duration(seconds: 6),
        );
        errorMessage = null;
      }
      if (mounted) {
        setState(() {
          fetchedLectures=data;
          sortSessions();
          isLoading = false;
        });
      }
    }
  }

  void _handleOpenTranscript(int index) {
    print('Open Transcript pressed on card index: $index');
  }

  void _handleEnterChat(int index) {
    print('Enter Chat pressed on card index: $index');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Upcoming Lectures',
        showBackButton: false,
        showProfile: true,
      ),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: fetchScheduleData,
              child: fetchedLectures.isEmpty
                  ? SingleChildScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      child: SizedBox(
                        height: MediaQuery.of(context).size.height - 200,
                        child: Center(
                          child: Text(
                            'No scheduled lectures',
                            textAlign: TextAlign.center,
                            style: AppStyles.h2.copyWith(
                              color: AppColors.textLight,
                            ),
                          ),
                        ),
                      ),
                    )
                  : ListView.builder(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      itemCount: fetchedLectures.length,
                      itemBuilder: (context, index) => Padding(
                        padding: const EdgeInsets.only(
                          bottom: AppStyles.spacingM,
                        ),
                        child: SessionCard(
                          session: fetchedLectures[index],
                          onOpenTranscript: () => _handleOpenTranscript(index),
                          onEnterChat: () => _handleEnterChat(index),
                        ),
                      ),
                    ),
            ),
    );
  }
}
