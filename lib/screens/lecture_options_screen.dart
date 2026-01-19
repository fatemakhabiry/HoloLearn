import 'package:flutter/material.dart';
import '../constants/app_colors.dart';
import '../constants/app_styles.dart';
import '../widgets/app_bar_widget.dart';
import '../widgets/avatar_option_widget.dart';
import '../widgets/button_widget.dart';
import '../widgets/text_form_widget.dart';
import '../widgets/message_handler_widget.dart';

class LectureSetupScreen extends StatefulWidget {
  const LectureSetupScreen({super.key});

  @override
  State<LectureSetupScreen> createState() => _LectureSetupScreenState();
}

class _LectureSetupScreenState extends State<LectureSetupScreen> {
  String selectedAvatar = 'standard';
  bool is_loading = false;
  final TextEditingController _dateController = TextEditingController();
  final _formKey = GlobalKey<FormState>(); // ✅ Form key added

  String? selectedDate;
  String message = "";
  bool _showbanner = false;
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
      firstDate: DateTime(2026),
      lastDate: DateTime(2030),
    );

    if (pickedDate != null) {
      final formattedDate =
          "${pickedDate.day}/${pickedDate.month}/${pickedDate.year}";

      if (!mounted) return;
      setState(() {
        _dateController.text = formattedDate;
        selectedDate = formattedDate;
      });
    }
  }

  // 1. All possible time slots
  final List<String> allTimeSlots = [
    "9:00 to 10:00",
    "10:00 to 11:00",
    "11:00 to 12:00",
    "12:00 to 1:00",
    "1:00 to 2:00",
    "2:00 to 3:00",
  ];
  final List<String> reservedSlots = ["10:00 to 11:00", "12:00 to 1:00"];
  String? selectedTimeSlot;
  List<String> get availableTimeSlots {
    if (allTimeSlots.isEmpty) return [];
    return allTimeSlots.where((slot) => !reservedSlots.contains(slot)).toList();
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
            key: _formKey, // ✅ Wrapping everything in Form
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Container for Avatar + Time Slot
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
                          print('Selected avatar: $id');
                        },
                      ),
                      const SizedBox(height: AppStyles.spacingL),
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
                      CustomDropdown(
                        label: "Time Slot",
                        items: availableTimeSlots,
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
                          });
                          print('Selected time slot: $value');
                        },
                      ),
                      const SizedBox(height: AppStyles.spacingL),
                      // Proceed Button
                      CustomButton(
                        text: 'CONFIRM & PUBLISH LECTURE',
                        fullWidth: true,
                        isLoading: is_loading,
                        onPressed: () async {
                          if (_formKey.currentState!.validate()) {
                            _formKey.currentState!.save();

                            // Start loading
                            setState(() {
                              is_loading = true;
                            });

                            try {
                              // Simulate API call for publishing lecture
                              await Future.delayed(const Duration(seconds: 2));

                              // Success - show success message
                              setState(() {
                                message = "Lecture published successfully!";
                                _showbanner = true;
                                _success = true;
                              });

                              // Navigate to teacher dashboard after success
                              Future.delayed(const Duration(seconds: 1), () {
                                if (mounted) {
                                  // TODO: Navigate to teacher dashboard
                                  print("Selected Date: $selectedDate");
                                  print(
                                    "Selected Time Slot: $selectedTimeSlot",
                                  );
                                  print("Selected Avatar: $selectedAvatar");
                                  // Navigator.pushReplacement(
                                  //   context,
                                  //   MaterialPageRoute(
                                  //     builder: (context) => const TeacherDashboardScreen(),
                                  //   ),
                                  // );
                                }
                              });
                            } catch (e) {
                              // Error - show error message
                              setState(() {
                                _showbanner = true;
                                _success = false;
                                message =
                                    "Failed to publish lecture. Please try again.";
                              });
                            } finally {
                              // Stop loading
                              if (mounted) {
                                setState(() {
                                  is_loading = false;
                                });
                              }
                            }
                          } else {
                            // Form is not valid
                            setState(() {
                              _showbanner = true;
                              _success = false;
                              message =
                                  "Please fill all required fields correctly!";
                            });
                          }
                        },
                      ),
                      const SizedBox(height: AppStyles.spacingL),
                    ],
                  ),
                ),
                if (_showbanner) ...[
                  const SizedBox(height: AppStyles.spacingL),
                  MessageDisplay(
                    isSuccess: _success,
                    massegeBanner: _success
                        ? "Lecture Published Successfully"
                        : "Publication Failed",
                    message: message,
                    onDismiss: () => setState(() => _showbanner = false),
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
