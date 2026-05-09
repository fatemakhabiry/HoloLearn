import 'dart:io';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/constants.dart';
import '../../models/qa_models.dart';
import '../../models/schedule_models.dart';
import '../../providers/app_state_provider.dart';
import '../../services/qa_service.dart';
import '../../widgets/widgets.dart';

// ─── Internal UI model ────────────────────────────────────────────────────────

enum MessageSender { you, hologramAvatar }

class ChatMessage {
  final String text;
  final MessageSender sender;
  final DateTime timestamp;
  final int? messageId;

  ChatMessage({
    required this.text,
    required this.sender,
    DateTime? timestamp,
    this.messageId,
  }) : timestamp = timestamp ?? DateTime.now();

  factory ChatMessage.fromQAMessage(QAMessage msg) {
    return ChatMessage(
      text: msg.content,
      sender: msg.role == QAMessageRole.assistant
          ? MessageSender.hologramAvatar
          : MessageSender.you,
      timestamp: msg.createdAt,
      messageId: msg.messageId,
    );
  }
}

// ─── Screen ───────────────────────────────────────────────────────────────────

class StudentQAScreen extends StatefulWidget {
  final ScheduleSlot session;

  const StudentQAScreen({super.key, required this.session});

  @override
  State<StudentQAScreen> createState() => _StudentQAScreenState();
}

