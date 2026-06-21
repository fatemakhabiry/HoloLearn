import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'constants/constants.dart';

import 'routes/app_routes.dart';
import 'routes/route_generator.dart';
import 'state/processing_notifier.dart';
import 'providers/theme_provider.dart';
import 'providers/app_state_provider.dart';
import 'providers/lecture_state_provider.dart';
import 'providers/resource_state_provider.dart';


final RouteObserver<ModalRoute<void>> routeObserver =
    RouteObserver<ModalRoute<void>>();

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final processingNotifier = ProcessingNotifier();
  await processingNotifier.init();

  final themeProvider = ThemeProvider();
  await themeProvider.init();

  runApp(MyApp(processingNotifier: processingNotifier, themeProvider: themeProvider));
}

class MyApp extends StatelessWidget {
  final ProcessingNotifier processingNotifier;
  final ThemeProvider themeProvider;

  const MyApp({super.key, required this.processingNotifier, required this.themeProvider});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AppStateProvider()),
        ChangeNotifierProvider(create: (_) => LectureStateProvider()),
        ChangeNotifierProvider(create: (_) => ResourceStateProvider()),
        ChangeNotifierProvider.value(value: processingNotifier),
        ChangeNotifierProvider.value(value: themeProvider),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, theme, _) => MaterialApp(
          title: 'HoloLearn',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light,
          darkTheme: AppTheme.dark,
          themeMode: theme.themeMode,
          initialRoute: AppRoutes.splash,
          onGenerateRoute: RouteGenerator.generateRoute,
          navigatorObservers: [routeObserver],
        ),
      ),
    );
  }
}

// import 'package:flutter/material.dart';
// import 'package:provider/provider.dart';
// import 'constants/constants.dart';

// import 'routes/app_routes.dart';
// import 'routes/route_generator.dart';
// import 'state/processing_notifier.dart';
// import 'providers/theme_provider.dart';
// import 'providers/app_state_provider.dart';
// import 'providers/lecture_state_provider.dart';
// import 'providers/resource_state_provider.dart';


// final RouteObserver<ModalRoute<void>> routeObserver =
//     RouteObserver<ModalRoute<void>>();

// void main() async 

//   runApp(MyApp(processingNotifier: processingNotifier, themeProvider: themeProvider));
// }

// class MyApp extends StatelessWidget {
//   final ProcessingNotifier processingNotifier;
//   final ThemeProvider themeProvider;

//   const MyApp({super.key, required this.processingNotifier, required this.themeProvider});

//   @override
//   Widget build(BuildContext context) {
//     return  MaterialApp(
//           title: 'HoloLearn',
//           debugShowCheckedModeBanner: false,
          
//     );
//   }
// }