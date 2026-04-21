// import 'package:flutter/foundation.dart';
// import '../../utils/storage_helper.dart';

// class ProcessingNotifier extends ChangeNotifier {
//   bool _isActive = false;
//   String _stepLabel = '';
//   int _sessionId = 0;
//   bool _isDone = false;

//   bool get isActive => _isActive;
//   String get stepLabel => _stepLabel;
//   int get sessionId => _sessionId;
//   bool get isDone => _isDone;

//   // ── Init from storage ─────────────────────────────────────────────────────

//   Future<void> init() async {
//     final data = await StorageHelper.getProcessingState();
//     if (data != null) {
//       _isActive = data['isActive'] as bool? ?? false;
//       _stepLabel = data['stepLabel'] as String? ?? '';
//       _sessionId = data['sessionId'] as int? ?? 0;
//       _isDone = data['isDone'] as bool? ?? false;
//       notifyListeners();
//     }
//   }

//   Future<void> _save() async {
//     await StorageHelper.saveProcessingState({
//       'isActive': _isActive,
//       'stepLabel': _stepLabel,
//       'sessionId': _sessionId,
//       'isDone': _isDone,
//     });
//   }

//   // ── Actions ───────────────────────────────────────────────────────────────

//   Future<void> start({int sessionId = 0}) async {
//     _isActive = true;
//     _stepLabel = '';
//     _sessionId = sessionId;
//     _isDone = false;
//     await _save();
//     notifyListeners();
//   }

//   Future<void> update(String stepLabel) async {
//     _isActive = true;
//     _stepLabel = stepLabel;
//     await _save();
//     notifyListeners();
//   }

//   Future<void> stop() async {
//     _isDone = true;
//     _stepLabel = 'Complete';
//     await _save();
//     notifyListeners();
//   }

//   Future<void> dismiss() async {
//     _isActive = false;
//     _stepLabel = '';
//     _sessionId = 0;
//     _isDone = false;
//     await _save();
//     notifyListeners();
//   }
// }
// import 'dart:async';
// import 'dart:convert';
// import 'package:flutter/foundation.dart';
// import 'package:http/http.dart' as http;
// import '../../config/api_config.dart';
// import '../../models/session_models.dart';
// import '../../state/providers/app_state_provider.dart';
// import '../../utils/storage_helper.dart';

// class ProcessingNotifier extends ChangeNotifier {
//   // ── State ─────────────────────────────────────────────────────────────────
//   LectureProcessingModel _model = const LectureProcessingModel();

//   // ── Getters ───────────────────────────────────────────────────────────────
//   LectureProcessingModel get model => _model;
//   ProcessingLifecycle get lifecycle => _model.lifecycle;
//   int get sessionId => int.tryParse(_model.sessionId ?? '0') ?? 0;
//   double get progress => _model.progress;
//   String get stageTitle => _model.stageTitle;
//   String get stageDescription => _model.stageDescription;
//   String get estimatedTimeLabel => _model.estimatedTimeLabel;
//   String? get errorMessage => _model.errorMessage;
//   bool get isActive =>
//       _model.lifecycle != ProcessingLifecycle.idle &&
//       _model.lifecycle != ProcessingLifecycle.failed;
//   bool get isDone => _model.lifecycle == ProcessingLifecycle.completed;
//   bool get isAwaitingApproval => _model.isAwaitingApproval;
//   bool get isTerminal => _model.isTerminal;

//   // ── Internal ──────────────────────────────────────────────────────────────
//   StreamSubscription<LectureProcessingModel>? _streamSub;

//   // ── Init ──────────────────────────────────────────────────────────────────
//   Future<void> init() async {
//     final data = await StorageHelper.getProcessingState();
//     if (data == null) return;
//     _model = LectureProcessingModel.fromApi(data);
//     notifyListeners();
//   }

//   Future<void> _save() async {
//     await StorageHelper.saveProcessingState({
//       'session_id': _model.sessionId,
//       'current_step': _model.currentStepKey,
//       'progress_percent': (_model.progress * 100).toInt(),
//       'step_number': _model.currentStep,
//       'total_steps': _model.totalSteps,
//       'step_label': _model.stageTitle,
//       'description': _model.stageDescription,
//     });
//   }

//   // ── Start ─────────────────────────────────────────────────────────────────
//   Future<void> startForSession(
//       int sessionId, AppStateProvider appState) async {
//     _streamSub?.cancel();

//     _model = LectureProcessingModel(
//       sessionId: sessionId.toString(),
//       currentStepKey: 'starting',
//       lifecycle: ProcessingLifecycle.starting,
//       progress: 0.05,
//       currentStep: 1,
//       totalSteps: 3,
//       stageTitle: 'Starting',
//       stageDescription: 'Initializing your session…',
//     );

//     await _save();
//     notifyListeners();

//     _startStream(sessionId, appState);
//   }

//   void _startStream(int sessionId, AppStateProvider appState) {
//     _streamSub?.cancel();
//     _streamSub = _sseStream(sessionId, appState).listen(
//       _onModel,
//       onError: (_) => _setFailed('Stream error'),
//       onDone: () {
//         if (!isTerminal) _setFailed('Stream closed unexpectedly');
//       },
//     );
//   }

