import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'state/providers/app_state_provider.dart';
import 'screens/splash_screen.dart'; // ADD THIS
import 'screens/login_screen.dart';
// ... other imports

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppStateProvider()),
        // ... other providers
      ],
      child: MaterialApp(
        title: 'HoloLearn',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          primarySwatch: Colors.blue,
          useMaterial3: true,
        ),
        home: const SplashScreen(), // CHANGE THIS from LoginPage to SplashScreen
      ),
    );
  }
}