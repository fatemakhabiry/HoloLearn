import 'package:flutter/material.dart';
import 'package:hololearn/widgets/button_widget.dart';
import 'dart:io';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';

class UpoladCard extends StatelessWidget {
  late String stepNumber;
  late IconData icon;
  late String iconLabel;
  late String primaryButtonText;
  late String? secondaryButtonText;
  late String subtext;
  late VoidCallback onPrimaryPressed;
  late VoidCallback? onSecondaryPressed;
  late bool hasFile;
  late bool isRecording;
  late bool isDashed;
  late File? photoFile;
  UpoladCard({
    required String stepNumber,
    required IconData icon,
    required String iconLabel,
    required String primaryButtonText,
    String? secondaryButtonText,
    required String subtext,
    required VoidCallback onPrimaryPressed,
    VoidCallback? onSecondaryPressed,
    required bool hasFile,
    bool isRecording = false,
    bool isDashed = false,
    File? photoFile,
  });



     @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final cardMaxWidth = (screenWidth / 2) - 40;
    return Container(
      constraints: BoxConstraints(
        maxWidth: cardMaxWidth,
      ),
      padding: const EdgeInsets.all(AppStyles.spacingL),
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(AppStyles.radiusXL),
            boxShadow: AppStyles.cardShadow
          ),
      child: Column(
        children: [
          // Step Number
          Text(
            stepNumber,
            style: AppStyles.h2
          ),
          const SizedBox(height: 24),
          // Icon or Photo
          if (photoFile != null && isDashed)
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.file(
                photoFile!,
                width: 200,
                height: 200,
                fit: BoxFit.cover,
              ),
            )
          else
            Container(
              width: isDashed ? 200 : 80,
              height: isDashed ? 200 : 80,
              decoration: BoxDecoration(
                shape: isDashed ? BoxShape.rectangle : BoxShape.circle,
                borderRadius: isDashed ? BorderRadius.circular(12) : null,
                border: Border.all(
                  color: isDashed ? AppColors.gray : AppColors.darkBlue,
                  width: isDashed ? 2 : 3,
                  strokeAlign: BorderSide.strokeAlignInside,
                ),
                color: isDashed ? Colors.transparent : null,
              ),
              child: isDashed
                  ? Center(
                      child: Text(
                        iconLabel,
                        style:AppStyles.h2.copyWith(color: AppColors.gray),
                      ),
                    )
                  : Center(
                      child: Text(
                        iconLabel,
                        style:AppStyles.h2,
                      ),
                    ),
            ),
          const SizedBox(height: 24),
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
            const SizedBox(height: 12),
            CustomButton(
              buttonType: ButtonType.secondary,
              onPressed: onSecondaryPressed!,
              text: secondaryButtonText!,
            ),
          ],
          const SizedBox(height: 16),
          // Subtext
          Text(
            subtext,
            textAlign: TextAlign.center,
            style: AppStyles.caption,
          ),
        ],
      ),
    );
  }
}
