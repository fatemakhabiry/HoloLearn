import 'package:flutter/foundation.dart';
// import '../models/user_model.dart';
// import '../services/auth_service.dart';

class AuthProvider with ChangeNotifier {
  // final AuthService _authService;
  
  // User? _currentUser;
  // bool _isLoading = false;
  // String? _errorMessage;

  // AuthProvider(this._authService);

  // // Getters
  // User? get currentUser => _currentUser;
  // bool get isLoading => _isLoading;
  // String? get errorMessage => _errorMessage;
  // bool get isLoggedIn => _currentUser != null;
  
  // void _setLoading(bool value) {
  //   _isLoading = value;
  //   notifyListeners();
  // }

  // void _setError(String? error) {
  //   _errorMessage = error;
  //   notifyListeners();
  // }

  // void clearError() {
  //   _errorMessage = null;
  //   notifyListeners();
  // }

  // /// Login - Returns both token and user in one call
  // Future<bool> login({
  //   required String email,
  //   required String password,
  // }) async {
  //   _setLoading(true);
  //   _setError(null);

  //   final response = await _authService.login(
  //     email: email,
  //     password: password,
  //   );

  //   _setLoading(false);

  //   if (response.isSuccess && response.data != null) {
  //     _currentUser = response.data;
  //     notifyListeners();
  //     return true;
  //   } else {
  //     _setError(response.error);
  //     return false;
  //   }
  // }

  // /// Load current user (on app start)
  // Future<bool> loadCurrentUser() async {
  //   if (!_authService.isLoggedIn()) {
  //     return false;
  //   }

  //   _setLoading(true);

  //   final response = await _authService.getCurrentUser();

  //   _setLoading(false);

  //   if (response.isSuccess && response.data != null) {
  //     _currentUser = response.data;
  //     notifyListeners();
  //     return true;
  //   } else {
  //     // Token might be expired
  //     await logout();
  //     return false;
  //   }
  // }

  // /// Update profile
  // Future<bool> updateProfile({
  //   String? email,
  //   String? fullName,
  // }) async {
  //   _setLoading(true);
  //   _setError(null);

  //   final response = await _authService.updateProfile(
  //     email: email,
  //     fullName: fullName,
  //   );

  //   _setLoading(false);

  //   if (response.isSuccess && response.data != null) {
  //     _currentUser = response.data;
  //     notifyListeners();
  //     return true;
  //   } else {
  //     _setError(response.error);
  //     return false;
  //   }
  // }

  // /// Upload teacher photo
  // Future<bool> uploadPhoto(File imageFile) async {
  //   _setLoading(true);
  //   _setError(null);

  //   final response = await _authService.uploadTeacherPhoto(imageFile);

  //   _setLoading(false);

  //   if (response.isSuccess) {
  //     // Reload user profile to get updated photo URL
  //     await loadCurrentUser();
  //     return true;
  //   } else {
  //     _setError(response.error);
  //     return false;
  //   }
  // }

  // /// Upload teacher voice
  // Future<bool> uploadVoice(File audioFile) async {
  //   _setLoading(true);
  //   _setError(null);

  //   final response = await _authService.uploadTeacherVoice(audioFile);

  //   _setLoading(false);

  //   if (response.isSuccess) {
  //     // Reload user profile to get updated voice URL
  //     await loadCurrentUser();
  //     return true;
  //   } else {
  //     _setError(response.error);
  //     return false;
  //   }
  // }

  // /// Logout
  // Future<void> logout() async {
  //   await _authService.logout();
  //   _currentUser = null;
  //   _errorMessage = null;
  //   notifyListeners();
  // }
}
