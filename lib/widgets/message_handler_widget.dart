import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';
import 'package:hololearn/constants/app_fonts.dart';

class MessageDisplay extends StatelessWidget {
  final String massegeBannerSuccess;
  final String massegeBannerFail;
  final String message;
  final VoidCallback? onDismiss;
  final bool isInfo; // NEW: Add this parameter
  final bool showIcon; // NEW: Add this parameter

  const MessageDisplay({
    super.key,
    required this.massegeBannerSuccess,
    required this.massegeBannerFail,
    required this.message,
    this.onDismiss,
    this.isInfo = false, // NEW: Default to false
    this.showIcon = true, // NEW: Default to true
  });

  @override
  Widget build(BuildContext context) {
    if (message.isEmpty) return const SizedBox.shrink();


    // MODIFIED: Add info message type support
    final bool isSuccess = message.contains("Success");
    final Color messageColor;

    if (isInfo) {
      messageColor = Colors.blue; // Info color
    } else {
      messageColor = isSuccess ? AppColors.success : AppColors.error;
    }

    final backgroundColor = messageColor;
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
                if ((isSuccess && massegeBannerSuccess.isNotEmpty) ||
                    (!isSuccess &&
                        !isInfo &&
                        massegeBannerFail.isNotEmpty)) ...[
                  Text(
                    isSuccess ? massegeBannerSuccess : massegeBannerFail,
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
                    color: messageColor,
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

// ===== USAGE EXAMPLES =====

// 1. Info message (like Figma design - no icon, no title)
// MessageDisplay(
//   massegeBannerSuccess: '',
//   massegeBannerFail: '',
//   message: 'To reset your password, please fill out the form below. We will send you a password to your email address within a few minutes.',
//   isInfo: true,
//   showIcon: false,
// )

// 2. Success message with title and icon (original behavior)
// MessageDisplay(
//   massegeBannerSuccess: 'Success',
//   massegeBannerFail: 'Error',
//   message: 'Success: Your password has been reset!',
//   onDismiss: () => setState(() => message = ''),
// )

// 3. Error message with title and icon (original behavior)
// MessageDisplay(
//   massegeBannerSuccess: 'Success',
//   massegeBannerFail: 'Error',
//   message: 'Failed to reset password.',
//   onDismiss: () => setState(() => message = ''),
// )

// 4. Info message with icon
// MessageDisplay(
//   massegeBannerSuccess: '',
//   massegeBannerFail: '',
//   message: 'Please check your email for verification.',
//   isInfo: true,
//   showIcon: true,
// )
