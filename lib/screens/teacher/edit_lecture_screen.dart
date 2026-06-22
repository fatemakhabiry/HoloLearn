import 'dart:io';
import 'dart:async';
import 'package:http/http.dart';
import 'package:provider/provider.dart';
import 'package:flutter/material.dart';

import '../../services/course_service.dart';
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
  List<String> _courseItems = [];

  // The lecture's ORIGINAL scheduled date, set once from the fetched
  // lecture data and never reassigned afterward — unlike `selectedDate`,
  // which changes every time the person picks a different date. Needed
  // to know when it's valid to synthesize the lecture's current slot
  // (only when looking at the date it's actually booked on).
  String? _originalScheduledDate;

  // Time tracking
  String? currentStartTime;
  String? currentEndTime;

  // Single source of truth for the full-screen LoadingOverlay. Covers
  // initial lecture fetch, course-code fetch, and save — every async
  // operation that should block the whole screen.
  bool isLoading = false;

  // Distinct from `isLoading`: this only controls the inline
  // spinner-vs-dropdown swap inside the Schedule section, since that's a
  // separate visual concern from the full-screen overlay (the dropdown
  // area needs to show its own spinner while slots are (re)fetched after
  // picking a date, even though `isLoading` is already true at that point
  // too via the overlay).
  bool isFetchingSlots = false;

  // True once the initial pre-selection of the lecture's existing time
  // slot has been attempted. Without this, _preselectCurrentTimeSlot ran
  // on every single fetch (every date change, every refresh) and kept
  // forcing the selection back to the original slot — fighting the
  // person's own date/slot picks and looping.
  bool _didInitialPreselect = false;

  String message = "";
  bool showBanner = false;
  bool success = false;
  String? errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchLectureData();
    _fetchCourseCodes();
  }

  void _showError(String message) {
    if (!mounted) return;
    CustomErrorHandler.show(context, message: message, type: ErrorType.fail);
  }

  /// Fetch lecture details by schedule_id
  Future<void> _fetchLectureData() async {
    setState(() {
      isLoading = true;
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
        lectureUrl = response.currentFileUrl;
        selectedDate = response.scheduledDate;
        _originalScheduledDate = response.scheduledDate;
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
      });

      // Fetch available slots for the selected date. Suppress the empty
      // toast here since this is the automatic fetch on first load — the
      // inline Schedule card message covers it without needing a toast
      // the moment the screen opens.
      if (selectedDate != null && selectedDate!.isNotEmpty) {
        await _fetchAvailableSlots(showEmptyToast: false);
      }
    } catch (e) {
      if (mounted) {
        _showError(
          'Error loading lecture: ${e.toString().replaceAll('Exception: ', '')}',
        );
      }
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  Future<void> _fetchCourseCodes() async {
    setState(() => isLoading = true);
    try {
      final appState = context.read<AppStateProvider>();
      final courses = await CourseService.fetchCourseCodes(appState);
      if (!mounted) return;
      setState(() => _courseItems = courses);
    } on SocketException {
      _showError('No internet connection.');
    } on TimeoutException {
      _showError('Request timed out.');
    } catch (e) {
      _showError(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => isLoading = false);
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

  /// Fetch available time slots for the selected date using AvailabilityService.
  ///
  /// [showEmptyToast] controls whether the "No available time slots"
  /// toast fires when the result is empty. It's suppressed on the
  /// automatic fetch triggered from `_fetchLectureData()` during initial
  /// load — showing a toast the moment the screen opens, before the
  /// person has done anything, is noisy. It's still shown for fetches
  /// the person actually triggered (picking a new date, pull-to-refresh).
  /// Either way, the Schedule card shows its own inline empty-state
  /// message regardless of this flag.
  Future<void> _fetchAvailableSlots({bool showEmptyToast = true}) async {
    if (selectedDate == null || selectedDate!.isEmpty) return;

    setState(() {
      isFetchingSlots = true;
      showBanner = false;
    });

    try {
      // FIX: this was `listen: true`, called from an async method body
      // (not from build()). Provider explicitly disallows listening from
      // outside the widget tree's build/rebuild cycle — this is what
      // caused the "Tried to listen to a value exposed with provider,
      // from outside of the widget tree" assertion failure. Only ever
      // read the token here; nothing in this method needs to rebuild
      // when accessToken changes.
      final response = await AvailabilityService.fetchAvailableSlots(
        token: Provider.of<AppStateProvider>(
          context,
          listen: false,
        ).accessToken,
        date: selectedDate!,
      );

      if (!mounted) return;

      setState(() {
        // The backend's available-slots endpoint only returns slots that
        // are free to NEWLY book — it does not include the lecture's own
        // existing booking (confirmed: for a lecture scheduled today, the
        // response was `available_slots: []`). So the current slot can
        // never be found by searching the response; it must be built
        // locally from the lecture's own start/end time instead.
        //
        // Only do this when looking at the lecture's ORIGINAL date —
        // once the person picks a different date, the old time slot has
        // no meaning there and shouldn't be offered as an option.
        AvailabilitySlot? currentSlotEntry;
        if (currentStartTime != null &&
            currentEndTime != null &&
            selectedDate != null &&
            selectedDate == _originalScheduledDate) {
          currentSlotEntry = _buildCurrentSlotEntry();
        }

        // NOTE: this backend's real status values are 'scheduled' /
        // 'drafted' (confirmed) — never 'available'. The old filter
        // `status == 'available'` could never match anything from this
        // endpoint. Since /available-slots is documented by its own name
        // as "slots free to book", every entry it returns is already
        // available — so no status filtering is needed on these at all.
        availableSlots = [...response.availableSlots];

        // Make sure the lecture's own current slot is present and
        // selectable, since the backend never includes it.
        if (currentSlotEntry != null &&
            !availableSlots.any(
              (s) => s.scheduleId == currentSlotEntry!.scheduleId,
            )) {
          availableSlots.add(currentSlotEntry);
        }

        // Pre-select the current slot — only on the VERY FIRST fetch
        // (initial load) — now that it's guaranteed to be in the list.
        if (!_didInitialPreselect && currentSlotEntry != null) {
          selectedSlot = currentSlotEntry;
          selectedTimeSlot = currentSlotEntry.formattedTimeSlot;
          _didInitialPreselect = true;
        }

        if (availableSlots.isEmpty && showEmptyToast) {
          _showError("No available time slots for this date");
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
            _showError(errorMessage!);
            availableSlots = [];
          });
        }
        errorMessage = null;
      }
      if (mounted) setState(() => isFetchingSlots = false);
    }
  }

  /// Builds an [AvailabilitySlot] representing the lecture's CURRENT
  /// booking, from `currentStartTime`/`currentEndTime`/`widget.scheduleId`
  /// directly — not from the backend's available-slots response, since
  /// that endpoint never includes a lecture's own existing booking
  /// (confirmed: it returns `available_slots: []` for a date that has
  /// nothing free but this lecture's own slot).
  ///
  /// `currentStartTime`/`currentEndTime` arrive as bare time strings like
  /// `"03:45:41.911000"` (no date) — combine them with `selectedDate`
  /// ("2026-06-22") to build full ISO datetimes the same way
  /// [AvailabilitySlot.fromJson] does internally.
  AvailabilitySlot? _buildCurrentSlotEntry() {
    if (currentStartTime == null ||
        currentEndTime == null ||
        selectedDate == null) {
      return null;
    }

    try {
      final start = DateTime.parse('${selectedDate}T$currentStartTime');
      final end = DateTime.parse('${selectedDate}T$currentEndTime');

      return AvailabilitySlot(
        scheduleId: widget.scheduleId,
        startTime: start,
        endTime: end,
        status: 'scheduled',
      );
    } catch (e) {
      print('🔴 Failed to build current slot entry: $e');
      return null;
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

    // courseCode is set via onChanged on the dropdown, not via onSaved
    // newCourseCode was never assigned — use courseCode directly
    final resolvedTitle = newLectureTitle ?? _titleController.text.trim();
    final resolvedCourseCode = newCourseCode ?? courseCode;

    if (resolvedTitle.isEmpty) {
      setState(() {
        showBanner = true;
        success = false;
        message = "Lecture title is required.";
      });
      return;
    }

    if (resolvedCourseCode == null || resolvedCourseCode.isEmpty) {
      setState(() {
        showBanner = true;
        success = false;
        message = "Please select a course code.";
      });
      return;
    }

    if (selectedSlot == null) {
      setState(() {
        showBanner = true;
        success = false;
        message = availableSlots.isEmpty
            ? "There are no available time slots for the selected date. Please choose a different date."
            : "Please select a time slot!";
      });
      return;
    }

    setState(() {
      showBanner = false;
      isLoading = true;
    });

    try {
      final appState = Provider.of<AppStateProvider>(context, listen: false);
      await LectureService.updateLecture(
        appState: appState,
        oldScheduleId: widget.scheduleId,
        newScheduleId: selectedSlot!.scheduleId,
        title: resolvedTitle,
        courseCode: resolvedCourseCode,
      );

      if (!mounted) return;
      CustomErrorHandler.show(
        context,
        message: "Edited successfully",
        type: ErrorType.success,
        duration: const Duration(seconds: 3),
      );
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) {
          Navigator.pushReplacementNamed(context, AppRoutes.teacherDashboard);
        }
      });
    } catch (e) {
      if (mounted) {
        CustomErrorHandler.show(
          context,
          message:
              'Error updating lecture: ${e.toString().replaceAll('Exception: ', '')}',
          type: ErrorType.fail,
          duration: const Duration(seconds: 3),
        );
      }
    } finally {
      if (mounted) setState(() => isLoading = false);
    }
  }

  /// Pull-to-refresh handler — re-fetches both the lecture details and
  /// the course code list, mirroring what initState does on first load.
  Future<void> _refreshData() async {
    await Future.wait([_fetchLectureData(), _fetchCourseCodes()]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: CustomAppBar(title: 'Edit Lecture'),
      body: LoadingOverlay(
        isLoading: isLoading,
        child: RefreshIndicator(
          onRefresh: _refreshData,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: Center(
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

                              CustomDropdown(
                                selectedValue: courseCode,
                                label: _courseItems.isEmpty
                                    ? 'No course available'
                                    : 'Select Course Code',
                                items: _courseItems,
                                onChanged: (value) => setState(() {
                                  courseCode = value;
                                  newCourseCode = value; // ← add this
                                }),
                                validator: (value) =>
                                    (value == null || value.isEmpty)
                                    ? 'Course code is required'
                                    : null,
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
                                    color: Theme.of(
                                      context,
                                    ).scaffoldBackgroundColor,
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
                                      const SizedBox(width: AppStyles.spacingS),
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
                              else if (selectedDate != null &&
                                  availableSlots.isEmpty)
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(
                                    AppStyles.spacingM,
                                  ),
                                  decoration: BoxDecoration(
                                    color: AppColors.gray.withOpacity(0.08),
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
                                        Icons.event_busy,
                                        color: AppColors.gray,
                                      ),
                                      const SizedBox(width: AppStyles.spacingS),
                                      Expanded(
                                        child: Text(
                                          'No available time slots for this date. Please choose a different date.',
                                          style: AppStyles.bodyMedium.copyWith(
                                            color: context.textSecondary,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                )
                              else
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    CustomDropdown(
                                      label: 'Time Slot',
                                      items: availableSlots
                                          .map((slot) => slot.formattedTimeSlot)
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
                          fullWidth: true,
                          onPressed: _handleSaveChanges,
                        ),

                        // Message Banner
                        if (showBanner) ...[
                          const SizedBox(height: AppStyles.spacingL),
                          MessageDisplay(
                            isSuccess: false,
                            message: message,
                            onDismiss: () => setState(() => showBanner = false),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
