import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

 import '../constants/constants.dart';
import '../models/lecture_models.dart';
import '../state/processing_notifier.dart';

class ProcessingNotificationBar extends StatelessWidget {
  final VoidCallback? onAwait;
  final VoidCallback? onDone;
  final VoidCallback? ontap;

  const ProcessingNotificationBar({super.key, this.onAwait, this.onDone, this.ontap});

  @override
  Widget build(BuildContext context) {
    return Consumer<ProcessingNotifier>(
      builder: (context, notifier, _, ) {
        if (!notifier.isActive) return const SizedBox.shrink();

        final isFailed = notifier.lifecycle == ProcessingLifecycle.failed;
        final isAwaiting = notifier.isAwaitingApproval;
        final isDone = notifier.isDone;

        // 🔥 Trigger onDone callback once finished
        if (notifier.isDone && onDone != null) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            onDone!;
          });
        }

        Color barColor = AppColors.primaryColor;
        if (notifier.isDone) barColor = AppColors.success;
        if (isFailed) barColor = AppColors.error;

        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: AppStyles.spacingM),
          padding: const EdgeInsets.symmetric(
            horizontal: AppStyles.spacingM,
            vertical: AppStyles.spacingS,
          ),
          decoration: BoxDecoration(
            color: Theme.of(context).scaffoldBackgroundColor,
            border: Border.all(color: barColor,width: 1.5),
            borderRadius: BorderRadius.circular(AppStyles.radiusPill),
          ),
          child: Row(
            children: [
              // ── Status icon ──────────────────────────────────────
              if (isDone || isAwaiting)
                Icon(Icons.check_sharp, color: barColor, size: 24)
              else if (isFailed)
                Icon(Icons.error_outline, color: barColor, size: 24)
              else
                SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: barColor,
                  ),
                ),

              const SizedBox(width: AppStyles.spacingM),

              // ── Label ────────────────────────────────────────────
              Expanded(
                child: GestureDetector(
                  onTap: ontap,
                  child: Text(
                    isFailed
                        ? 'Generation failed. Dismiss to clear.'
                        : notifier.Title.isEmpty
                        ? 'Lecture is being generated…'
                        : notifier.Title,
                    style: AppStyles.bodyMedium.copyWith(color: barColor),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),

              // ── Review button ────────────────────────────────────
              if (isAwaiting || isDone)
                GestureDetector(
                  onTap: isAwaiting ? onAwait : onDone,
                  child: Container(
                    margin: const EdgeInsets.only(right: AppStyles.spacingS),
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppStyles.spacingS,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: barColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(AppStyles.radiusPill),
                    ),
                    child: Text(
                      'Review',
                      style: AppStyles.caption.copyWith(
                        color: barColor,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),

              // ── Dismiss ──────────────────────────────────────────
              GestureDetector(
                onTap: () => notifier.dismiss(),
                child: Icon(Icons.close, color: barColor, size: 18),
              ),
            ],
          ),
        );
      },
    );
  }
}
