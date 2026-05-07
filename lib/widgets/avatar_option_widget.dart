import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_themes.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';

/// Generic model for any selectable option
class SelectableOption {
  final String id;
  final String title;
  final String description;

  const SelectableOption({
    required this.id,
    required this.title,
    required this.description,
  });
}

/// Truly reusable radio options group widget
/// Can be used for avatars, settings, preferences, or any radio selection
class RadioOptionsGroup extends StatelessWidget {
  final String? sectionTitle;
  final String selectedId;
  final List<SelectableOption> options;
  final Function(String) onOptionSelected;

  const RadioOptionsGroup({
    super.key,
    this.sectionTitle,
    required this.selectedId,
    required this.options,
    required this.onOptionSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (sectionTitle != null)
          Padding(
            padding: const EdgeInsets.only(
              bottom: AppStyles.spacingM,
              top: AppStyles.spacingL,
            ),
            child: Text(
              sectionTitle!,
              style: AppStyles.labelStyle.copyWith(
                fontWeight: AppFonts.bold,
                fontSize: AppFonts.fontSizeXS,
                letterSpacing: 1.2,
                color: context.textSecondary
              ),
            ),
          ),
        ...options.map((option) {
          return GestureDetector(
            onTap: () => onOptionSelected(option.id),
            child: Container(
              margin: const EdgeInsets.only(bottom: AppStyles.spacingM),
              padding: const EdgeInsets.all(AppStyles.spacingM),
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                border: Border.all(
                  color: selectedId == option.id
                      ? AppColors.primaryColor
                      : AppColors.gray.withOpacity(0.3),
                  width: selectedId == option.id ? 2 : 1,
                ),
                borderRadius: BorderRadius.circular(AppStyles.radiusM),
              ),
              child: Row(
                children: [
                  // Radio Button
                  Container(
                    width: 20,
                    height: 20,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: selectedId == option.id
                            ? AppColors.primaryColor
                            : AppColors.gray,
                        width: 2,
                      ),
                    ),
                    child: selectedId == option.id
                        ? Center(
                            child: Container(
                              width: 10,
                              height: 10,
                              decoration: const BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppColors.primaryColor,
                              ),
                            ),
                          )
                        : null,
                  ),
                  const SizedBox(width: AppStyles.spacingM),
                  // Text Content
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          option.title,
                          style: AppStyles.bodyMedium.copyWith(
                            fontWeight: AppFonts.semiBold,
                            color: context.textPrimary
                          ),
                        ),
                        const SizedBox(height: AppStyles.spacingXS),
                        Text(
                          option.description,
                          style: AppStyles.caption.copyWith(
                            color: AppColors.textLight,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList(),
      ],
    );
  }
}

/// Preset avatar options for HoloLearn
class AvatarOptions {
  static const List<SelectableOption> options = [
    SelectableOption(
      id: 'standard',
      title: 'Standard Voice Avatar',
      description: 'Uses your recorded voice sample',
    ),
    SelectableOption(
      id: 'sign',
      title: 'Sign Language Avatar',
      description: 'For accessibility - Includes sign language',
    ),
  ];
}

/// Input type options for lecture content
class LectureInputOptions {
  static const List<SelectableOption> options = [
    SelectableOption(
      id: 'prepared',
      title: 'Prepared',
      description: 'Upload PDF, PPTX, or TXT files',
    ),
    SelectableOption(
      id: 'generated',
      title: 'Generated',
      description: 'Enter Resources to your lecture content',
    ),
  ];
}
