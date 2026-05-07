import 'dart:io';
import 'dart:async';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import 'package:flutter/material.dart';

import '../../widgets/widgets.dart';
import '../../routes/app_routes.dart';
import '../../constants/constants.dart';
import '../../services/lecture_service.dart';
import '../../models/availability_models.dart';
import '../../services/availability_service.dart';
import '../../providers/app_state_provider.dart';

class EditLectureScreen extends StatefulWidget {
  final int scheduleId;

  const EditLectureScreen({super.key, required this.scheduleId});

  @override
  State<EditLectureScreen> createState() => _EditLectureScreenState();
}

class _EditLectureScreenState extends State<EditLectureScreen> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _dateController = TextEditingController();
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _courseCodeController = TextEditingController();
  final TextEditingController _urlController = TextEditingController();

  // Lecture data from API
  int lectureId = 0;
  String selectedInputType = 'document';
  String selectedAvatar = 'standard';

  // Form fields
  String? lectureTitle;
  String? newLectureTitle;
  String? courseCode;
  String? lectureUrl;
  String? currentDocumentName;
  String? newCourseCode;

  // Scheduling
  String? selectedDate;
  String? selectedTimeSlot;
  AvailabilitySlot? selectedSlot;
  List<AvailabilitySlot> availableSlots = [];

  // Time tracking
  String? currentStartTime;
  String? currentEndTime;

  bool isLoading = false;
  bool isFetchingSlots = false;
  bool isFetchingLecture = true;
  String message = "";
  bool showBanner = false;
  bool success = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchLectureData();
  }

  /// Fetch lecture details by schedule_id
  Future<void> _fetchLectureData() async {
    setState(() {
      isFetchingLecture = true;
      showBanner = false;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      final response = await LectureService.getLectureByScheduleId(
        appState: appState,
        scheduleId: widget.scheduleId,
      );

      if (!mounted) return;

      setState(() {
        lectureId = response.lectureId;
        lectureTitle = response.title;
        courseCode = response.courseCode;
        currentDocumentName = response.currentFileName;
        lectureUrl = response.currentFileUrl;
        selectedDate = response.scheduledDate;
        currentStartTime = response.startTime;
        currentEndTime = response.endTime;

        // Populate controllers
        _titleController.text = response.title;
        _courseCodeController.text = response.courseCode;
        _urlController.text = response.currentFileUrl;

        // Format date for display
        if (response.scheduledDate.isNotEmpty) {
          final parts = response.scheduledDate.split('-');
          if (parts.length == 3) {
            _dateController.text = "${parts[2]}/${parts[1]}/${parts[0]}";
          }
        }

        isFetchingLecture = false;
      });

      // Fetch available slots for the selected date
      if (selectedDate != null && selectedDate!.isNotEmpty) {
        await _fetchAvailableSlots();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          showBanner = true;
          success = false;
          message =
              'Error loading lecture: ${e.toString().replaceAll('Exception: ', '')}';
          isFetchingLecture = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _dateController.dispose();
    _titleController.dispose();
    _courseCodeController.dispose();
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _pickDate(BuildContext context) async {
    DateTime? pickedDate = await showDatePicker(
      context: context,
      initialDate: selectedDate != null
          ? DateTime.parse(selectedDate!)
          : DateTime.now(),
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

      // Fetch available slots for the new date
      await _fetchAvailableSlots();
    }
  }

  /// Fetch available time slots for the selected date using AvailabilityService
  Future<void> _fetchAvailableSlots() async {
    if (selectedDate == null || selectedDate!.isEmpty) return;

    setState(() {
      isFetchingSlots = true;
      showBanner = false;
    });

    try {
      final response = await AvailabilityService.fetchAvailableSlots(
        token: Provider.of<AppStateProvider>(
          context,
          listen: false,
        ).accessToken,
        date: selectedDate!,
      );

      if (!mounted) return;

      setState(() {
        // Filter only available slots
        availableSlots = response.availableSlots
            .where((slot) => slot.status == 'available')
            .toList();
        isFetchingSlots = false;

        // Try to pre-select current time slot if it exists in available slots
        if (currentStartTime != null && currentEndTime != null) {
          _preselectCurrentTimeSlot();
        }

        if (availableSlots.isEmpty) {
          showBanner = true;
          success = false;
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
            showBanner = true;
            success = false;
            message = errorMessage!;
            availableSlots = [];
          });
        }
        errorMessage = null;
      }
    }
  }

  /// Try to pre-select the current time slot
  void _preselectCurrentTimeSlot() {
    if (currentStartTime == null || currentEndTime == null) return;

    // Convert current times to comparable format (remove seconds if present)
    final currentStart = currentStartTime!.substring(0, 5); // "10:00"
    final currentEnd = currentEndTime!.substring(0, 5); // "11:00"

    // Find matching slot
    for (var slot in availableSlots) {
      final slotStart =
          "${slot.startTime.hour.toString().padLeft(2, '0')}:${slot.startTime.minute.toString().padLeft(2, '0')}";
      final slotEnd =
          "${slot.endTime.hour.toString().padLeft(2, '0')}:${slot.endTime.minute.toString().padLeft(2, '0')}";

      if (slotStart == currentStart && slotEnd == currentEnd) {
        setState(() {
          selectedSlot = slot;
          selectedTimeSlot = slot.formattedTimeSlot;
        });
        break;
      }
    }
  }

  /// Handle saving changes
  Future<void> _handleSaveChanges() async {
    if (!_formKey.currentState!.validate()) {
      setState(() {
        showBanner = true;
        success = false;
        message = "Please fill all required fields correctly!";
      });
      return;
    }

    _formKey.currentState!.save();

    if (selectedSlot == null) {
      setState(() {
        showBanner = true;
        success = false;
        message = "Please select a time slot!";
      });
      return;
    }

    setState(() {
      isLoading = true;
      showBanner = false;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      // Call update API
      await LectureService.updateLecture(
        appState: appState,
        oldScheduleId: widget.scheduleId,
        newScheduleId: selectedSlot!.scheduleId,
        title: newLectureTitle!,
        courseCode: newCourseCode!,
      );

      if (!mounted) return;
      setState(() {
        // message = response.message;
        isLoading = false;
      });
      CustomErrorHandler.show(
        context,
        message: "Editted succesfully",
        type: ErrorType.success,
        duration: Duration(seconds: 3),
      );
      // Navigate back after success
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          // Navigator.pushReplacement(context, MaterialPageRoute(
          //   builder: (context) => TeacherDashboardScreen(),
          // ));
          Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          isLoading = false;
        });
        CustomErrorHandler.show(
          context,
          message:
              'Error updating lecture: ${e.toString().replaceAll('Exception: ', '')}',
          type: ErrorType.fail,
          duration: Duration(seconds: 3),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: CustomAppBar(title: 'Edit Lecture'),
      body: LoadingOverlay(
        isLoading: isFetchingLecture||isLoading,
        child: Center(
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.all(AppStyles.spacingL),
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 600),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Lecture Details Container
                          Container(
                            padding: const EdgeInsets.all(AppStyles.spacingL),
                            decoration: BoxDecoration(
                              color: Theme.of(context).cardColor,
                              borderRadius: BorderRadius.circular(
                                AppStyles.radiusXL,
                              ),
                              boxShadow: AppStyles.cardShadow,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'LECTURE DETAILS',
                                  style: AppStyles.labelStyle.copyWith(
                                    fontWeight: AppFonts.bold,
                                    fontSize: AppFonts.fontSizeXS,
                                    letterSpacing: 1.2,
                                  ),
                                ),
                                const SizedBox(height: AppStyles.spacingM),

                                // Lecture Title
                                CustomTextFormField(
                                  hintText: 'Enter Lecture Title',
                                  label: 'Lecture Title',
                                  keyboardType: TextInputType.text,
                                  controller: _titleController,
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Lecture title is required';
                                    }
                                    return null;
                                  },
                                  onSaved: (value) => newLectureTitle = value,
                                ),

                                const SizedBox(height: AppStyles.spacingL),

                                // Course Code (Read-only)
                                CustomTextFormField(
                                  hintText: 'Course Code',
                                  label: 'Course Code',
                                  keyboardType: TextInputType.text,
                                  controller: _courseCodeController,
                                  readOnly: true,
                                  validator: (value) {
                                    if (value == null || value.isEmpty) {
                                      return 'Course code is required';
                                    }
                                    return null;
                                  },
                                  onSaved: (value) => newCourseCode = value,
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Current Content Section
                          if (currentDocumentName != null &&
                              currentDocumentName!.isNotEmpty)
                            Container(
                              padding: const EdgeInsets.all(AppStyles.spacingL),
                              decoration: BoxDecoration(
                                color: Theme.of(context).cardColor,
                                borderRadius: BorderRadius.circular(
                                  AppStyles.radiusXL,
                                ),
                                boxShadow: AppStyles.cardShadow,
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'CURRENT CONTENT',
                                    style: AppStyles.labelStyle.copyWith(
                                      fontWeight: AppFonts.bold,
                                      fontSize: AppFonts.fontSizeXS,
                                      letterSpacing: 1.2,
                                    ),
                                  ),
                                  const SizedBox(height: AppStyles.spacingM),

                                  Container(
                                    padding: const EdgeInsets.all(
                                      AppStyles.spacingM,
                                    ),
                                    decoration: BoxDecoration(
                                      color:Theme.of(context).scaffoldBackgroundColor,
                                      borderRadius: BorderRadius.circular(
                                        AppStyles.radiusM,
                                      ),
                                      border: Border.all(
                                        color: AppColors.gray.withOpacity(0.3),
                                      ),
                                    ),
                                    child: Row(
                                      children: [
                                        Icon(
                                          Icons.insert_drive_file,
                                          color: AppColors.primaryColor,
                                        ),
                                        const SizedBox(
                                          width: AppStyles.spacingS,
                                        ),
                                        Expanded(
                                          child: Text(
                                            currentDocumentName!,
                                            style: AppStyles.bodyMedium,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Avatar Type Section
                          Container(
                            padding: const EdgeInsets.all(AppStyles.spacingL),
                            decoration: BoxDecoration(
                              color: Theme.of(context).cardColor,
                              borderRadius: BorderRadius.circular(
                                AppStyles.radiusXL,
                              ),
                              boxShadow: AppStyles.cardShadow,
                            ),
                            child: RadioOptionsGroup(
                              sectionTitle: 'AVATAR TYPE',
                              selectedId: selectedAvatar,
                              options: AvatarOptions.options,
                              onOptionSelected: (id) {
                                setState(() {
                                  selectedAvatar = id;
                                });
                              },
                            ),
                          ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Schedule Section
                          Container(
                            padding: const EdgeInsets.all(AppStyles.spacingL),
                            decoration: BoxDecoration(
                              color: Theme.of(context).cardColor,
                              borderRadius: BorderRadius.circular(
                                AppStyles.radiusXL,
                              ),
                              boxShadow: AppStyles.cardShadow,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'SCHEDULE',
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
                                      padding: const EdgeInsets.all(
                                        AppStyles.spacingM,
                                      ),
                                      child: CircularProgressIndicator(
                                        color: AppColors.primaryColor,
                                      ),
                                    ),
                                  )
                                else
                                  Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      CustomDropdown(
                                        label: 'Time Slot',
                                        items: availableSlots
                                            .map(
                                              (slot) => slot.formattedTimeSlot,
                                            )
                                            .toList(),
                                        selectedValue: selectedTimeSlot,
                                        hintText: selectedDate == null
                                            ? 'Please select a date first'
                                            : 'Select time slot',
                                        enabled: availableSlots.isNotEmpty,
                                        validator: (value) {
                                          if (value == null || value.isEmpty) {
                                            return 'Time slot is required';
                                          }
                                          return null;
                                        },
                                        onChanged: (value) {
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
                                      ),
                                    ],
                                  ),
                              ],
                            ),
                          ),

                          const SizedBox(height: AppStyles.spacingL),

                          // Save Changes Button
                          CustomButton(
                            text: 'SAVE CHANGES',
                            isLoading: isLoading,
                            fullWidth: true,
                            onPressed: _handleSaveChanges,
                          ),

                          // Message Banner
                          if (showBanner) ...[
                            const SizedBox(height: AppStyles.spacingL),
                            MessageDisplay(
                              isSuccess: false,
                              message: message,
                              onDismiss: () =>
                                  setState(() => showBanner = false),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
    ),);
  }
}
