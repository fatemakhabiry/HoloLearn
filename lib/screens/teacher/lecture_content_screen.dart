import 'dart:io';
import 'dart:async';
import 'package:open_file/open_file.dart';
import 'package:provider/provider.dart';
import 'package:flutter/material.dart';

import '../../models/schedule_models.dart';
import '../../services/local_file_service.dart';
// import '../../utils/storage_helper.dart';
import '../../widgets/widgets.dart';
import '../../constants/constants.dart';
import '../../models/lecture_models.dart';
import '../../services/lecture_service.dart';
import '../../providers/app_state_provider.dart';

class LectureContentScreen extends StatefulWidget {
  final ScheduleSlot lecture;

  const LectureContentScreen({super.key, required this.lecture});

  @override
  State<LectureContentScreen> createState() => _LectureContentScreenState();
}

class _LectureContentScreenState extends State<LectureContentScreen> {
  // int _sessionId = 0; // ← no longer a getter, now a real field

  int get _lectureId => widget.lecture.lectureId ?? 0;
  // Which content types are available for this lecture
  List<GenContentType> get _contentTypes {
    final allTypes = [
      GenContentType.lecture,
      GenContentType.summary,
      GenContentType.script,
      GenContentType.worksheet,
      GenContentType.quiz,
      GenContentType.knowledgeGraph,
      GenContentType.worksheetAnswers,
      GenContentType.quizAnswers,
    ];

    // Prepared lectures don't have a generated lecture PDF
    if (widget.lecture.lectureType == 'prepared') {
      return allTypes.where((t) => t != GenContentType.lecture).toList();
    }

    return allTypes;
  }

  // Per-tile state
  final Map<GenContentType, bool> _cached = {};
  final Map<GenContentType, bool> _downloading = {};

  @override
  void initState() {
    super.initState();
    // _loadSessionId();
    _checkCache();
  }

  // Future<void> _loadSessionId() async {
  //   final sessionId = await StorageHelper.getSessionIdForLecture(_lectureId);
  //   if (sessionId == null) {
  //     _showError('Session not found for this lecture.');
  //     return;
  //   }
  //   setState(() => _sessionId = sessionId);
  //   _checkCache(); // ← move this here, after sessionId is loaded
  // }

  /// Check which files are already on disk
  Future<void> _checkCache() async {
    for (final type in _contentTypes) {
      final exists = await LocalFileService.exists(_lectureId, type);
      if (mounted) {
        setState(() => _cached[type] = exists);
      }
    }
  }

  /// Download → save → open
  Future<void> _downloadAndOpen(GenContentType type) async {
    final appState = context.read<AppStateProvider>();
    // If cached, just open
    if (_cached[type] == true) {
      final file = await LocalFileService.fileFor(_lectureId, type);
      await _openFile(file);
      return;
    }

    setState(() => _downloading[type] = true);

    try {
      // ── Call your existing service method ──────────────────────────────
      final bytes;
      if (type == GenContentType.lecture) {
         bytes= await LectureService.getLecturePdfBytes(_lectureId, appState);
      } else {
         bytes = await LectureService.getLectureGeneratedResourceBytes(
          _lectureId,
          type,
          appState,
        );
        // ───────────────────────────────────────────────────────────────────
      }

      final file = await LocalFileService.save(_lectureId, type, bytes);

      if (mounted) setState(() => _cached[type] = true);

      await _openFile(file);
    } on TimeoutException {
      _showError('Request timed out.');
    } catch (e) {
      _showError(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _downloading[type] = false);
    }
  }

  /// Opens a local file with the device's default app.
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
        title: widget.lecture.lectureTitle,
        showBackButton: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppStyles.spacingL),
        child: Center(
          child: Container(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header info
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppStyles.spacingL),
                  decoration: BoxDecoration(
                    color: Theme.of(context).cardColor,
                    borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                    boxShadow: AppStyles.cardShadow,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.lecture.lectureTitle, style: AppStyles.h2.copyWith(color: context.textPrimary)),
                      const SizedBox(height: AppStyles.spacingS),
                      Text(
                        '${widget.lecture.courseCode}  •  ${widget.lecture.formattedDate}',
                        style: AppStyles.caption,
                      ),
                      if (widget.lecture.timeRange.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          widget.lecture.timeRange,
                          style: AppStyles.caption,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: AppStyles.spacingL),

                Text(
                  'GENERATED CONTENT',
                  style: AppStyles.labelStyle.copyWith(
                    fontWeight: AppFonts.bold,
                    fontSize: AppFonts.fontSizeXS,
                    letterSpacing: 1.2,
                    color: context.textPrimary
                  ),
                ),
                const SizedBox(height: AppStyles.spacingM),

                // Content type tiles
                ..._contentTypes.map(
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
    );
  }
}
