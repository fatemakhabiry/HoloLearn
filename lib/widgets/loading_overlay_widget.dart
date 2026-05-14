import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';
import '../constants/constants.dart';

String animationPath="assets/animation/Logo Animation.json";
class LoadingOverlay extends StatelessWidget {
  final bool isLoading;
  final Widget child;
  final String? message;
  final Color? barrierColor;

  const LoadingOverlay({
    super.key,
    required this.isLoading,
    required this.child,
    this.message,
    this.barrierColor,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        child,
        if (isLoading) ...[
          // Barrier — absorbs all taps
          Positioned.fill(
            child: AbsorbPointer(
              absorbing: true,
              child: Container(
                color:
                    barrierColor ?? AppColors.secondaryColor.withOpacity(0.45),
              ),
            ),
          ),
          // Spinner card
          const Center(child: _SpinnerCard()),
        ],
      ],
    );
  }
}

class _SpinnerCard extends StatelessWidget {
  const _SpinnerCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppStyles.spacingXL,
        vertical: AppStyles.spacingL,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Lottie.asset(
            animationPath,
            width: 200,
            height: 200,
            repeat: true,
          ),
          // const CircularProgressIndicator(
          //   color: AppColors.white,
          //   strokeWidth: 5,
          // ),
          const SizedBox(height: AppStyles.spacingM),
          Text(
            'Please wait…',
            style: AppStyles.bodyLarge.copyWith(color: AppColors.white),
          ),
        ],
      ),
    );
  }
}

/// Static helper — wraps showDialog so you can show/hide
/// the overlay from any async method without managing
/// a boolean in setState.
///
/// Usage:
///   LoadingOverlayHelper.show(context);
///   await someAsyncCall();
///   LoadingOverlayHelper.hide(context);
class LoadingOverlayHelper {
  static bool _isShowing = false;

  static void show(BuildContext context, {String? message}) {
    if (_isShowing) return;
    _isShowing = true;

    showDialog(
      context: context,
      barrierDismissible: false,
      barrierColor: AppColors.secondaryColor.withOpacity(0.45),
      builder: (_) => PopScope(
        canPop: false,
        child: Center(
          child: Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppStyles.spacingXL,
              vertical: AppStyles.spacingL,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Lottie.asset(
                  animationPath,
                  width: 200,
                  height: 200,
                  repeat: true,
                ),
                // const CircularProgressIndicator(
                //   color: AppColors.primaryColor,
                //   strokeWidth: 5,
                // ),
                const SizedBox(height: AppStyles.spacingM),
                Text(
                  message ?? 'Please wait…',
                  style: AppStyles.bodyLarge.copyWith(color: AppColors.white),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  static void hide(BuildContext context) {
    if (!_isShowing) return;
    _isShowing = false;
    Navigator.of(context, rootNavigator: true).pop();
  }
}
