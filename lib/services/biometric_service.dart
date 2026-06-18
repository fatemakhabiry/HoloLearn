import 'package:local_auth/local_auth.dart';
import 'package:local_auth/error_codes.dart' as auth_error;
import 'package:flutter/services.dart';

class BiometricService {
  BiometricService._();

  static final _auth = LocalAuthentication();

  /// Check if the device supports biometrics at all
  static Future<bool> isAvailable() async {
    try {
      return await _auth.canCheckBiometrics || await _auth.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  /// Returns which biometrics are enrolled (fingerprint, face, iris)
  static Future<List<BiometricType>> availableTypes() async {
    try {
      return await _auth.getAvailableBiometrics();
    } catch (_) {
      return [];
    }
  }

  /// Trigger the biometric prompt.
  /// Returns true if authenticated, false if cancelled or failed.
  /// Throws [BiometricException] on error.
  static Future<bool> authenticate({
    String reason = 'Please authenticate to continue',
  }) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: false, // false = allow PIN/pattern fallback
          stickyAuth: true,     // keeps prompt alive if app goes background
          useErrorDialogs: true,
        ),
      );
    } on PlatformException catch (e) {
      if (e.code == auth_error.notAvailable ||
          e.code == auth_error.notEnrolled) {
        throw BiometricException('Biometrics not set up on this device.');
      }
      if (e.code == auth_error.lockedOut ||
          e.code == auth_error.permanentlyLockedOut) {
        throw BiometricException(
            'Too many attempts. Try again later or use your PIN.');
      }
      throw BiometricException(e.message ?? 'Authentication error.');
    }
  }
}

class BiometricException implements Exception {
  final String message;
  const BiometricException(this.message);

  @override
  String toString() => message;
}