class _StudentQAScreenState extends State<StudentQAScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  bool isLoading = true;
  bool _isSending = false;
  bool _isInQueue = false;
  int? _queuePosition;
  int? _sessionId;

  bool _isIndexed = false;
  String _indexStatusLabel = 'Checking…';

  final List<ChatMessage> _messages = [];

  int get _lectureId => widget.session.lectureId ?? 0;

  // ─── Lifecycle ─────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  // ─── Data loading ──────────────────────────────────────────────────────

  Future<void> _loadData() async {
    setState(() {
      isLoading = true;
      _isSending = false; // cancel any stale sending state
    });
    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);

      final status = await QAService.getIndexStatus(
        appState: appState,
        lectureId: _lectureId,
      );

      if (!mounted) return;

      _isIndexed = status.isIndexed && status.status == QAIndexStatus.ready;
      _indexStatusLabel = _statusLabel(status.status);

      if (_isIndexed) {
        await _loadHistory(appState);
      }
    } catch (e) {
      if (!mounted) return;
      _indexStatusLabel = 'Status unavailable';
      CustomErrorHandler.show(
        context,
        message: e.toString().replaceFirst('Exception: ', ''),
        type: ErrorType.fail,
      );
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  Future<void> _loadHistory(AppStateProvider appState) async {
    try {
      final history = await QAService.getHistory(
        appState: appState,
        lectureId: _lectureId,
      );
      if (!mounted) return;
      setState(() {
        _sessionId = history.sessionId;
        _messages
          ..clear()
          ..addAll(history.messages.map(ChatMessage.fromQAMessage));
      });
      _scrollToBottom();
    } catch (_) {
      // History is optional — silently ignore; user can still type
    }
  }

  String _statusLabel(QAIndexStatus s) {
    switch (s) {
      case QAIndexStatus.ready:
        return 'Ready';
      case QAIndexStatus.ingesting:
        return 'Preparing lecture content…';
      case QAIndexStatus.pending:
        return 'Pending indexing…';
      case QAIndexStatus.failed:
        return 'Indexing failed. Contact your teacher.';
    }
  }

  // ─── Actions ───────────────────────────────────────────────────────────

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isSending) return;

    // Add optimistic question bubble
    final optimisticQuestion = ChatMessage(
      text: text,
      sender: MessageSender.you,
    );

    setState(() {
      _isSending = true;
      _messages.add(optimisticQuestion);
      _messageController.clear();
    });
    _scrollToBottom();

    final appState = Provider.of<AppStateProvider>(context, listen: false);
    try {
      final response = await QAService.askQuestion(
        appState: appState,
        lectureId: _lectureId,
        text: text,
      );
      if (!mounted) return;
      setState(() {
        // Optimistic question bubble stays — just append the answer
        _messages.add(ChatMessage.fromQAMessage(response.answer));
        _sessionId ??= response.answer.sessionId;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      // Remove optimistic bubble on failure
      setState(() => _messages.remove(optimisticQuestion));
      CustomErrorHandler.show(
        context,
        message: e.toString().replaceFirst('Exception: ', ''),
        type: ErrorType.fail,
      );
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  Future<void> _sendVoiceMessage(File audioFile) async {
    if (_isSending) return;
    setState(() => _isSending = true);

    final appState = Provider.of<AppStateProvider>(context, listen: false);
    try {
      final response = await QAService.askQuestion(
        appState: appState,
        lectureId: _lectureId,
        voiceFile: audioFile,
      );
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage.fromQAMessage(response.question));
        _messages.add(ChatMessage.fromQAMessage(response.answer));
        _sessionId ??= response.answer.sessionId;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      CustomErrorHandler.show(
        context,
        message: e.toString().replaceFirst('Exception: ', ''),
        type: ErrorType.fail,
      );
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }

  void _raiseHand() {
    // TODO: call raise-hand API endpoint when available
    setState(() {
      if (_isInQueue) {
        _isInQueue = false;
        _queuePosition = null;
      } else {
        _isInQueue = true;
        _queuePosition = 1;
      }
    });
  }

  void _clearSession() {
    if (_sessionId == null) return;

    CustomConfirmationDialog.show(
      context,
      title: 'Clear Chat',
      message: 'This will delete all messages in this session. Are you sure?',
      confirmButtonText: 'Clear',
      cancelButtonText: 'Cancel',
      onConfirm: () async {
        CustomConfirmationDialog.dismiss(context);
        setState(() => isLoading = true);
        final appState = Provider.of<AppStateProvider>(context, listen: false);
        try {
          await QAService.clearSession(
            appState: appState,
            sessionId: _sessionId!,
          );
          if (!mounted) return;
          setState(() {
            _messages.clear();
            _sessionId = null;
          });
          CustomErrorHandler.show(
            context,
            message: 'Chat cleared.',
            type: ErrorType.success,
          );
        } catch (e) {
          if (!mounted) return;
          CustomErrorHandler.show(
            context,
            message: e.toString().replaceFirst('Exception: ', ''),
            type: ErrorType.fail,
          );
        } finally {
          if (mounted) setState(() => isLoading = false);
        }
      },
    );
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  // ─── Build ──────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Q&A Chat',
        actions: _sessionId != null
            ? [
                Padding(
                  padding: const EdgeInsets.only(right: AppStyles.spacingM),
                  child: IconButton(
                    tooltip: 'Clear chat',
                    icon: const Icon(Icons.delete_outline),
                    onPressed: _clearSession,
                  ),
                ),
              ]
            : null,
      ),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: LoadingOverlay(
        isLoading: isLoading,
        child: !isLoading && !_isIndexed
            ? _NotReadyState(label: _indexStatusLabel, onRetry: _loadData)
            : Column(
                children: [
                  // Teacher info strip
                  _TeacherStrip(session: widget.session),

                  // Queue position banner
                  if (_isInQueue && _queuePosition != null)
                    _QueueBanner(position: _queuePosition!),

                  // Messages list
                  Expanded(
                    child: RefreshIndicator(
                      onRefresh: _loadData,
                      child: _messages.isEmpty
                          ? _EmptyChat(teacherName: widget.session.teacherName)
                          : ListView.builder(
                              controller: _scrollController,
                              physics: const AlwaysScrollableScrollPhysics(),
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppStyles.spacingM,
                                vertical: AppStyles.spacingM,
                              ),
                              itemCount: _messages.length,
                              itemBuilder: (context, index) =>
                                  _MessageBubble(message: _messages[index]),
                            ),
                    ),
                  ),

                  // Bottom actions
                  _BottomBar(
                    controller: _messageController,
                    isInQueue: _isInQueue,
                    isSending: _isSending,
                    onRaiseHand: _raiseHand,
                    onSend: _sendMessage,
                    onVoiceSend: _sendVoiceMessage,
                  ),
                ],
              ),
      ),
    );
  }
}

// ─── Teacher Strip ────────────────────────────────────────────────────────────

class _TeacherStrip extends StatelessWidget {
  final ScheduleSlot session;
  const _TeacherStrip({required this.session});

