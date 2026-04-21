import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'routes/app_routes.dart';
import 'routes/route_generator.dart';
import 'state/processing_notifier.dart';
import 'state/providers/app_state_provider.dart';
import 'state/providers/lecture_state_provider.dart';
import 'state/providers/resource_state_provider.dart';


final RouteObserver<ModalRoute<void>> routeObserver =
    RouteObserver<ModalRoute<void>>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final processingNotifier = ProcessingNotifier();
  await processingNotifier.init();

  runApp(MyApp(processingNotifier: processingNotifier));
}

class MyApp extends StatelessWidget {
  final ProcessingNotifier processingNotifier;

  const MyApp({super.key, required this.processingNotifier});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppStateProvider()),
        ChangeNotifierProvider(create: (_) => LectureStateProvider()),
        ChangeNotifierProvider(create: (_) => ResourceStateProvider()),
        ChangeNotifierProvider.value(value: processingNotifier),
      ],
      child: MaterialApp(
        title: 'HoloLearn',
        debugShowCheckedModeBanner: false,
        initialRoute: AppRoutes.splash,
        onGenerateRoute: RouteGenerator.generateRoute,
        navigatorObservers: [routeObserver],
      ),
    );
  }
}