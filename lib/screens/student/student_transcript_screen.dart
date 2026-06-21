import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../constants/constants.dart';
import '../../models/transcript_models.dart';
import '../../models/schedule_models.dart';
import '../../providers/app_state_provider.dart';
import '../../services/transcript_service.dart';
import '../../widgets/widgets.dart';

class StudentTranscriptScreen extends StatefulWidget {
  final ScheduleSlot session;

  const StudentTranscriptScreen({super.key, required this.session});

  @override
  State<StudentTranscriptScreen> createState() =>
      _StudentTranscriptScreenState();
}

class _StudentTranscriptScreenState extends State<StudentTranscriptScreen> {
  List<TranscriptSegment> _segments = [];
  bool _isLoading = true;
  String? _errorMessage;

  int get _lectureId => widget.session.lectureId ?? 0;

  @override
  void initState() {
    super.initState();
    _loadTranscript();
  }

  Future<void> _loadTranscript() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final segments = await TranscriptService.getTranscript(
        appState: appState,
        lectureId: _lectureId,
      );
      if (!mounted) return;
      setState(() => _segments = segments);
    } catch (e) {
      if (!mounted) return;
      setState(
        () => _errorMessage = e.toString().replaceFirst('Exception: ', ''),
      );
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: const CustomAppBar(title: 'Transcript'),
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: LoadingOverlay(
        isLoading: _isLoading,
        child: _errorMessage != null
            ? _ErrorState(message: _errorMessage!, onRetry: _loadTranscript)
            : _segments.isEmpty
            ? const _EmptyState()
            : RefreshIndicator(
                onRefresh: _loadTranscript,
                child: ListView.separated(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppStyles.spacingM,
                    vertical: AppStyles.spacingL,
                  ),
                  itemCount: _segments.length,
                  separatorBuilder: (_, __) =>
                      const SizedBox(height: AppStyles.spacingM),
                  itemBuilder: (context, index) => _TranscriptTile(
                    segment: _segments[index],
                    isDark: isDark,
                  ),
                ),
              ),
      ),
    );
  }
}

// ─── Transcript Tile ──────────────────────────────────────────────────────────

class _TranscriptTile extends StatelessWidget {
  final TranscriptSegment segment;
  final bool isDark;

  const _TranscriptTile({required this.segment, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Timestamp pill
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppStyles.spacingS + 2,
            vertical: 3,
          ),
          decoration: BoxDecoration(
            color: AppColors.primaryColor.withOpacity(0.12),
            borderRadius: BorderRadius.circular(AppStyles.radiusPill),
          ),
          child: Text(
            segment.timestamp,
            style: AppStyles.caption.copyWith(
              color: AppColors.primaryColor,
              fontWeight: AppFonts.semiBold,
              fontSize: AppFonts.fontSizeXXS,
            ),
          ),
        ),
        const SizedBox(height: AppStyles.spacingXS + 2),
        // Segment text
        Text(
          segment.text,
          style: AppStyles.bodyMedium.copyWith(
            color: isDark ? AppColors.textLight : AppColors.textBlack,
            height: 1.55,
          ),
        ),
      ],
    );
  }
}

// ─── Error State ──────────────────────────────────────────────────────────────

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppStyles.spacingXL),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.error_outline_rounded,
              size: 52,
              color: AppColors.primaryColor,
            ),
            const SizedBox(height: AppStyles.spacingM),
            Text('Could not load transcript', style: AppStyles.h3),
            const SizedBox(height: AppStyles.spacingS),
            Text(
              message,
              style: AppStyles.bodyMedium.copyWith(color: AppColors.textLight),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppStyles.spacingL),
            CustomButton(text: 'Retry', onPressed: onRetry),
          ],
        ),
      ),
    );
  }
}

// ─── Empty State ──────────────────────────────────────────────────────────────

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Center(
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
                Icons.subtitles_off_outlined,
                color: AppColors.primaryColor,
                size: 36,
              ),
            ),
            const SizedBox(height: AppStyles.spacingM),
            Text('No transcript yet', style: AppStyles.h3),
            const SizedBox(height: AppStyles.spacingS),
            Text(
              'The transcript will be available once the lecture is processed.',
              textAlign: TextAlign.center,
              style: AppStyles.bodyMedium.copyWith(color: AppColors.textLight),
            ),
          ],
        ),
      ),
    );
  }
}
