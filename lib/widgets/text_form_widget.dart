import 'package:flutter/material.dart';
import '../constants/app_styles.dart';
import '../constants/app_themes.dart';

class CustomTextFormField extends StatelessWidget {
  final String? label;
  final String hintText;
  final bool obscureText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final void Function(String?)? onSaved;
  final TextEditingController? controller;
  final Widget? prefixIcon;     // ✅ Add this
  final Widget? suffixIcon;
  final bool isFieldRequired;
  final VoidCallback? onTap;
  final bool readOnly;
  final int maxLines;

  const CustomTextFormField({
    super.key,
    this.label,
    required this.hintText,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.validator,
    this.onSaved,
    this.controller,
    this.prefixIcon,          // ✅ Add this
    this.suffixIcon,
    this.isFieldRequired = true,
    this.onTap,
    this.readOnly = false,
    this.maxLines = 1,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null)
          RichText(
            text: TextSpan(
              text: label,
              style: AppStyles.labelStyle.copyWith(color: context.textPrimary),
              children: isFieldRequired
                  ? const [
                      TextSpan(
                        text: ' *',
                        style: TextStyle(color: Colors.red),
                      ),
                    ]
                  : null,
            ),
          ),
        SizedBox(height: AppStyles.spacingM),
        TextFormField(
          validator: validator,
          onSaved: onSaved,
          controller: controller,
          onTap: onTap,
          maxLines: maxLines,
          readOnly: readOnly,
          keyboardType: keyboardType,
          decoration: AppStyles.inputDecoration(
            context: context,
            hint: hintText,
            prefixIcon: prefixIcon,
            suffixIcon: suffixIcon,
          ),
          obscureText: obscureText,
        ),
      ],
    );
  }
}