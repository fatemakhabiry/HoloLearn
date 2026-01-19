import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/avatar_option_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/message_handler_widget.dart';
import '../services/availability_service.dart';
import '../utils/app_state.dart';

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

      // Fetch available slots for the selected date
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
      final response = await AvailabilityService.fetchAvailableSlots(
        token: AppState.accessToken,
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
    } catch (e) {
      if (!mounted) return;
      setState(() {
        isFetchingSlots = false;
        _showBanner = true;
        _success = false;
        message = e.toString().replaceAll('Exception: ', '');
        availableSlots = [];
      });
    }
  }

  List<String> get availableTimeSlotsFormatted {
    return availableSlots.map((slot) => slot.formattedTimeSlot).toList();
  }

  // Future<void> _publishLecture() async {
  //   if (_formKey.currentState!.validate()) {
  //     _formKey.currentState!.save();

  //     if (selectedSlot == null) {
  //       setState(() {
  //         _showBanner = true;
  //         _success = false;
  //         message = "Please select a time slot";
  //       });
  //       return;
  //     }

  //     setState(() {
  //       isLoading = true;
  //       _showBanner = false;
  //     });

  //     try {
  //       // Map avatar selection to API format
  //       String avatarType = selectedAvatar == 'standard'
  //           ? 'standard'
  //           : 'sign_language';

  //       await AvailabilityService.publishLecture(
  //         token: AppState.accessToken,
  //         date: selectedDate!,
  //         startTime: selectedSlot!.startTime.toIso8601String(),
  //         endTime: selectedSlot!.endTime.toIso8601String(),
  //         avatar: avatarType,
  //       );

  //       if (!mounted) return;
  //       setState(() {
  //         message = "Lecture published successfully!";
  //         _showBanner = true;
  //         _success = true;
  //         isLoading = false;
  //       });

  //       // Navigate to teacher dashboard after success
  //       Future.delayed(const Duration(seconds: 2), () {
  //         if (mounted) {
  //           Navigator.pop(context, true); // Return true to indicate success
  //         }
  //       });
  //     } catch (e) {
  //       if (!mounted) return;
  //       setState(() {
  //         _showBanner = true;
  //         _success = false;
  //         message = e.toString().replaceAll('Exception: ', '');
  //         isLoading = false;
  //       });
  //     }
  //   } else {
  //     setState(() {
  //       _showBanner = true;
  //       _success = false;
  //       message = "Please fill all required fields correctly!";
  //     });
  //   }
  // }

  @override
  Widget build(BuildContext context) {
    // Determine hologram room status
    bool isRoomAvailable =
        selectedDate != null && availableSlots.isNotEmpty && !isFetchingSlots;

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
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textLight,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: AppStyles.spacingM),

                      // Date Picker
                      CustomTextFormField(
                        label: "DATE",
                        hintText: "MM/DD/YYYY",
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
                        CustomDropdown(
                          label: "TIME SLOT",
                          items: availableTimeSlotsFormatted,
                          selectedValue: selectedTimeSlot,
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return 'Time slot is required';
                            }
                            return null;
                          },
                          onChanged: (value) {
                            setState(() {
                              selectedTimeSlot = value;
                              // Find the corresponding slot object
                              selectedSlot = availableSlots.firstWhere(
                                (slot) => slot.formattedTimeSlot == value,
                              );
                            });
                          },
                        ),
                      const SizedBox(height: AppStyles.spacingL),

                      // // Hologram Room Status
                      // Container(
                      //   padding: const EdgeInsets.symmetric(
                      //     horizontal: AppStyles.spacingM,
                      //     vertical: AppStyles.spacingS,
                      //   ),
                      //   decoration: BoxDecoration(
                      //     color: isRoomAvailable
                      //         ? AppColors.success.withOpacity(0.1)
                      //         : AppColors.textLight.withOpacity(0.1),
                      //     borderRadius: BorderRadius.circular(
                      //       AppStyles.radiusM,
                      //     ),
                      //     border: Border.all(
                      //       color: isRoomAvailable
                      //           ? AppColors.success
                      //           : AppColors.textLight,
                      //       width: 1.5,
                      //     ),
                      //   ),
                      //   child: Row(
                      //     mainAxisAlignment: MainAxisAlignment.center,
                      //     children: [
                      //       Text(
                      //         'HOLOGRAM ROOM STATUS: ',
                      //         style: TextStyle(
                      //           fontSize: 12,
                      //           fontWeight: FontWeight.w600,
                      //           color: AppColors.textBlack,
                      //           letterSpacing: 0.5,
                      //         ),
                      //       ),
                      //       Text(
                      //         isRoomAvailable ? 'AVAILABLE' : 'UNAVAILABLE',
                      //         style: TextStyle(
                      //           fontSize: 12,
                      //           fontWeight: FontWeight.bold,
                      //           color: isRoomAvailable
                      //               ? AppColors.success.withOpacity(0.1)
                      //               : AppColors.textLight.withOpacity(0.1),
                      //           letterSpacing: 0.5,
                      //         ),
                      //       ),
                      //     ],
                      //   ),
                      // ),
                      const SizedBox(height: AppStyles.spacingL),

                      // Confirm Button
                      CustomButton(
                        text: 'CONFIRM & PUBLISH LECTURE',
                        fullWidth: true,
                        isLoading: isLoading,
                        // onPressed: _publishLecture,
                        onPressed: () {},
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
