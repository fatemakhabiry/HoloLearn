import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:hololearn/services/local_file_service.dart';
import 'package:provider/provider.dart';
import 'package:syncfusion_flutter_pdfviewer/pdfviewer.dart';

import '../../models/lecture_models.dart';
import '../../services/avatar_service.dart';
import '../../state/processing_notifier.dart';
import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/lecture_service.dart';
import '../../state/providers/app_state_provider.dart';
import '../../state/providers/lecture_state_provider.dart';

class LecturePreviewScreen extends StatefulWidget {
  final bool isContent;

  const LecturePreviewScreen({super.key, this.isContent = false});

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

  // void _handleApprove() async{
  //   try {
  //     final lectureState = context.read<LectureStateProvider>();
  //     final appState = context.read<AppStateProvider>();
  //     await LectureService.approve(lectureState.sessionId, appState);

  //     Navigator.pushNamed(context, AppRoutes.lectureprocessing);
  //   } catch (e) {
  //     if (mounted) {
  //       CustomErrorHandler.show(
  //         context,
  //         message: 'Failed to start lecture processing. Please try again.',
  //         type: ErrorType.fail,
  //         duration: const Duration(seconds: 4),
  //       );
  //     }
  //   }
  // }
  void _handleApprove() async {
    try {
      final lectureState = context.read<LectureStateProvider>();
      final appState = context.read<AppStateProvider>();

      await LectureService.approve(lectureState.sessionId, appState);

      if (!mounted) return;

      // Resume polling — server will move to generating_content
      Provider.of<ProcessingNotifier>(
        context,
        listen: false,
      ).startForSession(lectureState.sessionId, appState);

      Navigator.pushNamed(
        context,
        AppRoutes.lectureprocessing,
        arguments: {
          'sessionId': lectureState.sessionId,
          'lectureType': lectureState.lectureType,
        },
      );
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message: 'Failed to approve lecture. Please try again.',
          type: ErrorType.fail,
        );
      }
    }
  }

  void _handleavtartoptions() async {
    final appState = context.read<AppStateProvider>();
    appState.setLectureId(context.read<LectureStateProvider>().lectureId);
    await AvatarService.checkAvatarStatus(appState);
    if (!mounted) return;
    Navigator.pushNamed(
      context,
      appState.isFirstTimeLogin
          ? AppRoutes.createAvatar
          : AppRoutes.lectureSetup,
    );
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
    if (widget.isContent) {
      _loadContent();
    } else {
      _loadLecture();
    }
  }

  Future<void> _loadLecture() async {
    final lectureState = context.read<LectureStateProvider>();
    final appState = context.read<AppStateProvider>();

    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      // final bytes = await LectureService.getLectureGeneratedResourceBytes(
      //   lectureState.sessionId,
      //   GenContentType.lecture,
      //   appState,
      // );
      final bytes = await LectureService.getLecturePdfBytes(
        lectureState.sessionId,
        appState,
      );

      LocalFileService.save(
        lectureState.lectureId,
        GenContentType.lecture,
        bytes,
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

  Future<void> _loadContent() async {
    final lectureState = context.read<LectureStateProvider>();
    final appState = context.read<AppStateProvider>();

    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      final bytes = await LectureService.getLectureGeneratedResourceBytes(
        lectureState.sessionId,
        GenContentType.script,
        appState,
      );
      LocalFileService.save(
        lectureState.lectureId,
        GenContentType.script,
        bytes,
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

  Widget _buildLecture() {
    final body;
    if (_hasError) {
      body = _buildError();
    } else if (_pdfBytes == null) {
      body = const Center(child: CircularProgressIndicator());
    } else {
      body = SfPdfViewer.memory(
        _pdfBytes!,
        controller: _pdfController,
        onDocumentLoadFailed: (_) => _onLoadFailed(),
      );
    }
    //  _hasError
    //       ? _buildError()
    //       : SfPdfViewer.memory(
    //           _pdfBytes!,
    //           controller: _pdfController,
    //           onDocumentLoadFailed: (_) => _onLoadFailed(),
    //         );

    return Scaffold(
      appBar: CustomAppBar(title: 'Lecture Preview', showBackButton: true),

      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadLecture,
              child: _hasError
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: [
                        SizedBox(
                          height: MediaQuery.of(context).size.height * 0.8,
                          child: body,
                        ),
                      ],
                    )
                  : body,
            ),

      bottomNavigationBar: (_isLoading || _hasError)
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

  Widget _buildContent() {
    final text = _pdfBytes != null ? String.fromCharCodes(_pdfBytes!) : '';

    return Scaffold(
      appBar: CustomAppBar(title: 'Content Preview', showBackButton: true),

      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _loadContent,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(AppStyles.spacingM),
                children: [
                  SelectableText(
                    text,
                    style: AppStyles.bodyMedium.copyWith(height: 1.5),
                  ),
                ],
              ),
            ),

      bottomNavigationBar: _isLoading
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(AppStyles.spacingL),
                child: CustomButton(
                  text: 'AVATAR OPTIONS & SCHEDULING',
                  buttonType: ButtonType.primary,
                  onPressed: _handleavtartoptions,
                  fullWidth: true,
                ),
              ),
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return widget.isContent ? _buildContent() : _buildLecture();
  }
}
