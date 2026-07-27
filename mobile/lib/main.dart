import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/theme.dart';
import 'core/navigation/router.dart';
import 'core/api/connection_controller.dart';

void main() {
  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    // Initialize connection controller to trigger auto-reconnect on launch
    ref.watch(connectionProvider);

    return MaterialApp.router(
      title: 'Squad OS Mobile',
      theme: AppTheme.darkTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.dark, // Force Dark Mode (as specified in "Dark mode first" Section UI)
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}
