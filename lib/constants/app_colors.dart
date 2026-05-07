import 'package:flutter/material.dart';

class AppColors {
  AppColors._();

  // ── Brand ──────────────────────────────────────────────────────────────────
  static const Color primaryColor   = Color(0xFF2562EB);
  static const Color secondaryColor = Color(0xFF433EA0);

  // ── Semantic ───────────────────────────────────────────────────────────────
  static const Color error   = Color(0xFFD32F2F);
  static const Color success = Color(0xFF388E3C);

  // ── Light theme ────────────────────────────────────────────────────────────
  static const Color lightBackground = Color(0xFFE8EFFF); // page / scaffold
  static const Color white           = Color(0xFFFFFFFF); // card / surface
  static const Color gray            = Color(0xFFB1AAAF); // border, disabled
  static const Color textBlack       = Color(0xFF000000); // primary text
  static const Color textBlue        = Color(0xFF433EA0); // accent text
  static const Color textLight       = Color(0xFFB1AAAF); // secondary text

  // ── Dark theme ─────────────────────────────────────────────────────────────
  static const Color darkBackground  = Color(0xFF0F172A); // page / scaffold
  static const Color darkCard        = Color(0xFF1E293B); // card / surface
  static const Color darkBorder      = Color(0xFF334155); // border, divider
  static const Color darkTextSecondary = Color(0xFF94A3B8); // secondary text

}