//   void _onModel(LectureProcessingModel incoming) {
//     final hasChange = _hasMeaningfulChange(_model, incoming);
//     if (!hasChange) return;

//     _model = incoming;
//     _save();
//     notifyListeners();
//   }

//   bool _hasMeaningfulChange(
//       LectureProcessingModel prev, LectureProcessingModel next) {
//     return prev.currentStepKey != next.currentStepKey ||
//         prev.lifecycle != next.lifecycle ||
//         prev.progress != next.progress ||
//         prev.stageTitle != next.stageTitle ||
//         prev.stageDescription != next.stageDescription;
//   }

//   void _setFailed(String message) {
//     _model = _model.copyWith(
//       lifecycle: ProcessingLifecycle.failed,
//       errorMessage: message,
//     );
//     _streamSub?.cancel();
//     _save();
//     notifyListeners();
//   }

//   // ── Resume ────────────────────────────────────────────────────────────────
//   Future<void> resumeIfNeeded(AppStateProvider appState) async {
//     if (sessionId != 0 && !isTerminal) {
//       _startStream(sessionId, appState);
//     }
//   }

//   // ── Dismiss ───────────────────────────────────────────────────────────────
//   Future<void> dismiss() async {
//     _streamSub?.cancel();
//     _model = const LectureProcessingModel();
//     await StorageHelper.clearProcessingState();
//     notifyListeners();
//   }

//   // ── SSE Stream ────────────────────────────────────────────────────────────
//   static Stream<LectureProcessingModel> _sseStream(
//       int sessionId, AppStateProvider appState) {
//     final controller = StreamController<LectureProcessingModel>.broadcast();

//     Future<void> connect() async {
//       final request = http.Request(
//         'GET',
//         Uri.parse(
//           ApiConfig.getUrl(ApiConfig.getSessionStreamEndpoint)
//               .replaceAll('{session_id}', sessionId.toString()),
//         ),
//       )..headers.addAll({
//           'Content-Type': 'application/json',
//           'ngrok-skip-browser-warning': 'true',
//           'Authorization': 'Bearer ${appState.accessToken}',
//           'Accept': 'text/event-stream',
//           'Cache-Control': 'no-cache',
//         });

//       try {
//         final streamedResponse =
//             await http.Client().send(request);

//         if (streamedResponse.statusCode < 200 ||
//             streamedResponse.statusCode >= 300) {
//           controller.addError(
//               Exception('Stream failed: ${streamedResponse.statusCode}'));
//           await controller.close();
//           return;
//         }

//         final buffer = StringBuffer();

//         await for (final chunk
//             in streamedResponse.stream.transform(utf8.decoder)) {
//           buffer.write(chunk);
//           String bufStr = buffer.toString();

//           while (bufStr.contains('\n\n')) {
//             final idx = bufStr.indexOf('\n\n');
//             final block = bufStr.substring(0, idx).trim();
//             bufStr = bufStr.substring(idx + 2);
//             buffer..clear()..write(bufStr);

//             for (final line in block.split('\n')) {
//               if (!line.startsWith('data:')) continue;
//               final raw = line.substring(5).trim();
//               if (raw.isEmpty) continue;

//               try {
//                 final json = jsonDecode(raw) as Map<String, dynamic>;
//                 final model = LectureProcessingModel.fromSse(json);
//                 controller.add(model);

//                 if (model.isTerminal || model.isAwaitingApproval) {
//                   await controller.close();
//                   return;
//                 }
//               } catch (_) {}
//             }
//           }
//         }
//       } catch (e) {
//         controller.addError(e);
//       } finally {
//         if (!controller.isClosed) await controller.close();
//       }
//     }

//     connect();
//     return controller.stream;
//   }

//   @override
//   void dispose() {
//     _streamSub?.cancel();
//     super.dispose();
//   }
// }
import 'dart:async';
import 'dart:math';
import 'package:flutter/foundation.dart';
import '../../models/lecture_models.dart';
import '../../services/lecture_service.dart';
import '../../state/providers/app_state_provider.dart';
import '../../utils/storage_helper.dart';

class ProcessingNotifier extends ChangeNotifier {
  // ── Config ────────────────────────────────────────────────────────────────
  final Duration _pollEvery;
  final bool useDemoMode;

  ProcessingNotifier({
    int pollIntervalSeconds = 3,
    this.useDemoMode = false,
  }) : _pollEvery = Duration(seconds: max(1, pollIntervalSeconds));

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
  String get Title => _title(_job.stageTitle);


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
    String _title(String stageTitle) {
    switch (stageTitle) {
      case 'starting':
        return 'Starting';
      case 'generating_lecture':
        return 'Generating Lecture';
      case 'awaiting_approval':
        return 'Awaiting Approval';
      case 'regenerating':
        return 'Regenerating';
      case 'generating_content':
        return 'Generating Content';
      case 'done':
        return 'Done';
      case 'failed':
        return 'Failed';
      default:
        return 'Unknown';
    }
  }
  // ── Dismiss ───────────────────────────────────────────────────────────────
  Future<void> dismiss() async {
    _pollTimer?.cancel();
    _job = const LectureProcessingModel();
    await StorageHelper.clearProcessingState();
    notifyListeners();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}