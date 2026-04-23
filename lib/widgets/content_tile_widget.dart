
import 'package:flutter/material.dart';
import '../constants/constants.dart';
import '../models/lecture_models.dart';
class ContentTileWidget extends StatelessWidget {
  final GenContentType type;
  final bool isCached;
  final bool isDownloading;
  final VoidCallback onTap;
 
 const ContentTileWidget({
  super.key, // ← add this
  required this.type,
  required this.isCached,
  required this.isDownloading,
  required this.onTap,
});
 
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppStyles.spacingM),
      child: InkWell(
        onTap: isDownloading ? null : onTap,
        borderRadius: BorderRadius.circular(AppStyles.radiusXL),
        child: Container(
          padding: const EdgeInsets.all(AppStyles.spacingL),
          decoration: BoxDecoration(
            color: AppColors.white,
            borderRadius: BorderRadius.circular(AppStyles.radiusXL),
            boxShadow: AppStyles.cardShadow,
          ),
          child: Row(
            children: [
              // Icon
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: AppColors.primaryColor.withOpacity(0.1),
                  borderRadius:
                      BorderRadius.circular(AppStyles.radiusM),
                ),
                child: Icon(type.icon,
                    color: AppColors.primaryColor, size: 24),
              ),
              const SizedBox(width: AppStyles.spacingM),
 
              // Label
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(type.displayName,
                        style: AppStyles.bodyMedium
                            .copyWith(fontWeight: AppFonts.semiBold)),
                    const SizedBox(height: 2),
                    Text(
                      isCached ? 'Saved locally — tap to open' : 'Tap to download',
                      style: AppStyles.caption,
                    ),
                  ],
                ),
              ),
 
              // Trailing action
              if (isDownloading)
                const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.primaryColor,
                  ),
                )
              else if (isCached)
                const Icon(Icons.folder_open,
                    color: AppColors.primaryColor, size: 24)
              else
                const Icon(Icons.download_outlined,
                    color: AppColors.gray, size: 24),
            ],
          ),
        ),
      ),
    );
  }
}