import 'package:flutter/material.dart';
import '../screens/teacher_profile_screen.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import 'button_widget.dart';

class CustomAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final bool showBackButton;
  final bool showProfile;
  final VoidCallback? onBackPressed;
  final List<Widget>? actions;

  const CustomAppBar({
    super.key,
    required this.title,
    this.showBackButton = true,
    this.showProfile = false,
    this.onBackPressed,
    this.actions,
  });

  @override
  Widget build(BuildContext context) {
    Widget? leadingWidget;

    if (showBackButton) {
      leadingWidget = IconsButton(
        onPressed: onBackPressed ?? () => Navigator.pop(context),
        icon: Icons.arrow_back_ios,
        backgroundColor: AppColors.lightBlue,
      );
    }

    List<Widget> appBarActions = [];
    if (showProfile) {
      appBarActions.add(
        Padding(
          padding: const EdgeInsets.only(right: AppStyles.spacingM),
          child: GestureDetector(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => const TeacherProfileScreen(),
              ),
            ),
            child: const Icon(
              Icons.account_circle,
              color: AppColors.white,
              size: 40,
            ),
          ),
        ),
      );
    }
    if (actions != null) {
      appBarActions.addAll(actions!);
    }

    return AppBar(
      backgroundColor: AppColors.lightBlue,
      elevation: 0,
      automaticallyImplyLeading: false,
      leading: leadingWidget,
      title: Text(title, style: AppStyles.h2.copyWith(color: AppColors.white)),
      actions: appBarActions.isNotEmpty ? appBarActions : null,
    );
  }

  @override
  Size get preferredSize => const Size.fromHeight(56.0);
}
