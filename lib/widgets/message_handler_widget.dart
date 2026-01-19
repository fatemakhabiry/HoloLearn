import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../constants/app_fonts.dart';

class MessageDisplay extends StatelessWidget {
  final String? massegeBanner;
  final String message;
  final VoidCallback? onDismiss;
  final bool isSuccess;
  final bool isInfo;
  final bool showIcon;

  const MessageDisplay({
    super.key,
    this.massegeBanner,
    required this.message,
    this.onDismiss,
    this.isInfo = false,
    this.isSuccess = false,
    this.showIcon = true,
  });

  @override
  Widget build(BuildContext context) {
    if (message.isEmpty) return const SizedBox.shrink();

    // Add info message type support
    final Color messageColor;

    if (isInfo) {
      messageColor = Colors.blue; // Info color
    } else {
      messageColor = isSuccess ? AppColors.success : AppColors.error;
    }

    final backgroundColor = messageColor.withOpacity(0.1);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppStyles.spacingM),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(AppStyles.radiusM),
        border: Border.all(color: messageColor, width: 1),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Icon - MODIFIED: Only show if showIcon is true
          if (showIcon)
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: messageColor,
                shape: BoxShape.circle,
              ),
              child: Icon(
                isInfo ? Icons.info : (isSuccess ? Icons.check : Icons.close),
                color: Colors.white,
                size: 16,
              ),
            ),
          if (showIcon) const SizedBox(width: 12),
          // Text Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // MODIFIED: Only show banner title if it's not empty
                if ((massegeBanner != null && massegeBanner!.isNotEmpty)) ...[
                  Text(
                    massegeBanner!,
                    style: AppStyles.bodySmall.copyWith(
                      color: messageColor,
                      fontWeight: AppFonts.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                ],
                Text(
                  message,
                  style: AppStyles.bodySmall.copyWith(
                    color: messageColor.withOpacity(0.8),
                    fontWeight: AppFonts.medium,
                  ),
                ),
              ],
            ),
          ),
          // Close button
          if (onDismiss != null)
            GestureDetector(
              onTap: onDismiss,
              child: Icon(Icons.close, size: 18, color: messageColor),
            ),
        ],
      ),
    );
  }
}
