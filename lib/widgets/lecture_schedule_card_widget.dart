import 'package:flutter/material.dart';
import 'package:hololearn/widgets/button_widget.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';

class LectureScheduleCard extends StatelessWidget {
  final String lectureTitle;
  final String? date;
  final String? timeRange;
  final String? status;
  final String? lectureType; // ← add
  final String editButtonText;
  final String cancelButtonText;
  final VoidCallback? onEdit;
  final VoidCallback? onCancel;
  final VoidCallback? onViewContent;

  const LectureScheduleCard({
    super.key,
    required this.lectureTitle,
    this.date,
    this.timeRange,
    this.status,
    this.lectureType, // ← add
    this.editButtonText = 'EDIT',
    this.cancelButtonText = 'CANCEL',
    this.onEdit,
    this.onCancel,
    this.onViewContent,
  });

bool _hasContent() =>
    onViewContent != null; // ← both types have content now


  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppStyles.spacingM),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppStyles.radiusM),
        boxShadow: AppStyles.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Lecture Title
          Text(
            lectureTitle,
            style: AppStyles.bodyLarge.copyWith(fontWeight: AppFonts.bold),
          ),
          const SizedBox(height: AppStyles.spacingS),

          // Date and Time
          Text(
            '$date . $timeRange',
            style: AppStyles.bodyMedium.copyWith(color: AppColors.textLight),
          ),

          const SizedBox(height: AppStyles.spacingL),

          // Action Buttons

          // Action Buttons
          Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: CustomButton(
                      text: editButtonText,
                      onPressed: onEdit!,
                      buttonType: ButtonType.secondary,
                      fullWidth: true,
                    ),
                  ),
                  const SizedBox(width: AppStyles.spacingM),
                  Expanded(
                    child: CustomButton(
                      text: cancelButtonText,
                      onPressed: onCancel!,
                      buttonType: ButtonType.outlined,
                      fullWidth: true,
                    ),
                  ),
                ],
              ),
              if (_hasContent()) ...[
                const SizedBox(height: AppStyles.spacingM),
                CustomButton(
                  text: 'VIEW CONTENT',
                  prefixIcon: Icon(
                    Icons.folder_open_outlined,
                    color: AppColors.white,
                  ),
                  onPressed: onViewContent!,
                  buttonType: ButtonType.primary,
                  fullWidth: true,
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
