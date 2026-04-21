import 'dart:async';
import 'package:flutter/material.dart';
import '../constants/app_fonts.dart';
import '../widgets/button_widget.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../models/schedule_models.dart';

class SessionCard extends StatefulWidget {
  final ScheduleSlot session;
  final VoidCallback? onOpenTranscript;
  final VoidCallback? onEnterChat;

  const SessionCard({
    super.key,
    required this.session,
    this.onOpenTranscript,
    this.onEnterChat,
  });

  @override
  State<SessionCard> createState() => _SessionCardState();
}

class _SessionCardState extends State<SessionCard> {
  late Timer _timer;

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(minutes: 1), (_) {
      setState(() {});
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final status = widget.session.sessionStatus;

    return Container(
      padding: const EdgeInsets.all(AppStyles.spacingL),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppStyles.radiusM),
        boxShadow: AppStyles.cardShadow,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          /// Status Row
          Row(
            children: [
              CircleAvatar(
                radius: 6,
                backgroundColor: status == SessionStatus.ongoing
                    ? AppColors.success
                    : status == SessionStatus.upcoming
                    ? AppColors.gray
                    : AppColors.error,
              ),
              const SizedBox(width: AppStyles.spacingS),
              Text(
                status.name.toUpperCase(),
                style: AppStyles.bodyMedium.copyWith(
                  color: AppColors.gray,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),

          const SizedBox(height: AppStyles.spacingM),

          /// Teacher name and course code
          Text(
            '${widget.session.teacherName} - ${widget.session.courseCode}',
            style: AppStyles.h2,
          ),

          const SizedBox(height: AppStyles.spacingS),

          /// Lecture title
          Text(widget.session.lectureTitle, style: AppStyles.caption),

          const SizedBox(height: AppStyles.spacingM),

          /// Time range
          Row(
            children: [
              Icon(Icons.access_time_outlined, color: AppColors.gray),
              const SizedBox(width: AppStyles.spacingXS),
              Text(widget.session.timeRange, style: AppStyles.caption),
            ],
          ),

          const SizedBox(height: AppStyles.spacingL),

          /// Upcoming countdown
          if (status == SessionStatus.upcoming) ...[
            Text(
              'Starts in ${widget.session.remainingTime}',
              style: AppStyles.bodyLarge.copyWith(
                color: AppColors.primaryColor,
                fontWeight: AppFonts.semiBold,
              ),
            ),
          ],

          /// Ongoing session buttons
          if (status == SessionStatus.ongoing) ...[
            CustomButton(
              onPressed: widget.onOpenTranscript!,
              text: 'OPEN TRANSCRIPT',
              fullWidth: true,
            ),
            const SizedBox(height: AppStyles.spacingM),
            CustomButton(
              onPressed: widget.onEnterChat!,
              text: 'ENTER Q&A CHAT',
              fullWidth: true,
              buttonType: ButtonType.outlined,
            ),
          ],
        ],
      ),
    );
  }
}
