import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';

class LectureScheduleCard extends StatelessWidget {
  final String lectureTitle;
  final String? date;
  final String? timeRange;
  final String editButtonText;
  final String cancelButtonText;
  final VoidCallback? onEdit;
  final VoidCallback? onCancel;

  const LectureScheduleCard({
    super.key,
    required this.lectureTitle,
    this.date,
    this.timeRange,
    this.editButtonText='EDIT',
    this.cancelButtonText='CANCEL',
    this.onEdit,
    this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppStyles.spacingL),
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
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: onEdit,
                  style: ElevatedButton.styleFrom(
                    foregroundColor: AppColors.gray,
                    // side: const BorderSide(
                    //   width: 1,
                    //   color: AppColors.gray
                    // ),
                    padding: const EdgeInsets.symmetric(
                      vertical: AppStyles.spacingS,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppStyles.radiusS),
                    ),
                  ),
                  child: Text(
                    editButtonText,
                    style: AppStyles.bodyMedium.copyWith(
                      fontWeight: AppFonts.regular,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: AppStyles.spacingM),
              Expanded(
                child: OutlinedButton(
                  onPressed: onCancel,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.textBlack,
                    side: const BorderSide(
                      color: AppColors.textBlack,
                      width: 1,
                    ),
                    padding: const EdgeInsets.symmetric(
                      vertical: AppStyles.spacingS,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppStyles.radiusS),
                    ),
                  ),
                  child: Text(
                    cancelButtonText,
                    style: AppStyles.bodyMedium.copyWith(
                      fontWeight: AppFonts.semiBold,
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
