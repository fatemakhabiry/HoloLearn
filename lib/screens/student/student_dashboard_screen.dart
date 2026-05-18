import 'dart:async';
import 'dart:io';
import 'package:hololearn/routes/app_routes.dart';
import 'package:http/http.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../widgets/widgets.dart';
import '../../constants/constants.dart';
import '../../models/schedule_models.dart';
import '../../services/schedule_service.dart';
import '../../providers/app_state_provider.dart';

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
          fetchedLectures = data;
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
    // print('Enter Chat pressed on card index: $index');
    Navigator.pushNamed(
      context,
      AppRoutes.studentQAScreen,
      arguments: {"session": fetchedLectures[index]},
    );
  }

  void _handleLectureContent(int index) {
    // print('Enter Chat pressed on card index: $index');
    Navigator.pushNamed(
      context,
      AppRoutes.studentlectureContent,
      arguments: {"session": fetchedLectures[index]},
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const CustomAppBar(
        title: 'Upcoming Lectures',
        showBackButton: false,
        showProfile: true,
      ),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: LoadingOverlay(
        isLoading: isLoading,
        child: RefreshIndicator(
          onRefresh: fetchScheduleData,
          child: fetchedLectures.isEmpty
              ? SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: Padding(
                    padding: const EdgeInsets.all(AppStyles.spacingL),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        ResearchAgentButton(
                          onTap: () => Navigator.pushNamed(
                            context,
                            AppRoutes.researchAgent,
                          ),
                        ),
                        const SizedBox(height: AppStyles.spacingL),
                        SizedBox(
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
                      ],
                    ),
                  ),
                )
              : ListView.builder(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.all(AppStyles.spacingL),
                  itemCount: fetchedLectures.length + 1,
                  itemBuilder: (context, index) {
                    if (index == 0) {
                      return Column(
                        children: [
                          CustomButton(
                            text: 'Research Agent',
                            onPressed: () {
                              Navigator.pushNamed(
                                context,
                                AppRoutes.researchAgent,
                              );
                            },
                            buttonType: ButtonType.secondary,
                            fullWidth: true,
                          ),
                          const SizedBox(height: AppStyles.spacingL),
                        ],
                      );
                    }

                    final lectureIndex = index - 1;
                    return Padding(
                      padding: const EdgeInsets.only(
                        bottom: AppStyles.spacingM,
                      ),
                      child: SessionCard(
                        session: fetchedLectures[lectureIndex],
                        onOpenTranscript: () =>
                            _handleOpenTranscript(lectureIndex),
                        onEnterChat: () => _handleEnterChat(lectureIndex),
                        onLectureContent: () =>
                            _handleLectureContent(lectureIndex),
                      ),
                    );
                  },
                ),
        ),
      ),
    );
  }
}
