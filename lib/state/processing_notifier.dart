import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../../models/lecture_models.dart';
import '../../services/lecture_service.dart';
import '../../providers/app_state_provider.dart';
import '../../utils/storage_helper.dart';

class ProcessingNotifier extends ChangeNotifier {
  // ── Config ────────────────────────────────────────────────────────────────
  final Duration _pollEvery;
  final bool useDemoMode;

  ProcessingNotifier({
    int pollIntervalSeconds = 3,
    this.useDemoMode = false,
  }) : _pollEvery = Duration(seconds: max(30, pollIntervalSeconds));

  // ── State ─────────────────────────────────────────────────────────────────
  LectureProcessingModel _job = const LectureProcessingModel();
  AppStateProvider? _appState;
  Timer? _pollTimer;

  // ── Getters ───────────────────────────────────────────────────────────────
  LectureProcessingModel get job => _job;
  ProcessingLifecycle get lifecycle => _job.lifecycle;
  int get sessionId => int.tryParse(_job.sessionId ?? '0') ?? 0;
  double get progress => _job.progress;
  String get stageTitle => _job.stageTitle;
  String get stageDescription => _job.stageDescription;
  String get estimatedTimeLabel => _job.estimatedTimeLabel;
  String? get errorMessage => _job.errorMessage;
  bool get isActive =>
      _job.lifecycle != ProcessingLifecycle.idle &&
      _job.lifecycle != ProcessingLifecycle.failed;
  bool get isDone => _job.isDone;
  bool get isAwaitingApproval => _job.isAwaitingApproval;
  bool get isTerminal => _job.isTerminal;
  String get Title => _job.title;


  // ── Init from storage ─────────────────────────────────────────────────────
  Future<void> init() async {
    final data = await StorageHelper.getProcessingState();
    if (data == null) return;
    _job = LectureProcessingModel.fromApi(data);
    notifyListeners();
  }

  Future<void> _save() async {
    await StorageHelper.saveProcessingState({
      'session_id': _job.sessionId,
      'current_step': _job.currentStepKey,
      'progress_percent': (_job.progress * 100).toInt(),
      'step_number': _job.currentStep,
      'total_steps': _job.totalSteps,
      'step_label': _job.stageTitle,
      'description': _job.stageDescription,
    });
  }

  // ── Start ─────────────────────────────────────────────────────────────────
  void startForSession(int sessionId, AppStateProvider appState) {
    _appState = appState;
    _pollTimer?.cancel();

    _job = LectureProcessingModel(
      sessionId: sessionId.toString(),
      currentStepKey: 'starting',
      lifecycle: ProcessingLifecycle.starting,
      progress: 0.05,
      currentStep: 1,
      totalSteps: 3,
      stageTitle: 'Starting',
      stageDescription: 'Initializing your session…',
    );

    _save();
    notifyListeners();

    if (useDemoMode) {
      _runDemoFlow();
      return;
    }

    _startPolling(sessionId);
  }

  // ── Polling ───────────────────────────────────────────────────────────────
  void _startPolling(int sessionId) {
    _pollTimer?.cancel();
    _fetchStatusOnce(sessionId);
    _pollTimer = Timer.periodic(_pollEvery, (_) => _fetchStatusOnce(sessionId));
  }

  Future<void> _fetchStatusOnce(int sessionId) async {
    if (_appState == null) return;
    try {
      final latest = await LectureService.fetchSessionStatus(sessionId, _appState!);
      final next = LectureProcessingModel.fromApi({
        'session_id': latest.sessionId.toString(),
        'stage_title':latest.stageTitle,
        'description':latest.stageDescription,
        'current_step': latest.currentStep,
        'progress_percent': latest.progress * 100, // filled by fromApi via _STEP_PROGRESS on backend
        'step_number': latest.currentStep,
        'total_steps': latest.totalSteps,
        'step_label': latest.currentStepKey,
        'error': latest.errorMessage,
      });

      if (_hasMeaningfulChange(_job, next)) {
        _job = next;
        _save();
        notifyListeners();
      }

      if (next.isTerminal) _pollTimer?.cancel();
    } catch (e) {
      _pollTimer?.cancel();
      _job = _job.copyWith(
        lifecycle: ProcessingLifecycle.failed,
        errorMessage: e.toString(),
      );
      _save();
      notifyListeners();
    }
  }

  bool _hasMeaningfulChange(LectureProcessingModel prev, LectureProcessingModel next) {
    return prev.currentStepKey != next.currentStepKey ||
        prev.lifecycle != next.lifecycle ||
        prev.progress != next.progress ||
        prev.stageTitle != next.stageTitle ||
        prev.stageDescription != next.stageDescription ||
        prev.estimatedTimeLabel != next.estimatedTimeLabel ||
        prev.errorMessage != next.errorMessage;
  }

  // ── Resume after restart ──────────────────────────────────────────────────
  Future<void> resumeIfNeeded(AppStateProvider appState) async {
    _appState = appState;
    if (sessionId != 0 && !isTerminal) {
      if (useDemoMode) {
        _runDemoFlow();
      } else {
        _startPolling(sessionId);
      }
    }
  }

  // ── Demo flow ─────────────────────────────────────────────────────────────
  void _runDemoFlow() {
    const demoFlow = [
      (0.05, 1, 'starting', 'Starting', 'Initializing your session…', '2 mins'),
      (0.40, 1, 'generating_lecture', 'Processing Content',
          'Our AI is analyzing your uploaded materials to build the lecture structure.', '2 mins'),
      (0.50, 1, 'awaiting_approval', 'Awaiting Your Review',
          'Lecture draft is ready. Please review and approve or send feedback.', '1 min'),
      (0.60, 1, 'regenerating', 'Regenerating Lecture',
          'Applying your feedback and regenerating the lecture…', '1 min'),
      (0.80, 2, 'generating_content', 'Generating Materials',
          'Creating script, quiz, worksheet and summary from the approved lecture.', '30s'),
      (1.00, 3, 'done', 'Complete',
          'All content has been generated successfully.', '0s'),
    ];

    var index = 0;
    _pollTimer = Timer.periodic(_pollEvery, (timer) {
      final f = demoFlow[index];
      _job = _job.copyWith(
        currentStepKey: f.$3,
        lifecycle: LectureProcessingModel.parseLifecycle(f.$3),
        progress: f.$1,
        currentStep: f.$2,
        totalSteps: 3,
        stageTitle: f.$4,
        stageDescription: f.$5,
        estimatedTimeLabel: f.$6,
        errorMessage: null,
      );
      _save();
      notifyListeners();

      index++;
      if (index >= demoFlow.length) timer.cancel();
    });
  }
  // ── Dismiss ───────────────────────────────────────────────────────────────
Future<void> dismiss() async {
  _pollTimer?.cancel();
  _job = const LectureProcessingModel();
  await StorageHelper.clearProcessingState();
  await StorageHelper.clearSessionId(); 
  notifyListeners();
}

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}