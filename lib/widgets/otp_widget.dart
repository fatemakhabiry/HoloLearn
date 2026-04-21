// import 'package:flutter/material.dart';
// import 'package:hololearn/constants/app_colors.dart';

// class OtpInputWidget extends StatefulWidget {
//   final Function(String) onCompleted;

//   const OtpInputWidget({Key? key, required this.onCompleted}) : super(key: key);

//   @override
//   State<OtpInputWidget> createState() => _OtpInputWidgetState();
// }

// class _OtpInputWidgetState extends State<OtpInputWidget> {
//   final List<TextEditingController> _controllers = List.generate(
//     6,
//     (index) => TextEditingController(),
//   );

//   final List<FocusNode> _focusNodes = List.generate(6, (index) => FocusNode());

//   @override
//   void dispose() {
//     for (var c in _controllers) {
//       c.dispose();
//     }
//     for (var f in _focusNodes) {
//       f.dispose();
//     }
//     super.dispose();
//   }

//   void _onDigitChanged(String value, int index) {
//     if (value.isNotEmpty) {
//       // Go to next field
//       if (index < 5) {
//         _focusNodes[index + 1].requestFocus();
//       }
//     } else {
//       // Backspace → previous field
//       if (index > 0) {
//         _focusNodes[index - 1].requestFocus();
//       }
//     }

//     // Check if all 6 digits are filled
//     String otp = _controllers.map((c) => c.text).join();

//     if (otp.length == 6) {
//       widget.onCompleted(otp);
//     }
//   }

//   @override
//   Widget build(BuildContext context) {
//     return Row(
//       mainAxisAlignment: MainAxisAlignment.spaceEvenly,
//       children: List.generate(6, (index) {
//         return SizedBox(
//           width: 50,
//           child: TextField(
//             controller: _controllers[index],
//             focusNode: _focusNodes[index],
//             keyboardType: TextInputType.number,
//             textAlign: TextAlign.center,
//             maxLength: 1,
//             style: const TextStyle(
//               fontSize: 24,
//               fontWeight: FontWeight.bold,
//               color: AppColors.textBlack,
//             ),
//             decoration: InputDecoration(
//               counterText: "",
//               filled: true,
//               fillColor: AppColors.white,

//               enabledBorder: OutlineInputBorder(
//                 borderRadius: BorderRadius.circular(12),
//                 borderSide: const BorderSide(color: AppColors.gray, width: 1.5),
//               ),

//               focusedBorder: OutlineInputBorder(
//                 borderRadius: BorderRadius.circular(12),
//                 borderSide: const BorderSide(
//                   color: AppColors.primaryColor,
//                   width: 2,
//                 ),
//               ),
//             ),
//             onChanged: (value) => _onDigitChanged(value, index),
//           ),
//         );
//       }),
//     );
//   }
// }
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../constants/app_colors.dart';

class OtpInputWidget extends StatefulWidget {
  final Function(String) onCompleted;

  const OtpInputWidget({Key? key, required this.onCompleted}) : super(key: key);

  @override
  State<OtpInputWidget> createState() => _OtpInputWidgetState();
}

class _OtpInputWidgetState extends State<OtpInputWidget> {
  final List<TextEditingController> _controllers = List.generate(
    6,
    (index) => TextEditingController(),
  );

  final List<FocusNode> _focusNodes = List.generate(6, (index) => FocusNode());

  @override
  void dispose() {
    for (var c in _controllers) {
      c.dispose();
    }
    for (var f in _focusNodes) {
      f.dispose();
    }
    super.dispose();
  }

  void _onDigitChanged(String value, int index) {
    if (value.isNotEmpty) {
      // Go to next field
      if (index < 5) {
        _focusNodes[index + 1].requestFocus();
      }
    } else {
      // Backspace → previous field
      if (index > 0) {
        _focusNodes[index - 1].requestFocus();
      }
    }

    // Check if all 6 digits are filled
    String otp = _controllers.map((c) => c.text).join();

    if (otp.length == 6) {
      widget.onCompleted(otp);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(6, (index) {
        return Flexible(
          child: Container(
            constraints: BoxConstraints(maxWidth: 50),
            margin: EdgeInsets.symmetric(horizontal: 3),
            child: AspectRatio(
              aspectRatio: 0.9,
              child: TextField(
                controller: _controllers[index],
                focusNode: _focusNodes[index],
                keyboardType: TextInputType.number,
                textAlign: TextAlign.center,
                maxLength: 1,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppColors.textBlack,
                ),
                decoration: InputDecoration(
                  counterText: "",
                  filled: true,
                  fillColor: AppColors.white,
                  contentPadding: EdgeInsets.zero,
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(
                      color: AppColors.gray,
                      width: 1.5,
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: const BorderSide(
                      color: AppColors.primaryColor,
                      width: 2,
                    ),
                  ),
                ),
                onChanged: (value) => _onDigitChanged(value, index),
              ),
            ),
          ),
        );
      }),
    );
  }
}
