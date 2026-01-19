import 'package:flutter/material.dart';
import '../screens/create_avatar_screen.dart';
import '../screens/login_screen.dart';
import '../screens/teacher_profile_screen.dart';
import 'package:http/http.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: LoginPage(),
    );
  }
}
