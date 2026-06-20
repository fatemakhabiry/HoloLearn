import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import '../constants/constants.dart';

class DefaultAvatars {
  static const List<DefaultAvatarOption> all = [
    DefaultAvatarOption(
      name: 'Arthur',
      imagePath: 'assets/avatars/arthur.jpeg',
      audioPath: 'avatars/arthur_voice_sample.mpeg',
    ),
    DefaultAvatarOption(
      name: 'Adeline',
      imagePath: 'assets/avatars/adeline.jpeg',
      audioPath: 'avatars/adeline_voice_sample.mpeg',
    ),
  ];
}

class DefaultAvatarOption {
  final String name;
  final String imagePath;
  final String audioPath;

  const DefaultAvatarOption({
    required this.name,
    required this.imagePath,
    required this.audioPath,
  });
}

class DefaultAvatarCard extends StatefulWidget {
  final DefaultAvatarOption avatar;
  final bool isSelected;
  final VoidCallback onSelected;

  const DefaultAvatarCard({
    super.key,
    required this.avatar,
    required this.isSelected,
    required this.onSelected,
  });

  @override
  State<DefaultAvatarCard> createState() => _DefaultAvatarCardState();
}

class _DefaultAvatarCardState extends State<DefaultAvatarCard> {
  final AudioPlayer _player = AudioPlayer();
  bool _isPlaying = false;

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _toggleVoiceSample() async {
    if (_isPlaying) {
      await _player.stop();
      setState(() => _isPlaying = false);
      return;
    }

    setState(() => _isPlaying = true);
    await _player.play(AssetSource(widget.avatar.audioPath));
    _player.onPlayerComplete.listen((_) {
      if (mounted) setState(() => _isPlaying = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    final selected = widget.isSelected;

    return GestureDetector(
      onTap: widget.onSelected,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(AppStyles.spacingM),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(AppStyles.radiusXL),
          border: Border.all(
            color: selected ? AppColors.primaryColor : Colors.transparent,
            width: 2,
          ),
          boxShadow: context.cardShadow,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              alignment: Alignment.topRight,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppStyles.radiusL),
                  child: Image.asset(
                    widget.avatar.imagePath,
                    width: 100,
                    height: 100,
                    fit: BoxFit.cover,
                  ),
                ),
                if (selected)
                  Container(
                    margin: const EdgeInsets.all(AppStyles.spacingXS),
                    decoration: const BoxDecoration(
                      color: AppColors.primaryColor,
                      shape: BoxShape.circle,
                    ),
                    padding: const EdgeInsets.all(2),
                    child:  Icon(
                      Icons.check,
                      color: context.cardColor,
                      size: 14,
                    ),
                  ),
              ],
            ),
            const SizedBox(height: AppStyles.spacingS),
            Text(
              widget.avatar.name,
              style: AppStyles.bodyMedium.copyWith(
                fontWeight: AppFonts.semiBold,
                color: context.textPrimary,
              ),
            ),
            const SizedBox(height: AppStyles.spacingS),
            GestureDetector(
              onTap: _toggleVoiceSample,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppStyles.spacingS,
                  vertical: AppStyles.spacingXS,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primaryColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(AppStyles.radiusPill),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      _isPlaying ? Icons.stop : Icons.play_arrow,
                      size: 16,
                      color: AppColors.primaryColor,
                    ),
                    const SizedBox(width: AppStyles.spacingXS),
                    Text(
                      _isPlaying ? 'Stop' : 'Listen',
                      style: AppStyles.caption.copyWith(
                        color: AppColors.primaryColor,
                        fontWeight: AppFonts.semiBold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}