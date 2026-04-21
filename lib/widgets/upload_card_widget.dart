import 'package:flutter/material.dart';
import '../widgets/button_widget.dart';
import 'dart:io';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';

class UpoladCard extends StatelessWidget {
  final String stepNumber;
  final IconData icon;
  final String? iconLabel;
  final String primaryButtonText;
  final String? secondaryButtonText;
  final String subtext;
  final VoidCallback onPrimaryPressed;
  final VoidCallback? onSecondaryPressed;
  final bool hasFile;
  final bool isRecording;
  final bool isDashed;
  final File? photoFile;
  const UpoladCard({
    required this.stepNumber,
    required this.icon,
    this.iconLabel,
    required this.primaryButtonText,
    this.secondaryButtonText,
    required this.subtext,
    required this.onPrimaryPressed,
    this.onSecondaryPressed,
    required this.hasFile,
    this.isRecording = false,
    this.isDashed = false,
    this.photoFile,
  });

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final cardMaxWidth = (screenWidth / 2) - 40;
    return Container(
      constraints: BoxConstraints(maxWidth: cardMaxWidth),
      height: 550,
      padding: const EdgeInsets.all(AppStyles.spacingL),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        boxShadow: AppStyles.cardShadow,
      ),
      child: Column(
        children: [
          // Step Number
          Text('Step $stepNumber', style: AppStyles.h2),
          const SizedBox(height: AppStyles.spacingS),
            Container(
              width: 200,
              height: 200,
              decoration: BoxDecoration(
                shape: isDashed ? BoxShape.rectangle : BoxShape.circle,
                borderRadius: isDashed ? BorderRadius.circular(AppStyles.radiusM) : null,
                border: Border.all(
                  color: isDashed ? AppColors.gray : AppColors.primaryColor,
                  width:2,
                  strokeAlign: BorderSide.strokeAlignInside,
                ),
                color: isDashed ? Colors.transparent : null,
              ),
              child: isDashed
                  ? Center(
                      child: Text(
                        iconLabel!,
                        style: AppStyles.h2.copyWith(color: AppColors.gray),
                      ),
                    )
                  : Icon(
                      icon,
                      size: 40,
                      color:  AppColors.primaryColor
                    ),
            ),
          const SizedBox(height: AppStyles.spacingM),
          // Primary Button
          SizedBox(
            child: CustomButton(
              text: primaryButtonText,
              onPressed: onPrimaryPressed,
            ),
            // child: Text(
            //   isRecording ? 'STOP RECORDING' : primaryButtonText,
            //   style: const TextStyle(
            //     fontSize: 14,
            //     fontWeight: FontWeight.w600,
            //     letterSpacing: 0.5,
            //   ),
          ),
          //   ),
          // ),
          // Secondary Button (if exists)
          if (secondaryButtonText != null) ...[
            const SizedBox(height:AppStyles.spacingS),
            CustomButton(
              buttonType: ButtonType.secondary,
              onPressed: onSecondaryPressed!,
              text: secondaryButtonText!,
            ),
          ],

          const SizedBox(height: AppStyles.spacingS),
          // Subtext
          Text(subtext, textAlign: TextAlign.center, style: AppStyles.caption),
        ],
      ),
    );
  }
}
