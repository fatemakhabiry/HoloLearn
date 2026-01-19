import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';

class ReservedTimeCard extends StatelessWidget {
  final String timeRange;
  final String reservedBy;

  const ReservedTimeCard({
    super.key,
    required this.timeRange,
    required this.reservedBy,
  });

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
          Text(
            timeRange,
            style: AppStyles.bodyLarge.copyWith(fontWeight: AppFonts.bold),
          ),
          const SizedBox(height: AppStyles.spacingXS),
          Text(
            reservedBy,
            style: AppStyles.bodyMedium.copyWith(color: AppColors.textLight),
          ),
        ],
      ),
    );
  }
}
