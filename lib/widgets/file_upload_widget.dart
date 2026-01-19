import 'package:flutter/material.dart';

import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import './message_handler_widget.dart';

import 'package:file_picker/file_picker.dart';

class FileUploadWidget extends StatefulWidget {
  final String label;
  final bool isRequired;
  final List<String> supportedFormats;
  final String? headerText;
  final String? subheaderText;
  final Function(List<PlatformFile>)? onFilesSelected;

  const FileUploadWidget({
    super.key,
    required this.label,
    required this.supportedFormats,
    this.headerText,
    this.subheaderText,
    this.isRequired = true,
    this.onFilesSelected,
  });

  @override
  State<FileUploadWidget> createState() => _FileUploadWidgetState();
}

class _FileUploadWidgetState extends State<FileUploadWidget> {
  List<PlatformFile>? _selectedFiles;

  Future<void> _pickFiles() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: widget.supportedFormats,
      allowMultiple: true,
    );

    if (result != null) {
      setState(() {
        _selectedFiles = result.files;
      });

      if (widget.onFilesSelected != null) {
        widget.onFilesSelected!(result.files);
      }
    }
  }

  void _removeFile(PlatformFile file) {
    setState(() {
      _selectedFiles?.remove(file);
    });
    //y3ni aihh?
    if (widget.onFilesSelected != null && _selectedFiles != null) {
      widget.onFilesSelected!(_selectedFiles!);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(AppStyles.spacingL),
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(AppStyles.radiusXL),
            boxShadow: AppStyles.cardShadow,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              RichText(
                text: TextSpan(
                  text: widget.label,
                  style: AppStyles.labelStyle,
                  children: [
                    if (widget.isRequired)
                      const TextSpan(
                        text: ' *',
                        style: TextStyle(color: Colors.red),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: AppStyles.spacingS),

              // Upload Widget
              InkWell(
                onTap: _pickFiles,
                borderRadius: BorderRadius.circular(AppStyles.radiusM),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(
                    vertical: AppStyles.spacingXXL,
                    horizontal: AppStyles.spacingL,
                  ),

                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // Plus Icon
                      Icon(
                        Icons.add,
                        size: 48,
                        color: AppColors.gray.withValues(),
                      ),
                      const SizedBox(height: AppStyles.spacingM),

                      // Main Text
                      if (widget.headerText != null) ...[
                        Text(
                          widget.headerText!,
                          textAlign: TextAlign.center,
                          style: AppStyles.h3,
                        ),

                        const SizedBox(height: AppStyles.spacingS),
                      ],
                      if (widget.subheaderText != null) ...[
                        Text(
                          widget.subheaderText!,
                          textAlign: TextAlign.center,
                          style: AppStyles.caption,
                        ),

                        const SizedBox(height: AppStyles.spacingS),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        // Display selected files
        if (_selectedFiles != null && _selectedFiles!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: AppStyles.spacingM),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: _selectedFiles!.map((file) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: AppStyles.spacingXS),
                  child: MessageDisplay(
                    message: file.name,
                    isInfo: true,
                    showIcon: false,
                    onDismiss: () => _removeFile(file),
                  ),
                );
              }).toList(),
            ),
          ),
      ],
    );
  }
}
