import 'dart:async';
import 'dart:math';
import 'package:flutter/material.dart';
import '../constants/constants.dart';


/// Animated pill button that cycles through phrases with a typewriter effect.
/// Tap navigates to the Research Agent screen.
///
/// Usage:
///   ResearchAgentButton(onTap: () => Navigator.pushNamed(context, AppRoutes.researchAgent))
class ResearchAgentButton extends StatefulWidget {
  final VoidCallback onTap;
  final List<String> phrases;

  const ResearchAgentButton({
    super.key,
    required this.onTap,
    this.phrases = const [
      "Can't find resources...?",
      "Need help finding materials?",
      "Missing something for your lesson?",
      "Looking for resources...?",
      "Need sources or references?",
      "Can't find what you need?",
      "Need better resources?",
      "Find resources for me",
      "Help me gather resources",
      "Search learning materials",
      "Find supporting content",
      "Need inspiration...?",
      "Build my resource list...",
    ],
  });

  @override
  State<ResearchAgentButton> createState() => _ResearchAgentButtonState();
}

class _ResearchAgentButtonState extends State<ResearchAgentButton>
    with SingleTickerProviderStateMixin {
  // ── Typewriter state ──────────────────────────────────────────────────────
  int _phraseIndex = 0;
  int _charIndex = 0;
  bool _deleting = false;
  bool _paused = false;
  String _displayed = '';
  Timer? _timer;

  // ── Cursor blink ──────────────────────────────────────────────────────────
  late final AnimationController _cursorCtrl;
  late final Animation<double> _cursorAnim;

  // ── Hover ─────────────────────────────────────────────────────────────────
  bool _hovered = false;

  final _rng = Random();

  @override
  void initState() {
    super.initState();

    _cursorCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);

    _cursorAnim = Tween<double>(begin: 1, end: 0).animate(
      CurvedAnimation(parent: _cursorCtrl, curve: Curves.easeInOut),
    );

    _scheduleTick(_firstDelay);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _cursorCtrl.dispose();
    super.dispose();
  }

  // ── Timing constants (ms) ─────────────────────────────────────────────────
  int get _firstDelay => 400;
  int get _typeDelay => 68 + _rng.nextInt(40);   // 68–108 ms per char
  int get _deleteDelay => 36 + _rng.nextInt(20); // 36–56 ms per char
  int get _pauseAfterTyped => 1600;
  int get _pauseAfterDeleted => 280;

  void _scheduleTick(int ms) {
    _timer?.cancel();
    _timer = Timer(Duration(milliseconds: ms), _tick);
  }

  void _tick() {
    if (!mounted) return;
    final word = widget.phrases[_phraseIndex];

    if (_paused) {
      _paused = false;
      _deleting = true;
      _scheduleTick(_pauseAfterTyped);
      return;
    }

    if (!_deleting) {
      if (_charIndex < word.length) {
        _charIndex++;
        setState(() => _displayed = word.substring(0, _charIndex));
        _scheduleTick(_typeDelay);
      } else {
        _paused = true;
        _scheduleTick(16); // tiny tick to trigger pause branch
      }
    } else {
      if (_charIndex > 0) {
        _charIndex--;
        setState(() => _displayed = word.substring(0, _charIndex));
        _scheduleTick(_deleteDelay);
      } else {
        _deleting = false;
        _phraseIndex = (_phraseIndex + 1) % widget.phrases.length;
        _scheduleTick(_pauseAfterDeleted);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final bgColor = Theme.of(context).scaffoldBackgroundColor;
    final borderColor = AppColors.primaryColor;

    final glowColor = AppColors.primaryColor.withOpacity(_hovered ? 0.14 : 0);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(
            horizontal: AppStyles.spacingM,
            vertical: AppStyles.spacingS,
          ),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(AppStyles.radiusPill),
            border: Border.all(color: borderColor, width: 1.5),
            boxShadow: [
              BoxShadow(
                color: glowColor,
                blurRadius: AppStyles.radiusL,
                spreadRadius: AppStyles.radiusS,
              ),
              if (!isDark)
                BoxShadow(
                  color: AppColors.primaryColor.withOpacity(0.06),
                  blurRadius: AppStyles.radiusS,
                  offset: const Offset(0, 2),
                ),
            ],
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              // ── AI search icon ────────────────────────────────────────────
             Icon(
                  Icons.saved_search_sharp,
                  color: AppColors.primaryColor,
                  size: 24,
                ),
              
              const SizedBox(width: AppStyles.spacingM),

              // ── Typewriter text ───────────────────────────────────────────
              Flexible(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Flexible(
                      child: Text(
                        _displayed,
                        style: TextStyle(
                          fontFamily: AppFonts.primary,
                          fontSize: AppFonts.fontSizeS,
                          fontWeight: AppFonts.regular,
                          color: context.textPrimary
                        ),
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                      ),
                    ),
                    // Blinking cursor
                    AnimatedBuilder(
                      animation: _cursorAnim,
                      builder: (_, __) => Opacity(
                        opacity: _cursorAnim.value,
                        child: Container(
                          width: 2,
                          height: 14,
                          margin: const EdgeInsets.only(left: 1),
                          decoration: BoxDecoration(
                            color: AppColors.primaryColor,
                            borderRadius: BorderRadius.circular(1),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // ── Arrow ─────────────────────────────────────────────────────
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: EdgeInsets.only(
                    left: AppStyles.spacingM),
                child: Icon(
                  Icons.arrow_forward_rounded,
                  size: 16,
                  color:  AppColors.primaryColor
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}