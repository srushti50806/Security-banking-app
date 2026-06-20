import 'dart:async';

import 'package:flutter/material.dart';

import '../services/api_service.dart';

class UserDashboard extends StatefulWidget {
  const UserDashboard({
    super.key,
    required this.apiService,
    required this.session,
    required this.onLogout,
  });

  final ApiService apiService;
  final AuthSession session;
  final Future<void> Function() onLogout;

  @override
  State<UserDashboard> createState() => _UserDashboardState();
}

class _UserDashboardState extends State<UserDashboard> {
  Timer? _refreshTimer;

  List<Map<String, dynamic>> _events = [];
  List<Map<String, dynamic>> _devices = [];
  List<Map<String, dynamic>> _ipHistory = [];

  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _fetchDashboardData();
    _refreshTimer = Timer.periodic(const Duration(seconds: 6), (_) {
      _fetchDashboardData(silent: true);
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchDashboardData({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final data = await widget.apiService.fetchUserDashboard();
      final rawEvents = data['events'] as List<dynamic>? ?? [];
      final rawDevices = data['devices'] as List<dynamic>? ?? [];
      final rawIps = data['ip_history'] as List<dynamic>? ?? [];

      if (!mounted) {
        return;
      }

      setState(() {
        _events = rawEvents.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _devices = rawDevices.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _ipHistory = rawIps.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      });
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _error = e.message);
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() => _error = 'Failed to load activity');
    } finally {
      if (mounted && !silent) {
        setState(() => _loading = false);
      }
    }
  }

  String _decision() {
    if (_events.isNotEmpty) {
      return (_events.first['decision'] ?? 'ALLOW').toString().toUpperCase();
    }
    final fromRisk = widget.session.risk?['decision'];
    if (fromRisk != null) {
      return fromRisk.toString().toUpperCase();
    }
    return 'ALLOW';
  }

  double _riskScore() {
    if (_events.isNotEmpty) {
      return (_events.first['risk_score'] as num?)?.toDouble() ??
          (_events.first['final_score'] as num?)?.toDouble() ??
          0.0;
    }
    return (widget.session.risk?['risk_score'] as num?)?.toDouble() ??
        (widget.session.risk?['final_score'] as num?)?.toDouble() ??
        0.0;
  }

  int _blockedAttempts() {
    return _events
        .where(
          (event) =>
              (event['decision'] ?? '').toString().toUpperCase() == 'BLOCK',
        )
        .length;
  }

  int _allowedAttempts() {
    return _events
        .where(
          (event) =>
              (event['decision'] ?? '').toString().toUpperCase() == 'ALLOW',
        )
        .length;
  }

  Color _decisionColor(String decision) {
    switch (decision) {
      case 'BLOCK':
        return const Color(0xFFD92D20);
      default:
        return const Color(0xFF067647);
    }
  }

  IconData _decisionIcon(String decision) {
    switch (decision) {
      case 'BLOCK':
        return Icons.block;
      default:
        return Icons.verified_user_outlined;
    }
  }

  String _formatTimestamp(dynamic rawTimestamp) {
    if (rawTimestamp is num) {
      final dt = DateTime.fromMillisecondsSinceEpoch(
        (rawTimestamp.toDouble() * 1000).toInt(),
        isUtc: true,
      ).toLocal();
      return '${dt.year}-${_pad(dt.month)}-${_pad(dt.day)} ${_pad(dt.hour)}:${_pad(dt.minute)}';
    }
    if (rawTimestamp is String && rawTimestamp.trim().isNotEmpty) {
      final parsed = DateTime.tryParse(rawTimestamp.trim());
      if (parsed != null) {
        final dt = parsed.toLocal();
        return '${dt.year}-${_pad(dt.month)}-${_pad(dt.day)} ${_pad(dt.hour)}:${_pad(dt.minute)}';
      }
    }
    return 'Unknown time';
  }

  String _pad(int value) => value.toString().padLeft(2, '0');

  List<String> _buildAlerts() {
    final alerts = <String>[];
    final latest = _events.isNotEmpty ? _events.first : null;
    final features = latest?['features'] as Map<String, dynamic>?;

    if ((features?['is_new_device'] as num?)?.toInt() == 1) {
      alerts.add('New device detected in your latest login attempt.');
    }
    if (((features?['failed_attempts'] as num?)?.toInt() ?? 0) > 3) {
      alerts.add('Multiple blocked attempts observed recently.');
    }
    if ((latest?['decision'] ?? '').toString().toUpperCase() == 'BLOCK') {
      alerts.add('A suspicious attempt was blocked by policy.');
    }

    if (alerts.isEmpty) {
      alerts.add('No active high-risk alerts for your account.');
    }
    return alerts;
  }

