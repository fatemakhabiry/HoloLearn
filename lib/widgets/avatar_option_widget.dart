import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_fonts.dart';
import '../constants/app_styles.dart';

/// Generic model for any selectable option
class SelectableOption {
  final String id; // Unique identifier (e.g., 'standard', 'sign')
  final String title; // Display name (e.g., 'Standard Voice Avatar')
  final String description; // Explanation text (e.g., 'Uses your recorded...')

  const SelectableOption({
    required this.id,
    required this.title,
    required this.description,
  });
}

// Can be used for avatars, settings, preferences, or any radio selection
class RadioOptionsGroup extends StatelessWidget {
  final String? sectionTitle; // Optional header (e.g., 'AVATAR OPTIONS')
  final String selectedId; // Currently selected option ID
  final List<SelectableOption> options; // List of choices to display
  final Function(String) onOptionSelected; // Callback when user selects

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
                color: AppColors.white,
                border: Border.all(
                  color: selectedId == option.id
                      ? AppColors.lightBlue
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
                            ? AppColors.lightBlue
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
                                color: AppColors.lightBlue,
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
//usage example:
/*RadioOptionsGroup(
  sectionTitle: 'AVATAR OPTIONS',
  selectedId: selectedAvatar,
  options: AvatarOptions.options,  // ← Simple!
  onOptionSelected: (id) => setState(() => selectedAvatar = id),
)*/