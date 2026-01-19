// lib/widgets/custom_confirmation_dialog.dart
import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import 'button_widget.dart';

class CustomConfirmationDialog extends StatelessWidget {
  final String? title;
  final String message;
  final String confirmButtonText;
  final String cancelButtonText;
  final VoidCallback onConfirm;
  final VoidCallback? onCancel;
  final ButtonType confirmButtonType;

  const CustomConfirmationDialog({
    super.key,
    this.title,
    required this.message,
    required this.confirmButtonText,
    required this.onConfirm,
    this.cancelButtonText = 'Cancel',
    this.onCancel,
    this.confirmButtonType = ButtonType.primary,
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: title != null
          ? Text(
              title!,
              style: AppStyles.h2.copyWith(color: AppColors.lightBlue),
            )
          : null,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            message,
            style: AppStyles.h3,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppStyles.spacingM),
          CustomButton(
            text: confirmButtonText,
            fullWidth: true,
            buttonType: confirmButtonType,
            onPressed: onConfirm,
          ),
          const SizedBox(height: AppStyles.spacingM),
          CustomButton(
            onPressed: onCancel ?? () => Navigator.pop(context),
            text: cancelButtonText,
            buttonType: ButtonType.secondary,
            fullWidth: true,
          ),
        ],
      ),
    );
  }

  // Static method to show the dialog easily
  static Future<void> show(
    BuildContext context, {
    required String title,
    required String message,
    required String confirmButtonText,
    required VoidCallback onConfirm,
    String cancelButtonText = 'Cancel',
    VoidCallback? onCancel,
    ButtonType confirmButtonType = ButtonType.primary,
  }) {
    return showDialog(
      context: context,
      builder: (context) => CustomConfirmationDialog(
        title: title,
        message: message,
        confirmButtonText: confirmButtonText,
        onConfirm: onConfirm,
        cancelButtonText: cancelButtonText,
        onCancel: onCancel,
        confirmButtonType: confirmButtonType,
      ),
    );
  }
}