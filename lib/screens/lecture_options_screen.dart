import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../constants/app_fonts.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/avatar_option_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../services/availability_service.dart';
import '../state/providers/app_state_provider.dart';
import 'teacher_dashboard_screen.dart';

class LectureSetupScreen extends StatefulWidget {
  const LectureSetupScreen({super.key});

  @override
  State<LectureSetupScreen> createState() => _LectureSetupScreenState();
}

class _LectureSetupScreenState extends State<LectureSetupScreen> {
  String selectedAvatar = 'standard';
  bool isLoading = false;
  bool isFetchingSlots = false;
  final TextEditingController _dateController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  String? selectedDate; // YYYY-MM-DD format
  String? selectedTimeSlot;
  AvailabilitySlot? selectedSlot;
  List<AvailabilitySlot> availableSlots = [];

  String message = "";
  bool _showBanner = false;
  bool _success = false;
  String? errorMessage;

  @override
  void dispose() {
    _dateController.dispose();
    super.dispose();
  }

  Future<void> _pickDate(BuildContext context) async {
    DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2025),
      lastDate: DateTime(2030),
    );

    if (pickedDate != null) {
      final formattedDateDisplay =
          "${pickedDate.day}/${pickedDate.month}/${pickedDate.year}";
      final formattedDateAPI =
          "${pickedDate.year}-${pickedDate.month.toString().padLeft(2, '0')}-${pickedDate.day.toString().padLeft(2, '0')}";

      if (!mounted) return;
      setState(() {
        _dateController.text = formattedDateDisplay;
        selectedDate = formattedDateAPI;
        selectedTimeSlot = null;
        selectedSlot = null;
        availableSlots = [];
      });

      await _fetchAvailableSlots();
    }
  }

  Future<void> _fetchAvailableSlots() async {
    if (selectedDate == null) return;

    setState(() {
      isFetchingSlots = true;
      _showBanner = false;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final response = await AvailabilityService.fetchAvailableSlots(
        token: appState.accessToken,
        date: selectedDate!,
      );

      if (!mounted) return;
      setState(() {
        availableSlots = response.availableSlots
            .where((slot) => slot.status == 'available')
            .toList();
        isFetchingSlots = false;

        if (availableSlots.isEmpty) {
          _showBanner = true;
          _success = false;
          message = "No available time slots for this date";
        }
      });
    } on ClientException {
      errorMessage = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      errorMessage = 'No internet connection.';
    } on TimeoutException {
      errorMessage = 'Request timed out.';
    } catch (e) {
      errorMessage = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (errorMessage != null) {
        if (mounted) {
          setState(() {
            isFetchingSlots = false;
            _showBanner = true;
            _success = false;
            message = errorMessage!;
            availableSlots = [];
          });
        }
        errorMessage = null;
      }
    }
  }

  List<String> get availableTimeSlotsFormatted {
    return availableSlots.map((slot) => slot.formattedTimeSlot).toList();
  }

  Future<void> _publishLecture() async {
    if (!_formKey.currentState!.validate()) {
      setState(() {
        _showBanner = true;
        _success = false;
        message = "Please fill all required fields correctly!";
      });
      return;
    }

    _formKey.currentState!.save();

    if (selectedSlot == null) {
      setState(() {
        _showBanner = true;
        _success = false;
        message = "Please select a time slot";
      });
      return;
    }

    setState(() {
      isLoading = true;
      _showBanner = false;
    });

    try {
      // ✅ Call the confirm and publish API
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final response = await AvailabilityService.confirmAndPublishLecture(
        token: appState.accessToken,
        lectureId: appState.lectureId,
        scheduleId: selectedSlot!.scheduleId,
      );

      if (!mounted) return;
      setState(() {
        message = response.message;
        _showBanner = true;
        _success = true;
        isLoading = false;
      });

      // Navigate back after success
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (context) => const TeacherDashboardScreen(),
            ),
          );
        }
      });
    } on ClientException {
      errorMessage = 'Cannot connect to server. Check internet or URL.';
    } on SocketException {
      errorMessage = 'No internet connection.';
    } on TimeoutException {
      errorMessage = 'Request timed out.';
    } catch (e) {
      errorMessage = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (errorMessage != null) {
        if (mounted) {
          setState(() {
            _showBanner = true;
            _success = false;
            message = errorMessage!;
            isLoading = false;
          });
        }
        errorMessage = null;
      }
      if (mounted) {
        setState(() {
          isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.lightBackground,
      appBar: CustomAppBar(title: "Lecture Setup", showBackButton: true),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(AppStyles.spacingL),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.all(AppStyles.spacingL),
                  decoration: BoxDecoration(
                    color: AppColors.white,
                    borderRadius: BorderRadius.circular(AppStyles.radiusXL),
                    boxShadow: AppStyles.cardShadow,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Avatar Options
                      RadioOptionsGroup(
                        sectionTitle: 'AVATAR OPTIONS',
                        selectedId: selectedAvatar,
                        options: AvatarOptions.options,
                        onOptionSelected: (id) {
                          setState(() {
                            selectedAvatar = id;
                          });
                        },
                      ),
                      const SizedBox(height: AppStyles.spacingL),

                      // Scheduling Section Header
                      Text(
                        'SCHEDULING',
                        style: AppStyles.labelStyle.copyWith(
                          fontWeight: AppFonts.bold,
                          fontSize: AppFonts.fontSizeXS,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: AppStyles.spacingM),

                      // Date Picker
                      CustomTextFormField(
                        label: "Date",
                        hintText: "DD/MM/YYYY",
                        controller: _dateController,
                        readOnly: true,
                        onTap: () => _pickDate(context),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Date is required';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: AppStyles.spacingL),

                      // Time Slot Dropdown
                      if (isFetchingSlots)
                        Center(
                          child: Padding(
                            padding: const EdgeInsets.all(AppStyles.spacingM),
                            child: CircularProgressIndicator(
                              color: AppColors.lightBlue,
                            ),
                          ),
                        )
                      else
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            RichText(
                              text: const TextSpan(
                                text: 'Time Slot',
                                style: AppStyles.labelStyle,
                                children: [
                                  TextSpan(
                                    text: ' *',
                                    style: TextStyle(color: Colors.red),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: AppStyles.spacingM),
                            DropdownButtonFormField<String>(
                              value: selectedTimeSlot,
                              hint: Text(
                                selectedDate == null
                                    ? 'Please select a date first'
                                    : 'Select time slot',
                                style: AppStyles.bodyMedium.copyWith(
                                  color: AppColors.textLight,
                                ),
                              ),
                              decoration: InputDecoration(
                                filled: true,
                                fillColor: AppColors.white,
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(
                                    AppStyles.radiusM,
                                  ),
                                  borderSide: BorderSide(
                                    color: AppColors.gray.withOpacity(0.3),
                                    width: 1,
                                  ),
                                ),
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(
                                    AppStyles.radiusM,
                                  ),
                                  borderSide: BorderSide(
                                    color: AppColors.gray.withOpacity(0.3),
                                    width: 1,
                                  ),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(
                                    AppStyles.radiusM,
                                  ),
                                  borderSide: const BorderSide(
                                    color: AppColors.lightBlue,
                                    width: 2,
                                  ),
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: AppStyles.spacingM,
                                  vertical: AppStyles.spacingM,
                                ),
                              ),
                              items: availableTimeSlotsFormatted.map((
                                String slot,
                              ) {
                                return DropdownMenuItem<String>(
                                  value: slot,
                                  child: Text(
                                    slot,
                                    style: AppStyles.bodyMedium,
                                  ),
                                );
                              }).toList(),
                              onChanged: availableTimeSlotsFormatted.isEmpty
                                  ? null
                                  : (value) {
                                      setState(() {
                                        selectedTimeSlot = value;
                                        selectedSlot = availableSlots
                                            .firstWhere(
                                              (slot) =>
                                                  slot.formattedTimeSlot ==
                                                  value,
                                            );
                                      });
                                    },
                              validator: (value) {
                                if (value == null || value.isEmpty) {
                                  return 'Time slot is required';
                                }
                                return null;
                              },
                              style: AppStyles.bodyMedium,
                            ),
                          ],
                        ),
                      const SizedBox(height: AppStyles.spacingL),

                      // Confirm Button
                      CustomButton(
                        text: 'CONFIRM & PUBLISH LECTURE',
                        fullWidth: true,
                        isLoading: isLoading,
                        onPressed: _publishLecture,
                      ),
                      const SizedBox(height: AppStyles.spacingL),
                    ],
                  ),
                ),

                // Message Banner
                if (_showBanner) ...[
                  const SizedBox(height: AppStyles.spacingL),
                  MessageDisplay(
                    isSuccess: _success,
                    massegeBanner: _success
                        ? "Lecture Published Successfully"
                        : "Publication Failed",
                    message: message,
                    onDismiss: () => setState(() => _showBanner = false),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
