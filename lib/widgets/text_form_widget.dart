import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_styles.dart';

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
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        RichText(
          text: TextSpan(
            text: label,
            style: AppStyles.labelStyle,
            children: isFieldRequired
                ? [
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