  String _initials(String name) {
    final parts = name.trim().split(' ');
    if (parts.length >= 2) return '${parts[0][0]}${parts[1][0]}'.toUpperCase();
    if (parts.isNotEmpty && parts[0].isNotEmpty) {
      return parts[0][0].toUpperCase();
    }
    return '?';
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppStyles.spacingM,
        vertical: AppStyles.spacingS,
      ),
      color: isDark ? AppColors.darkBorder : AppColors.secondaryColor,
      child: Row(
        children: [
          CircleAvatar(
            radius: 18,
            backgroundColor: AppColors.primaryColor.withOpacity(0.35),
            child: Text(
              _initials(session.teacherName),
              style: AppStyles.bodyMedium.copyWith(
                color: AppColors.white,
                fontWeight: AppFonts.semiBold,
              ),
            ),
          ),
          const SizedBox(width: AppStyles.spacingS),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  session.teacherName,
                  style: AppStyles.bodyLarge.copyWith(
                    color: AppColors.white,
                    fontWeight: AppFonts.semiBold,
                  ),
                ),
                if (session.courseCode.isNotEmpty)
                  Text(
                    session.courseCode,
                    style: AppStyles.caption.copyWith(
                      color: AppColors.white.withOpacity(0.75),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Not Ready State ──────────────────────────────────────────────────────────

class _NotReadyState extends StatelessWidget {
  final String label;
  final VoidCallback onRetry;
  const _NotReadyState({required this.label, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: SizedBox(
        height: MediaQuery.of(context).size.height - 200,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingXL),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.hourglass_bottom_rounded,
                  size: 52,
                  color: AppColors.primaryColor,
                ),
                const SizedBox(height: AppStyles.spacingM),
                Text('Lecture not ready', style: AppStyles.h3),
                const SizedBox(height: AppStyles.spacingS),
                Text(
                  label,
                  style: AppStyles.bodyMedium.copyWith(
                    color: AppColors.textLight,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppStyles.spacingL),
                CustomButton(text: 'Retry', onPressed: onRetry),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ─── Empty State ──────────────────────────────────────────────────────────────

class _EmptyChat extends StatelessWidget {
  final String teacherName;
  const _EmptyChat({required this.teacherName});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: SizedBox(
        height: MediaQuery.of(context).size.height - 300,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppStyles.spacingXL),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 72,
                  height: 72,
                  decoration: BoxDecoration(
                    color: AppColors.primaryColor.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.chat_bubble_outline_rounded,
                    color: AppColors.primaryColor,
                    size: 36,
                  ),
                ),
                const SizedBox(height: AppStyles.spacingM),
                Text(
                  'Ask your question',
                  style: AppStyles.h3.copyWith(
                    color: isDark ? AppColors.textLight : AppColors.textBlack,
                  ),
                ),
                const SizedBox(height: AppStyles.spacingS),
                Text(
                  'Type your question below or raise your hand to speak directly with $teacherName\'s hologram avatar.',
                  textAlign: TextAlign.center,
                  style: AppStyles.bodyMedium.copyWith(
                    color: isDark
                        ? AppColors.darkTextSecondary
                        : AppColors.textLight,
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

// ─── Queue Banner ─────────────────────────────────────────────────────────────

class _QueueBanner extends StatelessWidget {
  final int position;
  const _QueueBanner({required this.position});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        vertical: AppStyles.spacingS,
        horizontal: AppStyles.spacingM,
      ),
      color: isDark
          ? AppColors.darkBorder
          : AppColors.primaryColor.withOpacity(0.08),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.people_outline,
            size: 16,
            color: AppColors.primaryColor,
          ),
          const SizedBox(width: AppStyles.spacingXS),
          RichText(
            text: TextSpan(
              style: AppStyles.bodyMedium.copyWith(
                color: AppColors.primaryColor,
              ),
              children: [
                const TextSpan(text: 'YOUR QUESTION QUEUE POSITION: '),
                TextSpan(
                  text: '#$position',
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Message Bubble ───────────────────────────────────────────────────────────

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isYou = message.sender == MessageSender.you;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppStyles.spacingM),
      child: Column(
        crossAxisAlignment: isYou
            ? CrossAxisAlignment.end
            : CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(
              bottom: AppStyles.spacingXS,
              left: AppStyles.spacingXS,
              right: AppStyles.spacingXS,
            ),
            child: Text(
              isYou ? 'YOU' : 'HOLOGRAM AVATAR',
              style: AppStyles.caption.copyWith(
                fontWeight: AppFonts.semiBold,
                letterSpacing: 0.5,
                color: isYou
                    ? AppColors.primaryColor
                    : (isDark
                          ? AppColors.darkTextSecondary
                          : AppColors.textLight),
              ),
            ),
          ),
          Row(
            mainAxisAlignment: isYou
                ? MainAxisAlignment.end
                : MainAxisAlignment.start,
            children: [
              Flexible(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppStyles.spacingM,
                    vertical: AppStyles.spacingS + 2,
                  ),
                  decoration: isYou
                      ? BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [
                              AppColors.primaryColor,
                              AppColors.secondaryColor,
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(AppStyles.radiusM),
                            topRight: Radius.circular(AppStyles.radiusM),
                            bottomLeft: Radius.circular(AppStyles.radiusM),
                            bottomRight: Radius.circular(4.0),
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.primaryColor.withOpacity(0.3),
                              blurRadius: 8,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        )
                      : BoxDecoration(
                          color: isDark ? AppColors.darkCard : AppColors.white,
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(AppStyles.radiusM),
                            topRight: Radius.circular(AppStyles.radiusM),
                            bottomRight: Radius.circular(AppStyles.radiusM),
                            bottomLeft: Radius.circular(4.0),
                          ),
                          boxShadow: AppStyles.cardShadow,
                        ),
                  child: Text(
                    message.text,
                    style: AppStyles.bodyMedium.copyWith(
                      color: isYou
                          ? AppColors.white
                          : (isDark
                                ? AppColors.textLight
                                : AppColors.textBlack),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ─── Bottom Bar ───────────────────────────────────────────────────────────────

class _BottomBar extends StatelessWidget {
  final TextEditingController controller;
  final bool isInQueue;
  final bool isSending;
  final VoidCallback onRaiseHand;
  final Future<void> Function() onSend;
  final Future<void> Function(File) onVoiceSend;

  const _BottomBar({
    required this.controller,
    required this.isInQueue,
    required this.isSending,
    required this.onRaiseHand,
    required this.onSend,
    required this.onVoiceSend,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surfaceColor = isDark ? AppColors.darkCard : AppColors.white;
    final borderColor = isDark
        ? AppColors.darkBorder
        : AppColors.gray.withOpacity(0.2);

    return Container(
      decoration: BoxDecoration(
        color: surfaceColor,
        border: Border(top: BorderSide(color: borderColor, width: 1)),
      ),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppStyles.spacingM,
            AppStyles.spacingM,
            AppStyles.spacingM,
            AppStyles.spacingS,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Raise Hand button
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: onRaiseHand,
                  icon: Icon(
                    isInQueue ? Icons.back_hand : Icons.back_hand_outlined,
                    size: 18,
                    color: isInQueue ? AppColors.white : AppColors.primaryColor,
                  ),
                  label: Text(
                    isInQueue ? 'LEAVE QUEUE' : 'RAISE HAND FOR QUEUE',
                    style: AppStyles.button.copyWith(
                      color: isInQueue
                          ? AppColors.white
                          : AppColors.primaryColor,
                      letterSpacing: 0.5,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    backgroundColor: isInQueue
                        ? AppColors.primaryColor
                        : Colors.transparent,
                    side: const BorderSide(
                      color: AppColors.primaryColor,
                      width: 1.5,
                    ),
                    padding: const EdgeInsets.symmetric(
                      vertical: AppStyles.spacingM,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppStyles.radiusPill),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: AppStyles.spacingS),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: controller,
                      onSubmitted: (_) => onSend(),
                      enabled: !isSending,
                      style: AppStyles.bodyMedium.copyWith(
                        color: isDark
                            ? AppColors.textLight
                            : AppColors.textBlack,
                      ),
                      decoration: InputDecoration(
                        hintText: 'Type your question...',
                        hintStyle: AppStyles.caption,
                        filled: true,
                        fillColor: isDark
                            ? AppColors.darkBackground
                            : AppColors.lightBackground,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(
                            AppStyles.radiusPill,
                          ),
                          borderSide: BorderSide.none,
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(
                            AppStyles.radiusPill,
                          ),
                          borderSide: BorderSide.none,
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(
                            AppStyles.radiusPill,
                          ),
                          borderSide: const BorderSide(
                            color: AppColors.primaryColor,
                            width: 1.5,
                          ),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: AppStyles.spacingM,
                          vertical: AppStyles.spacingS + 2,
                        ),
                        suffixIcon: _MicButton(onVoiceSend: onVoiceSend),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppStyles.spacingS),
                  _SendButton(onPressed: onSend, isLoading: isSending),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Mic Button ───────────────────────────────────────────────────────────────

class _MicButton extends StatelessWidget {
  final Future<void> Function(File) onVoiceSend;
  const _MicButton({required this.onVoiceSend});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: AppStyles.spacingXS),
      child: GestureDetector(
        onTap: () {
          // TODO: record with `record` package then call onVoiceSend(File(path))
        },
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: AppColors.primaryColor.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.mic_outlined,
            color: AppColors.primaryColor,
            size: 20,
          ),
        ),
      ),
    );
  }
}

// ─── Send Button ──────────────────────────────────────────────────────────────

class _SendButton extends StatelessWidget {
  final Future<void> Function() onPressed;
  final bool isLoading;

  const _SendButton({required this.onPressed, this.isLoading = false});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: isLoading ? null : onPressed,
      child: Container(
        width: 48,
        height: 48,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              isLoading ? AppColors.gray : AppColors.primaryColor,
              isLoading ? AppColors.gray : AppColors.secondaryColor,
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          shape: BoxShape.circle,
          boxShadow: isLoading
              ? []
              : [
                  BoxShadow(
                    color: AppColors.primaryColor.withOpacity(0.35),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
        ),
        child: isLoading
            ? const Padding(
                padding: EdgeInsets.all(14),
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.white,
                ),
              )
            : const Icon(Icons.send_rounded, color: AppColors.white, size: 22),
      ),
    );
  }
}
