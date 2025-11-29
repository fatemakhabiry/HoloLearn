import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/constants/app_fonts.dart';

class MessageDisplay extends StatelessWidget {
  final String massegeBannerSuccess;
  final String massegeBannerFail;
  final String message;
  final VoidCallback? onDismiss;

  const MessageDisplay({super.key,required this.massegeBannerSuccess,required this.massegeBannerFail, required this.message, this.onDismiss});

  @override
  Widget build(BuildContext context) {
    if (message.isEmpty) return const SizedBox.shrink();

    final isSuccess = message.contains("Success");
    final messageColor = isSuccess ? AppColors.success : AppColors.error;
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
          // Icon
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: messageColor,
              shape: BoxShape.circle,
            ),
            child: Icon(
              isSuccess ? Icons.check : Icons.close,
              color: Colors.white,
              size: 16,
            ),
          ),
          const SizedBox(width: 12),
          // Text Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isSuccess ? massegeBannerSuccess : massegeBannerFail,
                  style: AppStyles.bodySmall.copyWith(
                    color: messageColor,
                    fontWeight: AppFonts.bold,
                  ),
                ),
                const SizedBox(height: 4),
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

// Usage in your LoginPage:
// if (message.isNotEmpty) ...[
//   const SizedBox(height: AppStyles.spacingL),
//   MessageDisplay(
//     message: message,
//     onDismiss: () => setState(() => message = ''),
//   ),
// ],