  Widget _sectionCard({required String title, required Widget child}) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF344054)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 17,
              fontWeight: FontWeight.w700,
              color: Color(0xFFE4E7EC),
            ),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  Widget _buildStatusPanel() {
    final latest = _events.isNotEmpty ? _events.first : null;
    final status = (latest?['decision'] ?? 'ALLOW').toString().toUpperCase();
    final color = status == 'BLOCK'
        ? const Color(0xFFF04438)
        : const Color(0xFF32D583);

    return _sectionCard(
      title: 'Latest Suspicious Login Attempt',
      child: Row(
        children: [
          Container(
            height: 64,
            width: 64,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              status == 'BLOCK' ? Icons.block : Icons.verified_user_outlined,
              color: color,
              size: 30,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  status == 'BLOCK' ? 'Suspicious activity' : 'Normal login',
                  style: TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                    color: color,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  status == 'BLOCK'
                      ? 'An outsider login attempt against your account was flagged.'
                      : 'No suspicious outsider login attempts were detected.',
                  style: const TextStyle(
                    color: Color(0xFF98A2B3),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertsPanel() {
    final latest = _events.isNotEmpty ? _events.first : null;
    final status = (latest?['decision'] ?? 'ALLOW').toString().toUpperCase();
    final message = status == 'BLOCK'
        ? 'Your recent login was reviewed by the system.'
        : 'No suspicious login activity detected.';

    return _sectionCard(
      title: 'Activity Notes',
      child: Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFF1D2939),
          border: Border.all(color: const Color(0xFF344054)),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.notification_important_outlined,
              size: 18,
              color: Color(0xFF84CAFF),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(color: Color(0xFFEAECF0)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRecentActivityPanel() {
    return _sectionCard(
      title: 'Suspicious Outsider Login History',
      child: _events.isEmpty
          ? const Text(
              'No suspicious outsider login activity found for this account yet.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : Column(
              children: _events.take(10).map((event) {
                final decision = (event['decision'] ?? 'ALLOW')
                    .toString()
                    .toUpperCase();
                final color = decision == 'BLOCK'
                    ? const Color(0xFFF04438)
                    : const Color(0xFF32D583);
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0B1220),
                    border: Border.all(color: color.withValues(alpha: 0.6)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: ListTile(
                    dense: true,
                    onTap: () => _showSecurityInsights(event),
                    leading: Icon(
                      decision == 'BLOCK' ? Icons.block : Icons.check_circle,
                      color: color,
                    ),
                    title: Text(
                      decision == 'BLOCK'
                          ? 'Suspicious login'
                          : 'Successful login',
                      style: TextStyle(color: color, fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Device: ${event['device_id'] ?? 'unknown'} | IP: ${event['ip_address'] ?? 'unknown'} | ${_formatTimestamp(event['timestamp'])}',
                      style: const TextStyle(color: Color(0xFF98A2B3)),
                    ),
                  ),
                );
              }).toList(),
            ),
    );
  }

  Widget _buildDeviceInsightsPanel() {
    return _sectionCard(
      title: 'Devices Used',
      child: _devices.isEmpty
          ? const Text(
              'No device intelligence available yet.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : Column(
              children: _devices.map((row) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0B1220),
                    border: Border.all(color: const Color(0xFF344054)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.devices_other_outlined, color: Color(0xFF84CAFF)),
                    title: Text(
                      (row['device_id'] ?? 'unknown').toString(),
                      style: const TextStyle(color: Color(0xFFF2F4F7), fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Attempts: ${row['attempts'] ?? 0}',
                      style: const TextStyle(color: Color(0xFF98A2B3)),
                    ),
                  ),
                );
              }).toList(),
            ),
    );
  }

  Widget _buildIpHistoryPanel() {
    return _sectionCard(
      title: 'IP History',
      child: _ipHistory.isEmpty
          ? const Text(
              'No IP history available yet.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : Column(
              children: _ipHistory.map((row) {
                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0B1220),
                    border: Border.all(color: const Color(0xFF344054)),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: ListTile(
                    leading: const Icon(Icons.language_outlined, color: Color(0xFFFDB022)),
                    title: Text(
                      (row['ip_address'] ?? 'unknown').toString(),
                      style: const TextStyle(color: Color(0xFFF2F4F7), fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Attempts: ${row['attempts'] ?? 0}',
                      style: const TextStyle(color: Color(0xFF98A2B3)),
                    ),
                  ),
                );
              }).toList(),
            ),
    );
  }

  void _showSecurityInsights([Map<String, dynamic>? selectedEvent]) {
    final event = selectedEvent ?? (_events.isNotEmpty ? _events.first : null);
    if (event == null) {
      return;
    }

    final ml = (event['ml_score'] as num?)?.toDouble();
    final graph = (event['graph_score'] as num?)?.toDouble();
    final rulePenalty = (event['rule_penalty'] as num?)?.toDouble();
    final finalScore = (event['final_score'] as num?)?.toDouble();
    final s3Path = event['s3_path']?.toString();
    final attackType = (event['attack_type'] ?? 'NONE').toString();

    // Parse SHAP attributions if available
    final shapMap = event['shap_attributions'] as Map<String, dynamic>?;
    final List<Widget> shapWidgets = [];
    if (shapMap != null && shapMap.isNotEmpty) {
      shapWidgets.add(const SizedBox(height: 12));
      shapWidgets.add(
        const Text(
          'SHAP Feature Attributions:',
          style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFE4E7EC)),
        ),
      );
      
      final sortedEntries = shapMap.entries.toList()
        ..sort((a, b) {
          final aPct = (a.value['percentage'] as num?)?.toDouble() ?? 0.0;
          final bPct = (b.value['percentage'] as num?)?.toDouble() ?? 0.0;
          return bPct.compareTo(aPct);
        });

      for (final entry in sortedEntries) {
        final pctVal = (entry.value['percentage'] as num?)?.toDouble() ?? 0.0;
        final pctStr = '${(pctVal * 100).toStringAsFixed(1)}%';
        shapWidgets.add(
          Padding(
            padding: const EdgeInsets.only(top: 4.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '- ${entry.key.replaceAll("_", " ").toUpperCase()}:',
                  style: const TextStyle(color: Color(0xFF98A2B3), fontSize: 13),
                ),
                Text(
                  pctStr,
                  style: const TextStyle(color: Color(0xFF00C4FF), fontWeight: FontWeight.bold, fontSize: 13),
                ),
              ],
            ),
          ),
        );
      }
    }

    showDialog<void>(
      context: context,
      builder: (_) {
        return AlertDialog(
          backgroundColor: const Color(0xFF111827),
          title: const Text(
            'Security Insight Breakdown',
            style: TextStyle(color: Color(0xFFE4E7EC)),
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('ML score: ${ml?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
                Text('Graph score: ${graph?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
                Text('Rule penalty: ${rulePenalty?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
                const Divider(color: Color(0xFF344054)),
                Text(
                  'Final risk score: ${finalScore?.toStringAsFixed(3) ?? 'N/A'}',
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFE4E7EC)),
                ),
                Text('Attack type: $attackType', style: const TextStyle(color: Color(0xFFF2F4F7))),
                if (s3Path != null) ...[
                  const SizedBox(height: 12),
                  const Text(
                    'Audit Trace Path (S3):',
                    style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFE4E7EC)),
                  ),
                  Text(
                    s3Path,
                    style: const TextStyle(color: Color(0xFF84CAFF), fontSize: 11),
                  ),
                ],
                ...shapWidgets,
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: const Key('user-dashboard-root'),
      backgroundColor: const Color(0xFF030712),
      appBar: AppBar(
        backgroundColor: const Color(0xFF111827),
        title: const Text(
          'GraphShield User Security Panel',
          style: TextStyle(color: Colors.white),
        ),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _fetchDashboardData,
            icon: const Icon(Icons.refresh, color: Color(0xFFD0D5DD)),
          ),
          TextButton.icon(
            key: const Key('dashboard-logout'),
            onPressed: widget.onLogout,
            icon: const Icon(Icons.logout, color: Color(0xFFD0D5DD)),
            label: const Text(
              'Logout',
              style: TextStyle(color: Color(0xFFD0D5DD)),
            ),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: _loading && _events.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: () => _fetchDashboardData(),
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null)
                    Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF2A130F),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFFFDA29B)),
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Color(0xFFFDA29B)),
                      ),
                    ),
                  _buildStatusPanel(),
                  _buildAlertsPanel(),
                  _buildRecentActivityPanel(),
                  _buildDeviceInsightsPanel(),
                  _buildIpHistoryPanel(),
                ],
              ),
            ),
    );
  }
}
