import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_themes.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';

enum ButtonType {
  primary,  // light: primary bg + white text  | dark: primary bg + dark text
  secondary, // light: white bg + primary text  | dark: darkCard bg + primary text
  outlined, // light: transparent + primary border | dark: transparent + primary border + dark bg
}

class CustomButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;
  final ButtonType buttonType;
  final bool fullWidth;
  final bool isLoading;
  final Widget? prefixIcon;
  final Widget? suffixIcon;

  const CustomButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.buttonType = ButtonType.primary,
    this.fullWidth = false,
    this.isLoading = false,
    this.prefixIcon,
    this.suffixIcon,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // ── Per-type colors ───────────────────────────────────────────────────
    final Color bgColor;
    final Color textColor;

    switch (buttonType) {
      case ButtonType.primary:
        bgColor   = AppColors.primaryColor;
        textColor = isDark ? AppColors.darkBackground : AppColors.white;
        break;
      case ButtonType.secondary:
        bgColor   = isDark ? AppColors.darkCard : AppColors.white;
        textColor = AppColors.primaryColor;
        break;
      case ButtonType.outlined:
        bgColor   = isDark ? AppColors.darkCard : Colors.transparent;
        textColor = AppColors.primaryColor;
        break;
    }

    // ── Button child ──────────────────────────────────────────────────────
    final buttonChild = Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (prefixIcon != null) ...[
          prefixIcon!,
          const SizedBox(width: AppStyles.spacingS),
        ],
        Text(
          isLoading ? 'Loading...' : text,
          style: AppStyles.button.copyWith(color: textColor),
        ),
        if (suffixIcon != null) ...[
          const SizedBox(width: AppStyles.spacingS),
          suffixIcon!,
        ],
      ],
    );

    // ── Build button ──────────────────────────────────────────────────────
    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(AppStyles.radiusM),
    );

    Widget button;

    switch (buttonType) {
      case ButtonType.primary:
      case ButtonType.secondary:
        button = ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: bgColor,
            foregroundColor: textColor,
            padding: const EdgeInsets.symmetric(
              horizontal: AppStyles.spacingL,
              vertical: AppStyles.spacingM,
            ),
            shape: shape,
            elevation: 0,
            shadowColor: Colors.transparent,
          ),
          child: buttonChild,
        );
        break;

      case ButtonType.outlined:
        button = OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            backgroundColor: bgColor,
            foregroundColor: textColor,
            side: const BorderSide(color: AppColors.primaryColor, width: 2),
            padding: const EdgeInsets.symmetric(
              horizontal: AppStyles.spacingL,
              vertical: AppStyles.spacingM,
            ),
            shape: shape,
          ),
          child: buttonChild,
        );
        break;
    }

    return fullWidth ? SizedBox(width: double.infinity, child: button) : button;
  }
}

// ── IconsButton ───────────────────────────────────────────────────────────────

class IconsButton extends StatelessWidget {
  final VoidCallback onPressed;
  final IconData icon;
  final Color iconColor;
  final Color backgroundColor;
  final double size;

  const IconsButton({
    super.key,
    required this.onPressed,
    required this.icon,
    this.iconColor = AppColors.white,
    this.backgroundColor = AppColors.primaryColor,
    this.size = 48.0,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: backgroundColor,
          shape: BoxShape.circle,
        ),
        child: Icon(icon, color: iconColor, size: size * 0.5),
      ),
    );
  }
}

// ── CustomDropdown ────────────────────────────────────────────────────────────

class CustomDropdown extends StatelessWidget {
  final String label;
  final bool isFieldRequired;
  final List<String> items;
  final String? selectedValue;
  final String? hintText;
  final String? Function(String?)? validator;
  final Function(String?) onChanged;
  final bool enabled;

  const CustomDropdown({
    super.key,
    required this.label,
    required this.items,
    required this.onChanged,
    this.validator,
    this.isFieldRequired = true,
    this.selectedValue,
    this.hintText,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final fillColor  = isDark ? AppColors.darkCard   : AppColors.white;
    final textColor  = isDark ? AppColors.textLight : AppColors.textBlack;
    final borderColor = isDark ? AppColors.darkBorder : AppColors.gray.withOpacity(0.3);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: TextSpan(
            text: label,
            style: AppStyles.labelStyle.copyWith(color: textColor),
            children: isFieldRequired
                ? [const TextSpan(text: ' *', style: TextStyle(color: Colors.red))]
                : null,
          ),
        ),
        const SizedBox(height: AppStyles.spacingM),
        DropdownButtonFormField<String>(
          value: selectedValue,
          validator: validator,
          dropdownColor: fillColor,
          style: AppStyles.bodyMedium.copyWith(color: textColor),
          decoration: InputDecoration(
            filled: true,
            fillColor: fillColor,
            hintText: hintText,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppStyles.radiusM),
              borderSide: BorderSide(color: borderColor, width: 1),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppStyles.radiusM),
              borderSide: BorderSide(color: borderColor, width: 1),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(AppStyles.radiusM),
              borderSide: const BorderSide(color: AppColors.primaryColor, width: 2),
            ),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: AppStyles.spacingM,
              vertical: AppStyles.spacingM,
            ),
          ),
          items: items.map((String item) {
            return DropdownMenuItem<String>(
              value: item,
              child: Text(item, style: AppStyles.bodyMedium.copyWith(color: context.textPrimary)),
            );
          }).toList(),
          onChanged: enabled ? onChanged : null,
        ),
      ],
    );
  }
}