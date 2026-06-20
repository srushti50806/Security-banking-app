import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'screens/admin_dashboard.dart';
import 'screens/auth.dart';
import 'screens/user_dashboard.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await dotenv.load(fileName: '.env');
  } catch (_) {
    // Ignore dotenv errors and use API fallback in ApiService.
  }

  final apiService = ApiService();
  await apiService.initialize();

  runApp(GraphShieldApp(apiService: apiService));
}

class GraphShieldApp extends StatefulWidget {
  const GraphShieldApp({super.key, required this.apiService});

  final ApiService apiService;

  @override
  State<GraphShieldApp> createState() => _GraphShieldAppState();
}

class _GraphShieldAppState extends State<GraphShieldApp> {
  bool _isBootstrapping = true;
  AuthSession? _session;

  @override
  void initState() {
    super.initState();
    widget.apiService.onUnauthorized = _handleUnauthorized;
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    final restored = await widget.apiService.restoreSession();
    if (!mounted) {
      return;
    }
    setState(() {
      _session = restored;
      _isBootstrapping = false;
    });
  }

  void _handleUnauthorized() {
    unawaited(_logout());
  }

  void _onAuthenticated(AuthSession session) {
    if (!mounted) {
      return;
    }
    setState(() => _session = session);
  }

  Future<void> _logout() async {
    await widget.apiService.logout();
    if (!mounted) {
      return;
    }
    setState(() => _session = null);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GraphShield',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0E7EA8)),
        fontFamily: 'Trebuchet MS',
      ),
      home: _buildHome(),
    );
  }

  Widget _buildHome() {
    if (_isBootstrapping) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_session == null) {
      return AuthScreen(
        apiService: widget.apiService,
        onAuthenticated: _onAuthenticated,
      );
    }

    if (_session!.role == 'ADMIN' || _session!.role == 'BANK') {
      return AdminDashboard(
        apiService: widget.apiService,
        session: _session!,
        onLogout: _logout,
      );
    }

    return UserDashboard(
      apiService: widget.apiService,
      session: _session!,
      onLogout: _logout,
    );
  }
}
