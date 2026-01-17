import 'package:flutter/material.dart';
import '../constants/app_styles.dart';

class CustomTextFormField extends StatelessWidget {
  final String? label;
  final String hintText;
  final bool obscureText;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;
  final void Function(String?)? onSaved;
  final TextEditingController? controller;
  final Widget? suffixIcon;
  final bool isFieldRequired;
  final VoidCallback? onTap;     // ✅ added
  final bool readOnly;           // ✅ added

  const CustomTextFormField({
    super.key,
    this.label,
    required this.hintText,
    this.obscureText = false,
    this.keyboardType = TextInputType.text,
    this.validator,
    this.onSaved,
    this.controller,
    this.suffixIcon,
    this.isFieldRequired = true,
    this.onTap,                  // ✅ added
    this.readOnly = false,        // ✅ added
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
              style: AppStyles.labelStyle,
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
          onTap: onTap,              // ✅ here
          readOnly: readOnly,        // ✅ here
          keyboardType: keyboardType,
          decoration: AppStyles.inputDecoration(
            hint: hintText,
            suffixIcon: suffixIcon,
          ),
          obscureText: obscureText,
        ),
      ],
    );
  }
}