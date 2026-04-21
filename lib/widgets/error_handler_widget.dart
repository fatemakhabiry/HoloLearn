import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';

enum ErrorType {
  fail,
  success,
  info,
}

class CustomErrorHandler {
  static void show(
    BuildContext context, {
    required String message,
    required ErrorType type,
    Duration duration = const Duration(seconds: 3),
  }) {
    Color backgroundColor;
    IconData icon;

    switch (type) {
      case ErrorType.fail:
        backgroundColor = AppColors.error;
        icon = Icons.error_outline;
        break;
      case ErrorType.success:
        backgroundColor = AppColors.success;
        icon = Icons.check_circle_outline;
        break;
      case ErrorType.info:
        backgroundColor = AppColors.darkBlue;
        icon = Icons.info_outline;
        break;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(icon, color: AppColors.white),
            const SizedBox(width: AppStyles.spacingM),
            Expanded(
              child: Text(
                message,
                style: AppStyles.bodyMedium.copyWith(
                  color: AppColors.white,
                ),
              ),
            ),
          ],
        ),
        backgroundColor: backgroundColor,
        // behavior: SnackBarBehavior.fixed,
        duration: duration,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppStyles.radiusM),
        ),
        margin: const EdgeInsets.all(AppStyles.spacingM),
      ),
    );
  }
}