import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';


class CustomProgressBar extends StatelessWidget {
  final double progress; // 0.0 to 1.0
  final Color progressColor;
  final double height;
  final bool showPercentage;
  final TextStyle? percentageStyle;

  const CustomProgressBar({
    super.key,
    required this.progress,
    this.progressColor = AppColors.primaryColor,
    this.height = 8,
    this.showPercentage = true,
    this.percentageStyle,
  });

  @override
  Widget build(BuildContext context) {
    final percentage = (progress * 100).toInt();

    return Row(
      children: [
        Expanded(
          child: Container(
            height: height,
            decoration: BoxDecoration(
              color: Theme.of(context).scaffoldBackgroundColor,
              borderRadius: BorderRadius.circular(height / 2),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(height / 2),
              child: LinearProgressIndicator(
                value: progress,
                backgroundColor: Colors.transparent,
                valueColor: AlwaysStoppedAnimation<Color>(progressColor),
                minHeight: height,
              ),
            ),
          ),
        ),
        if (showPercentage) ...[
          const SizedBox(width: 16),
          Text(
            '$percentage%',
            style: percentageStyle ?? AppStyles.labelStyle.copyWith(fontWeight: AppFonts.bold),
                
          ),
        ],
      ],
    );
  }
}