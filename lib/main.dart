import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'state/providers/app_state_provider.dart';
import 'state/providers/lecture_state_provider.dart';
import 'routes/app_routes.dart';
import 'routes/route_generator.dart';
import 'screens/splash_screen.dart';

final RouteObserver<ModalRoute<void>> routeObserver =
    RouteObserver<ModalRoute<void>>();

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
        ChangeNotifierProvider(create: (_) => LectureStateProvider()),
        // Add other providers here if needed
      ],
      child: MaterialApp(
        title: 'HoloLearn',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(primarySwatch: Colors.blue, useMaterial3: true),
        initialRoute: AppRoutes.splash, // start with splash screen route
        onGenerateRoute: RouteGenerator.generateRoute,
        navigatorObservers: [routeObserver],
      ),
    );
  }
}
