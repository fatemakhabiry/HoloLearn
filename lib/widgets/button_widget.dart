import 'package:flutter/material.dart';

import 'package:hololearn/constants/app_colors.dart';
import 'package:hololearn/constants/app_styles.dart';

enum ButtonType {
  primary, // blue button
  secondary, //white button
  outlined,
}

class CustomButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;
  final ButtonType buttonType;
  final bool fullWidth;
  final bool isLoading;
  const CustomButton({
    super.key,
    required this.text,
    required this.onPressed,
    this.buttonType = ButtonType.primary,
    this.fullWidth = false,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    Widget button;

    switch (buttonType) {
      case ButtonType.primary:
        button = ElevatedButton(
          onPressed: onPressed,
          style: AppStyles.primaryButton,
          child: Text(isLoading ? "Loading..." : text, style: AppStyles.button),
        );
        break;

      case ButtonType.secondary:
        button = ElevatedButton(
          onPressed: onPressed,
          style: AppStyles.secondaryButton,
          child: Text(
            isLoading ? "Loading..." : text,
            style: AppStyles.button.copyWith(color: AppColors.lightBlue),
          ),
        );
        break;

      case ButtonType.outlined:
        button = OutlinedButton(
          onPressed: onPressed,
          style: AppStyles.outlinedButton,
          child: Text(
            isLoading ? "Loading..." : text,
            style: AppStyles.button.copyWith(color: AppColors.lightBlue),
          ),
        );
        break;
    }

    return fullWidth ? SizedBox(width: double.infinity, child: button) : button;
  }
}

// Keep your other widgets as they are useful
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
    this.iconColor = Colors.white,
    this.backgroundColor = Colors.blue,
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

class CustomDropdown extends StatelessWidget {
  final String label;
  final List<String> items;
  final String? selectedValue;
  final Function(String?) onChanged;

  const CustomDropdown({
    super.key,
    required this.label,
    required this.items,
    required this.onChanged,
    this.selectedValue,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      value: selectedValue,
      decoration: AppStyles.inputDecoration(label: label),
      items: items.map((String item) {
        return DropdownMenuItem<String>(
          value: item,
          child: Text(item, style: AppStyles.bodyMedium),
        );
      }).toList(),
      onChanged: onChanged,
      style: AppStyles.bodyMedium,
    );
  }
}
