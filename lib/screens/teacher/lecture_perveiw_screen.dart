import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:syncfusion_flutter_pdfviewer/pdfviewer.dart';

import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/lecture_service.dart';
import '../../state/providers/app_state_provider.dart';
import '../../state/providers/lecture_state_provider.dart';

class LecturePreviewScreen extends StatefulWidget {
  // final String lectureTitle;
  final bool? iscontent;
  // final String? pdfUrl;
  // final Uint8List pdfBytes;
  const LecturePreviewScreen({
    super.key,
    // required this.pdfBytes,
    this.iscontent,
    // this.pdfUrl,
  });

  @override
  State<LecturePreviewScreen> createState() => _LecturePreviewScreenState();
}

class _LecturePreviewScreenState extends State<LecturePreviewScreen> {
  final PdfViewerController _pdfController = PdfViewerController();
  bool _hasError = false;
  Uint8List? _pdfBytes;
  bool _isLoading = true;

  void _handleDecline() {
    Navigator.pushNamed(context, AppRoutes.refinecontent);
  }

  void _handleApprove() {
    try {
      final lectureState = context.read<LectureStateProvider>();
      final appState = context.read<AppStateProvider>();
      final response = LectureService.approve(lectureState.sessionId, appState);

      Navigator.pushNamed(context, AppRoutes.lectureprocessing);
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Failed to start lecture processing. Please try again.',
          type: ErrorType.fail,
          duration: const Duration(seconds: 4),
        );
      }
    }
  }

  void _onLoadFailed() {
    setState(() => _hasError = true);
    if (mounted) {
      CustomErrorHandler.show(
        context,
        message: 'Failed to load lecture content. Please try again.',
        type: ErrorType.fail,
        duration: const Duration(seconds: 4),
      );
    }
  }

  // Widget _buildViewer() {
  //   if (widget.assetPath != null) {
  //     return SfPdfViewer.asset(
  //       widget.assetPath!,
  //       controller: _pdfController,
  //       onDocumentLoadFailed: (_) => _onLoadFailed(),
  //     );
  //   }
  //   if (widget.pdfUrl != null) {
  //     return SfPdfViewer.network(
  //       widget.pdfUrl!,
  //       controller: _pdfController,
  //       onDocumentLoadFailed: (_) => _onLoadFailed(),
  //     );
  //   }
  //   return _buildError();
  // }
  // Widget _buildViewer() {
  //   if (_isLoading) {
  //     return const Center(child: CircularProgressIndicator());
  //   }

  //   if (_pdfBytes != null) {
  //     return Column(
  //       children: [
  //         SfPdfViewer.memory(
  //           _pdfBytes!,
  //           controller: _pdfController,
  //           onDocumentLoadFailed: (_) => _onLoadFailed(),
  //         ),
  //       ],
        
  //     );
  //   }

  //   return _buildError();
  // }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: AppColors.error),
          const SizedBox(height: AppStyles.spacingM),
          Text(
            'Failed to load content',
            style: AppStyles.h3,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: AppStyles.spacingS),
          Text(
            'Please check your connection and try again',
            style: AppStyles.bodyMedium.copyWith(color: AppColors.gray),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _loadPdf();
  }

  // Future<void> _loadPdf() async {
  //   final lectureState = context.read<LectureStateProvider>();
  //   final appState = context.read<AppStateProvider>();
  //   try {
  //     final bytes = await LectureService.getLecturePdfBytes(
  //       lectureState.sessionId,
  //       appState,
  //     );

  //     setState(() {
  //       _pdfBytes = Uint8List.fromList(bytes);
  //       _isLoading = false;
  //     });
  //   } catch (e) {
  //     _onLoadFailed();
  //     setState(() => _isLoading = false);
  //   }
  // }
  Future<void> _loadPdf() async {
    final lectureState = context.read<LectureStateProvider>();
    final appState = context.read<AppStateProvider>();

    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      final bytes = await LectureService.getLecturePdfBytes(
        lectureState.sessionId,
        appState,
      );

      if (!mounted) return;

      setState(() {
        _pdfBytes = Uint8List.fromList(bytes);
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;

      setState(() {
        _isLoading = false;
        _hasError = true;
      });

      _onLoadFailed();
    }
  }

  @override
  @override
Widget build(BuildContext context) {
  return Scaffold(
    appBar: const CustomAppBar(
      title: 'Lecture Preview',
      showBackButton: true,
    ),

    // ── BODY ─────────────────────────────────────────────
    body: _isLoading
        ? const Center(child: CircularProgressIndicator())
        : RefreshIndicator(
            onRefresh: _loadPdf,
            child: _hasError
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      SizedBox(
                        height: MediaQuery.of(context).size.height * 0.8,
                        child: _buildError(),
                      ),
                    ],
                  )
                : SfPdfViewer.memory(
                    _pdfBytes!,
                    controller: _pdfController,
                    onDocumentLoadFailed: (_) => _onLoadFailed(),
                  ),
          ),

    // ── FIXED BUTTONS ────────────────────────────────────
    bottomNavigationBar: _hasError || _isLoading
        ? null
        : SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(AppStyles.spacingL),
              child: Row(
                children: [
                  Expanded(
                    child: CustomButton(
                      text: 'Decline',
                      buttonType: ButtonType.secondary,
                      onPressed: _handleDecline,
                      fullWidth: true,
                      prefixIcon: Icon(
                        Icons.close,
                        color: AppColors.primaryColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppStyles.spacingM),
                  Expanded(
                    child: CustomButton(
                      text: 'Approve',
                      buttonType: ButtonType.primary,
                      onPressed: _handleApprove,
                      fullWidth: true,
                      prefixIcon: const Icon(
                        Icons.check,
                        color: AppColors.white,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
  );
  }
}
