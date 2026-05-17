import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:open_file/open_file.dart';
import 'package:provider/provider.dart';

import '../../constants/constants.dart';
import '../../models/lecture_models.dart';
import '../../models/schedule_models.dart';
import '../../services/lecture_service.dart';
import '../../services/local_file_service.dart';
import '../../providers/app_state_provider.dart';
import '../../widgets/widgets.dart';

class StudentLectureContentScreen extends StatefulWidget {
  final ScheduleSlot session;

  const StudentLectureContentScreen({super.key, required this.session});

  @override
  State<StudentLectureContentScreen> createState() =>
      _StudentLectureContentScreenState();
}

class _StudentLectureContentScreenState
    extends State<StudentLectureContentScreen> {
  int get _lectureId => widget.session.lectureId ?? 0;
  bool isLoading = false;

  // Students only see content — not the raw generated lecture PDF
  // (that is teacher-only). Exclude GenContentType.lecture for students.
  static const List<GenContentType> _studentTypes = [
    GenContentType.worksheet,
    GenContentType.quiz,
    GenContentType.knowledgeGraph,
    GenContentType.worksheetAnswers,
    GenContentType.quizAnswers,
  ];

  final Map<GenContentType, bool> _cached = {};
  final Map<GenContentType, bool> _downloading = {};

  @override
  void initState() {
    super.initState();
    _checkCache();
  }

  Future<void> _checkCache() async {
    for (final type in _studentTypes) {
      final exists = await LocalFileService.exists(_lectureId, type);
      if (mounted) setState(() => _cached[type] = exists);
    }
  }

  Future<void> _downloadAndOpen(GenContentType type) async {
    final appState = context.read<AppStateProvider>();

    // Already cached — open directly
    if (_cached[type] == true) {
      final file = await LocalFileService.fileFor(_lectureId, type);
      await _openFile(file);
      return;
    }

    setState(() => _downloading[type] = true);

    try {
      // Uses lecture_id — no session_id needed for students
      final bytes = await LectureService.getStudentLectureContentBytes(
        _lectureId,
        type,
        appState,
      );

      final file = await LocalFileService.save(_lectureId, type, bytes);

      if (mounted) setState(() => _cached[type] = true);

      await _openFile(file);
    } on TimeoutException {
      _showError('Request timed out.');
    } on SocketException {
      _showError('No internet connection.');
    } catch (e) {
      _showError(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _downloading[type] = false);
    }
  }

  Future<void> _openFile(File file) async {
    final result = await OpenFile.open(file.path);
    if (result.type != ResultType.done && mounted) {
      _showError('Could not open file: ${result.message}');
    }
  }

  void _showError(String msg) {
    if (!mounted) return;
    CustomErrorHandler.show(context, message: msg, type: ErrorType.fail);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
        backgroundColor: Theme.of(context).scaffoldBackgroundColor,
        appBar: CustomAppBar(
          title: widget.session.lectureTitle,
          showBackButton: true,
        ),
        body: LoadingOverlay(
          isLoading: isLoading,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppStyles.spacingL),
            child: Center(
              child: Container(
                constraints: const BoxConstraints(maxWidth: 600),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // ── Lecture info card ─────────────────────────────────────
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(AppStyles.spacingL),
                      decoration: BoxDecoration(
                        color: context.cardColor,
                        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                        boxShadow: context.cardShadow,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.session.lectureTitle,
                            style: AppStyles.h2
                                .copyWith(color: context.textPrimary),
                          ),
                          const SizedBox(height: AppStyles.spacingS),
                          Text(
                            '${widget.session.teacherName}  •  ${widget.session.courseCode}',
                            style: AppStyles.caption,
                          ),
                          if (widget.session.formattedDate.isNotEmpty) ...[
                            const SizedBox(height: 2),
                            Text(
                              '${widget.session.formattedDate}  •  ${widget.session.timeRange}',
                              style: AppStyles.caption,
                            ),
                          ],
                        ],
                      ),
                    ),

                    const SizedBox(height: AppStyles.spacingL),

                    // ── Section label ─────────────────────────────────────────
                    Text(
                      'LECTURE MATERIALS',
                      style: AppStyles.labelStyle.copyWith(
                        fontWeight: AppFonts.bold,
                        fontSize: AppFonts.fontSizeXS,
                        letterSpacing: 1.2,
                        color: context.textPrimary,
                      ),
                    ),
                    const SizedBox(height: AppStyles.spacingM),

                    // ── Content tiles ─────────────────────────────────────────
                    ..._studentTypes.map(
                      (type) => ContentTileWidget(
                        type: type,
                        isCached: _cached[type] ?? false,
                        isDownloading: _downloading[type] ?? false,
                        onTap: () => _downloadAndOpen(type),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ));
  }
}
