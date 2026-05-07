import 'package:flutter/material.dart';
import 'package:hololearn/constants/app_themes.dart';

import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import './message_handler_widget.dart';

import 'package:file_picker/file_picker.dart';

// ─── Controller ───────────────────────────────────────────────────────────────

class FileUploadController {
  _FileUploadWidgetState? _state;

  void _attach(_FileUploadWidgetState state) => _state = state;
  void _detach() => _state = null;

  void reset() => _state?._reset();
}

// ─── Widget ───────────────────────────────────────────────────────────────────

class FileUploadWidget extends StatefulWidget {
  final String label;
  final bool isRequired;
  final List<String> supportedFormats;
  final String? headerText;
  final String? subheaderText;
  final Function(List<PlatformFile>)? onFilesSelected;
  final FileUploadController? controller;
  final bool allowMultiple;

  const FileUploadWidget({
    super.key,
    required this.label,
    required this.supportedFormats,
    this.headerText,
    this.subheaderText,
    this.isRequired = true,
    this.onFilesSelected,
    this.controller,
    this.allowMultiple= true,
  });

  @override
  State<FileUploadWidget> createState() => _FileUploadWidgetState();
}

class _FileUploadWidgetState extends State<FileUploadWidget> {
  List<PlatformFile> _selectedFiles = [];

  @override
  void initState() {
    super.initState();
    widget.controller?._attach(this);
  }

  @override
  void didUpdateWidget(FileUploadWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller?._detach();
      widget.controller?._attach(this);
    }
  }

  @override
  void dispose() {
    widget.controller?._detach();
    super.dispose();
  }

  // Called by the controller
  void _reset() {
    setState(() => _selectedFiles = []);
    widget.onFilesSelected?.call([]);
  }

Future<void> _pickFiles() async {
  final result = await FilePicker.platform.pickFiles(
    type: FileType.custom,
    allowedExtensions: widget.supportedFormats,
    allowMultiple: widget.allowMultiple,
  );

  if (result == null) return; 

  setState(() {
    if (widget.allowMultiple) {
      _selectedFiles.addAll(result.files); 
    } else {
      _selectedFiles = [result.files.first]; 
    }
  });

  widget.onFilesSelected?.call(_selectedFiles);
}

  void _removeFile(PlatformFile file) {
    setState(() => _selectedFiles.remove(file));
    widget.onFilesSelected?.call(_selectedFiles);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(AppStyles.spacingL),
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.circular(AppStyles.radiusXL),
            boxShadow: AppStyles.cardShadow,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              RichText(
                text: TextSpan(
                  text: widget.label,
                  style: AppStyles.labelStyle.copyWith(color: context.textPrimary),
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
                      Icon(Icons.add, size: 48, color: AppColors.gray.withValues()),
                      const SizedBox(height: AppStyles.spacingM),
                      if (widget.headerText != null) ...[
                        Text(widget.headerText!, textAlign: TextAlign.center, style: AppStyles.h3.copyWith(color: context.textPrimary)),
                        const SizedBox(height: AppStyles.spacingS),
                      ],
                      if (widget.subheaderText != null) ...[
                        Text(widget.subheaderText!, textAlign: TextAlign.center, style: AppStyles.caption.copyWith(color: context.textSecondary)),
                        const SizedBox(height: AppStyles.spacingS),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        if (_selectedFiles.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: AppStyles.spacingM),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: _selectedFiles.map((file) {
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
