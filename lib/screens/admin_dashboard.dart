import 'dart:async';

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:graphview/GraphView.dart';

import '../services/api_service.dart';

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({
    super.key,
    required this.apiService,
    required this.session,
    required this.onLogout,
  });

  final ApiService apiService;
  final AuthSession session;
  final Future<void> Function() onLogout;

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  Timer? _pollTimer;

  bool _loading = false;
  String? _error;

  int _totalEvents = 0;
  int _blocks = 0;
  int _allows = 0;

  List<Map<String, dynamic>> _latestEvents = [];
  List<String> _graphInsights = [];
  Map<String, dynamic> _graphData = {};
  List<Map<String, dynamic>> _attemptsVsDays = [];
  Map<String, dynamic> _suspiciousPatterns = {};
  List<Map<String, dynamic>> _pendingUsers = [];
  Map<String, dynamic>? _subscription;
  List<Map<String, dynamic>> _subscriptionRequests = [];
  String? _subscriptionActionRequestId;
  String? _pendingUserActionId;
  bool _subscriptionPopupShown = false;

  @override
  void initState() {
    super.initState();
    _refreshDashboard();
    _pollTimer = Timer.periodic(
      const Duration(seconds: 4),
      (_) => _refreshDashboard(silent: true),
    );
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  Future<void> _refreshDashboard({bool silent = false}) async {
    if (!silent) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    var stage = 'analytics';
    try {
      String? nonBlockingError;

      final analytics = await widget.apiService.fetchAdminDashboard();
      stage = 'graph insights';
      List<String> insights = [];
      try {
        insights = await widget.apiService.fetchGraphInsights();
      } on ApiException catch (e) {
        nonBlockingError = 'Graph insights unavailable: ${e.message}';
      } catch (e) {
        nonBlockingError = 'Graph insights unavailable: $e';
      }

      stage = 'graph data';
      var gData = <String, dynamic>{'nodes': [], 'edges': []};
      try {
        gData = await widget.apiService.fetchGraphData();
      } on ApiException catch (e) {
        nonBlockingError ??= 'Graph data unavailable: ${e.message}';
      } catch (e) {
        nonBlockingError ??= 'Graph data unavailable: $e';
      }

      stage = 'pending approvals';
      List<Map<String, dynamic>> pendingUsers = [];
      try {
        pendingUsers = await widget.apiService.fetchPendingApprovals();
      } on ApiException catch (e) {
        nonBlockingError ??= 'Pending approvals unavailable: ${e.message}';
      } catch (e) {
        nonBlockingError ??= 'Pending approvals unavailable: $e';
      }

      stage = 'subscription status';
      Map<String, dynamic>? subscription;
      try {
        subscription = await widget.apiService.fetchSubscriptionStatus();
      } on ApiException catch (e) {
        nonBlockingError ??= 'Subscription status unavailable: ${e.message}';
      } catch (e) {
        nonBlockingError ??= 'Subscription status unavailable: $e';
      }

      stage = 'subscription approvals';
      List<Map<String, dynamic>> subscriptionRequests = [];
      if (widget.session.role == 'ADMIN') {
        try {
          subscriptionRequests = await widget.apiService
              .fetchSubscriptionRequests();
        } on ApiException catch (e) {
          nonBlockingError ??=
              'Subscription approvals unavailable: ${e.message}';
        } catch (e) {
          nonBlockingError ??= 'Subscription approvals unavailable: $e';
        }
      }

      final latest = (analytics['latest'] as List<dynamic>? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

      final totalEvents =
          (analytics['total_events'] as num?)?.toInt() ?? latest.length;
      final blocks = (analytics['blocks'] as num?)?.toInt() ?? 0;
      final allows =
          (analytics['allows'] as num?)?.toInt() ??
          (totalEvents - blocks).clamp(0, totalEvents).toInt();
      final attemptsVsDaysRaw =
          (analytics['attempts_vs_days'] as List<dynamic>? ?? [])
              .map((e) => Map<String, dynamic>.from(e as Map))
              .toList();
      final suspiciousPatterns =
          (analytics['suspicious_patterns'] as Map<String, dynamic>?) ?? {};

      if (!mounted) {
        return;
      }

      setState(() {
        _error = nonBlockingError;
        _latestEvents = latest;
        _graphInsights = insights;
        _graphData = gData;
        _pendingUsers = pendingUsers;
        _totalEvents = totalEvents;
        _blocks = blocks;
        _allows = allows;
        _attemptsVsDays = attemptsVsDaysRaw;
        _suspiciousPatterns = suspiciousPatterns;
        _subscription =
            subscription ??
            (analytics['subscription'] as Map<String, dynamic>?);
        _subscriptionRequests = subscriptionRequests;
      });

      if (mounted &&
          widget.session.role == 'BANK' &&
          !_subscriptionPopupShown &&
          ((_subscription?['requires_subscription'] ?? false) == true)) {
        _subscriptionPopupShown = true;
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) {
            _showSubscriptionRequiredPopup();
          }
        });
      }
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      setState(
        () =>
            _error = 'Failed to refresh admin dashboard ($stage): ${e.message}',
      );
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() => _error = 'Failed to refresh admin dashboard ($stage): $e');
    } finally {
      if (mounted && !silent) {
        setState(() => _loading = false);
      }
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
    return 'Unknown';
  }

  String _pad(int value) => value.toString().padLeft(2, '0');

  Color _decisionColor(String decision) {
    switch (decision) {
      case 'BLOCK':
        return const Color(0xFFF04438);
      default:
        return const Color(0xFF32D583);
    }
  }

  IconData _decisionIcon(String decision) {
    switch (decision) {
      case 'BLOCK':
        return Icons.gpp_bad_outlined;
      default:
        return Icons.verified_user_outlined;
    }
  }

  Widget _panel({required String title, required Widget child}) {
    return Container(
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

  Widget _statCard(String label, int value, Color color) {
    return Expanded(
      child: Container(
        height: 92,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.55)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(label, style: const TextStyle(color: Color(0xFF98A2B3))),
            const SizedBox(height: 6),
            Text(
              '$value',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w800,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Map<String, dynamic>> _buildUserRiskRows() {
    final byUser = <String, Map<String, dynamic>>{};

    for (final event in _latestEvents) {
      final userId = (event['user_id'] ?? 'unknown').toString();
      final score = (event['final_score'] as num?)?.toDouble() ?? 0.0;
      final decision = (event['decision'] ?? 'UNKNOWN')
          .toString()
          .toUpperCase();

      final bucket = byUser.putIfAbsent(
        userId,
        () => {
          'user_id': userId,
          'sum': 0.0,
          'count': 0,
          'max': 0.0,
          'status': decision,
        },
      );

      bucket['sum'] = (bucket['sum'] as double) + score;
      bucket['count'] = (bucket['count'] as int) + 1;
      bucket['max'] = (bucket['max'] as double) < score ? score : bucket['max'];
      bucket['status'] = decision;
    }

    final rows = byUser.values.map((row) {
      final count = row['count'] as int;
      final avg = count == 0 ? 0.0 : (row['sum'] as double) / count;
      return {
        'user_id': row['user_id'],
        'avg': avg,
        'max': row['max'],
        'status': row['status'],
      };
    }).toList();

    rows.sort((a, b) => (b['avg'] as double).compareTo(a['avg'] as double));
    return rows;
  }

  List<String> _buildAlerts() {
    final alerts = <String>[];

    if (_blocks > 0) {
      alerts.add('Replay or attack payload patterns are being blocked.');
    }
    final deviceReuseRows =
        (_suspiciousPatterns['device_reuse'] as List<dynamic>? ?? [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
    final ipRotationRows =
        (_suspiciousPatterns['ip_rotation'] as List<dynamic>? ?? [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
    if (deviceReuseRows.isNotEmpty) {
      alerts.add('Suspicious device reuse detected across multiple users.');
    }
    if (ipRotationRows.isNotEmpty) {
      alerts.add('Suspicious IP rotation detected for one or more users.');
    }

    for (final insight in _graphInsights) {
      if (insight.contains('Botnet')) {
        alerts.add('Botnet activity: $insight');
      }
      if (insight.contains('IP Rotation')) {
        alerts.add('IP rotation anomaly: $insight');
      }
    }

    if (alerts.isEmpty) {
      alerts.add('No critical alerts right now. Security controls are active.');
    }

    return alerts;
  }

  void _showSecurityInsights([Map<String, dynamic>? selectedEvent]) {
    final event = selectedEvent ?? (_latestEvents.isNotEmpty ? _latestEvents.first : null);
    if (event == null) {
      return;
    }

    final ml = (event['ml_score'] as num?)?.toDouble();
    final graph = (event['graph_score'] as num?)?.toDouble();
    final rulePenalty = (event['rule_penalty'] as num?)?.toDouble();
    final finalScore = (event['final_score'] as num?)?.toDouble();
    final s3Path = event['s3_path']?.toString();

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
      builder: (_) => AlertDialog(
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
              Text('User: ${event['user_id']}', style: const TextStyle(color: Color(0xFFF2F4F7))),
              const SizedBox(height: 6),
              Text('ML score: ${ml?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
              Text('Graph score: ${graph?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
              Text('Rule penalty: ${rulePenalty?.toStringAsFixed(3) ?? 'N/A'}', style: const TextStyle(color: Color(0xFFF2F4F7))),
              const Divider(color: Color(0xFF344054)),
              Text(
                'Final score: ${finalScore?.toStringAsFixed(3) ?? 'N/A'}',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFFE4E7EC)),
              ),
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
      ),
    );
  }

  String _formatIsoDate(dynamic raw) {
    if (raw == null) {
      return 'N/A';
    }
    final value = raw.toString().trim();
    if (value.isEmpty) {
      return 'N/A';
    }
    try {
      final dt = DateTime.parse(value).toLocal();
      return '${dt.year}-${_pad(dt.month)}-${_pad(dt.day)}';
    } catch (_) {
      return value;
    }
  }

  Future<void> _showSubscriptionRequiredPopup() async {
    if (widget.session.role != 'BANK') {
      return;
    }
    final trialEnd = _formatIsoDate(_subscription?['trial_end_at']);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Subscription Required'),
          content: Text(
            'Your 1-month free trial has ended (trial end: $trialEnd). Please subscribe to continue using enforcement features.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Later'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                _openSubscribeDialog();
              },
              child: const Text('Subscribe Now'),
            ),
          ],
        );
      },
    );
  }

  Future<void> _openSubscribeDialog() async {
    if (widget.session.role != 'BANK') {
      return;
    }
    var selectedPlan = 'PLAN_6_MONTHS';
    var selectedPayment = 'BANK_TRANSFER';
    final transactionController = TextEditingController();
    var submitting = false;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: const Text('Choose Subscription Plan'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    DropdownButtonFormField<String>(
                      initialValue: selectedPlan,
                      decoration: const InputDecoration(
                        labelText: 'Subscription Plan',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'PLAN_6_MONTHS',
                          child: Text('6 Months'),
                        ),
                        DropdownMenuItem(
                          value: 'PLAN_1_YEAR',
                          child: Text('1 Year'),
                        ),
                        DropdownMenuItem(
                          value: 'PLAN_5_YEARS',
                          child: Text('5 Years'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        setDialogState(() => selectedPlan = value);
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedPayment,
                      decoration: const InputDecoration(
                        labelText: 'Payment Method',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'BANK_TRANSFER',
                          child: Text('Bank Transfer'),
                        ),
                        DropdownMenuItem(value: 'UPI', child: Text('UPI')),
                        DropdownMenuItem(value: 'CARD', child: Text('Card')),
                      ],
                      onChanged: (value) {
                        if (value == null) {
                          return;
                        }
                        setDialogState(() => selectedPayment = value);
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: transactionController,
                      decoration: const InputDecoration(
                        labelText: 'Transaction No.',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: submitting
                      ? null
                      : () {
                          Navigator.pop(dialogContext);
                        },
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: submitting
                      ? null
                      : () async {
                          final transactionNo = transactionController.text
                              .trim();
                          if (transactionNo.length < 4) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Please enter a valid transaction number',
                                ),
                                backgroundColor: Color(0xFFB42318),
                              ),
                            );
                            return;
                          }

                          setDialogState(() => submitting = true);
                          try {
                            await widget.apiService.submitSubscriptionRequest(
                              planCode: selectedPlan,
                              paymentMethod: selectedPayment,
                              transactionNo: transactionNo,
                            );
                            if (!mounted) {
                              return;
                            }
                            Navigator.pop(dialogContext);
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Subscription request submitted for admin approval',
                                ),
                                backgroundColor: Color(0xFF067647),
                              ),
                            );
                            _subscriptionPopupShown = true;
                            await _refreshDashboard(silent: false);
                          } on ApiException catch (e) {
                            if (!mounted) {
                              return;
                            }
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(e.message),
                                backgroundColor: const Color(0xFFB42318),
                              ),
                            );
                          } finally {
                            if (mounted) {
                              setDialogState(() => submitting = false);
                            }
                          }
                        },
                  child: submitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Submit'),
                ),
              ],
            );
          },
        );
      },
    );
    transactionController.dispose();
  }

  Future<void> _decideSubscriptionRequest(
    String requestId, {
    required bool approve,
  }) async {
    String? reason;
    if (!approve) {
      reason = await _promptSubscriptionRejectReason();
      if (reason == null) {
        return;
      }
    }

    setState(() => _subscriptionActionRequestId = requestId);
    try {
      await widget.apiService.decideSubscriptionRequest(
        requestId,
        approve: approve,
        reason: reason,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            approve
                ? 'Subscription approved successfully'
                : 'Subscription rejected successfully',
          ),
          backgroundColor: approve
              ? const Color(0xFF067647)
              : const Color(0xFFB42318),
        ),
      );
      await _refreshDashboard(silent: false);
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: const Color(0xFFB42318),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _subscriptionActionRequestId = null);
      }
    }
  }

  Future<void> _approvePendingUser(String userId) async {
    setState(() => _pendingUserActionId = userId);
    try {
      await widget.apiService.approveUser(userId);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('User approved successfully'),
          backgroundColor: Color(0xFF067647),
        ),
      );
      await _refreshDashboard(silent: false);
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: const Color(0xFFB42318),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _pendingUserActionId = null);
      }
    }
  }

  Future<String?> _promptSubscriptionRejectReason() async {
    final controller = TextEditingController();
    final reason = await showDialog<String>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Reject Subscription'),
          content: TextField(
            controller: controller,
            maxLength: 200,
            autofocus: true,
            decoration: const InputDecoration(
              labelText: 'Reason',
              hintText: 'Example: Invalid transaction number',
              border: OutlineInputBorder(),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                final value = controller.text.trim();
                if (value.isEmpty) {
                  return;
                }
                Navigator.pop(dialogContext, value);
              },
              child: const Text('Reject'),
            ),
          ],
        );
      },
    );
    controller.dispose();
    return reason;
  }

  Widget _buildSubscriptionStatusPanel() {
    final sub = _subscription;
    if (sub == null) {
      return const SizedBox.shrink();
    }
    final status = (sub['status'] ?? 'UNKNOWN').toString();
    final plan = (sub['plan_code'] ?? 'N/A').toString();
    final trialEnd = _formatIsoDate(sub['trial_end_at']);
    final expiry = _formatIsoDate(sub['subscription_expires_at']);
    final requires = (sub['requires_subscription'] ?? false) == true;

    return _panel(
      title: 'Subscription Status',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Status: $status',
            style: const TextStyle(color: Color(0xFFE4E7EC)),
          ),
          const SizedBox(height: 4),
          Text('Plan: $plan', style: const TextStyle(color: Color(0xFFE4E7EC))),
          const SizedBox(height: 4),
          Text(
            'Trial ends: $trialEnd',
            style: const TextStyle(color: Color(0xFF98A2B3)),
          ),
          const SizedBox(height: 4),
          Text(
            'Subscription expires: $expiry',
            style: const TextStyle(color: Color(0xFF98A2B3)),
          ),
          if (requires && widget.session.role == 'BANK') ...[
            const SizedBox(height: 10),
            const Text(
              'Subscription required to continue after trial.',
              style: TextStyle(
                color: Color(0xFFF97066),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSubscriptionApprovalsPanel() {
    if (widget.session.role != 'ADMIN') {
      return const SizedBox.shrink();
    }
    return _panel(
      title: 'Subscription Approvals',
      child: _subscriptionRequests.isEmpty
          ? const Text(
              'No pending subscription requests.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingTextStyle: const TextStyle(
                  color: Color(0xFFD0D5DD),
                  fontWeight: FontWeight.w700,
                ),
                dataTextStyle: const TextStyle(color: Color(0xFFF2F4F7)),
                columns: const [
                  DataColumn(label: Text('Bank')),
                  DataColumn(label: Text('Plan')),
                  DataColumn(label: Text('Payment')),
                  DataColumn(label: Text('Transaction No')),
                  DataColumn(label: Text('Created')),
                  DataColumn(label: Text('Action')),
                ],
                rows: _subscriptionRequests.map((item) {
                  final requestId = (item['request_id'] ?? '').toString();
                  final isActing = _subscriptionActionRequestId == requestId;
                  return DataRow(
                    cells: [
                      DataCell(
                        Text(
                          (item['bank_name'] ?? item['bank_id'] ?? 'N/A')
                              .toString(),
                        ),
                      ),
                      DataCell(Text((item['plan_code'] ?? 'N/A').toString())),
                      DataCell(
                        Text((item['payment_method'] ?? 'N/A').toString()),
                      ),
                      DataCell(
                        Text((item['transaction_no'] ?? 'N/A').toString()),
                      ),
                      DataCell(Text(_formatIsoDate(item['created_at']))),
                      DataCell(
                        Row(
                          children: [
                            ElevatedButton(
                              onPressed: isActing
                                  ? null
                                  : () => _decideSubscriptionRequest(
                                      requestId,
                                      approve: true,
                                    ),
                              child: const Text('Approve'),
                            ),
                            const SizedBox(width: 8),
                            OutlinedButton(
                              onPressed: isActing
                                  ? null
                                  : () => _decideSubscriptionRequest(
                                      requestId,
                                      approve: false,
                                    ),
                              child: const Text('Reject'),
                            ),
                          ],
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
    );
  }

  Widget _buildSystemOverview() {
    return _panel(
      title: 'System Overview',
      child: Row(
        children: [
          _statCard('Total attempts', _totalEvents, const Color(0xFF84CAFF)),
          const SizedBox(width: 10),
          _statCard('Blocked attempts', _blocks, const Color(0xFFF04438)),
          const SizedBox(width: 10),
          _statCard('Allowed attempts', _allows, const Color(0xFF32D583)),
        ],
      ),
    );
  }

  Widget _buildAttemptsVsDaysChart() {
    if (_attemptsVsDays.isEmpty && _latestEvents.isEmpty) {
      return _panel(
        title: 'Attempts vs Days',
        child: const Text(
          'No login data available for chart.',
          style: TextStyle(color: Color(0xFF98A2B3)),
        ),
      );
    }

    final labels = <String>[];
    final values = <double>[];
    if (_attemptsVsDays.isNotEmpty) {
      for (final point in _attemptsVsDays) {
        final label = (point['day'] ?? '').toString();
        final attempts = (point['attempts'] as num?)?.toDouble() ?? 0.0;
        if (label.isEmpty) {
          continue;
        }
        labels.add(label.substring(label.length - 2));
        values.add(attempts);
      }
    } else {
      final countsByDay = <int, int>{};
      for (final event in _latestEvents) {
        final ts = (event['timestamp'] as num?)?.toDouble();
        if (ts == null) continue;
        final dt = DateTime.fromMillisecondsSinceEpoch(
          (ts * 1000).toInt(),
          isUtc: true,
        ).toLocal();
        final dayKey = dt.day;
        countsByDay[dayKey] = (countsByDay[dayKey] ?? 0) + 1;
      }
      final sortedKeys = countsByDay.keys.toList()..sort();
      for (final key in sortedKeys) {
        labels.add(key.toString());
        values.add((countsByDay[key] ?? 0).toDouble());
      }
    }

    if (values.isEmpty) {
      return const SizedBox.shrink();
    }

    final spots = <FlSpot>[];
    double maxCount = 0;

    for (int i = 0; i < values.length; i++) {
      final count = values[i];
      if (count > maxCount) maxCount = count;
      spots.add(FlSpot(i.toDouble(), count));
    }

    return _panel(
      title: 'Attempts vs Days',
      child: SizedBox(
        height: 200,
        child: LineChart(
          LineChartData(
            gridData: FlGridData(show: true, drawVerticalLine: false),
            titlesData: FlTitlesData(
              bottomTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  getTitlesWidget: (value, meta) {
                    final int index = value.toInt();
                    if (index >= 0 && index < labels.length) {
                      return Padding(
                        padding: const EdgeInsets.only(top: 8.0),
                        child: Text(
                          labels[index],
                          style: const TextStyle(
                            color: Color(0xFFD0D5DD),
                            fontSize: 12,
                          ),
                        ),
                      );
                    }
                    return const Text('');
                  },
                ),
              ),
              leftTitles: AxisTitles(
                sideTitles: SideTitles(
                  showTitles: true,
                  reservedSize: 40,
                  getTitlesWidget: (value, meta) {
                    return Text(
                      '${value.toInt()}',
                      style: const TextStyle(
                        color: Color(0xFFD0D5DD),
                        fontSize: 12,
                      ),
                    );
                  },
                ),
              ),
              topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
              rightTitles: AxisTitles(
                sideTitles: SideTitles(showTitles: false),
              ),
            ),
            borderData: FlBorderData(show: false),
            minX: 0,
            maxX: (labels.length - 1).toDouble() > 0
                ? (labels.length - 1).toDouble()
                : 1,
            minY: 0,
            maxY: maxCount + 2,
            lineBarsData: [
              LineChartBarData(
                spots: spots.isEmpty ? [FlSpot(0, 0)] : spots,
                isCurved: true,
                color: const Color(0xFF00C4FF),
                barWidth: 3,
                isStrokeCapRound: true,
                dotData: FlDotData(show: true),
                belowBarData: BarAreaData(
                  show: true,
                  color: const Color(0xFF00C4FF).withValues(alpha: 0.15),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLiveThreatFeed() {
    return _panel(
      title: 'Live Threat Feed',
      child: _latestEvents.isEmpty
          ? const Text(
              'No outsider suspicious logins detected yet.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : Column(
              children: _latestEvents.take(12).map((event) {
                final decision = (event['decision'] ?? 'UNKNOWN')
                    .toString()
                    .toUpperCase();
                final color = _decisionColor(decision);
                final userId = (event['user_id'] ?? 'unknown').toString();
                final reason = _deriveReason(event);

                return Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    color: const Color(0xFF0B1220),
                    border: Border.all(color: color.withValues(alpha: 0.6)),
                  ),
                  child: ListTile(
                    dense: true,
                    onTap: () => _showSecurityInsights(event),
                    leading: Icon(_decisionIcon(decision), color: color),
                    title: Text(
                      '$decision | $userId',
                      style: TextStyle(
                        color: color,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    subtitle: Text(
                      '$reason | ${_formatTimestamp(event['timestamp'])}',
                      style: const TextStyle(color: Color(0xFF98A2B3)),
                    ),
                  ),
                );
              }).toList(),
            ),
    );
  }

  String _deriveReason(Map<String, dynamic> event) {
    final features = event['features'] as Map<String, dynamic>?;
    if ((event['botnet_suspected'] == true)) {
      return 'Botnet detected';
    }
    if ((event['ip_rotation_suspected'] == true)) {
      return 'IP rotation detected';
    }
    if ((features?['is_new_device'] as num?)?.toInt() == 1) {
      return 'New device';
    }
    if (((features?['failed_attempts'] as num?)?.toInt() ?? 0) > 3) {
      return 'Multiple failed attempts';
    }
    return 'Normal authentication path';
  }

  Widget _buildGraphInsights() {
    final nodesRaw = _graphData['nodes'] as List<dynamic>? ?? [];
    final edgesRaw = _graphData['edges'] as List<dynamic>? ?? [];

    if (nodesRaw.isEmpty) {
      return _panel(
        title: 'Network Graph Visualization',
        child: const Text(
          'No graph topology available.',
          style: TextStyle(color: Color(0xFF98A2B3)),
        ),
      );
    }

    final Graph graph = Graph()..isTree = false;

    // We will parse nodes and collect suspicious info
    final Map<String, Node> createdNodes = {};
    final suspiciousNodes = <String>{};

    // Analyze Insights to flag suspicious nodes (IPs, Users, etc.)
    for (final insight in _graphInsights) {
      if (insight.contains('IP ')) {
        final match = RegExp(r'IP ([\d\.]+)').firstMatch(insight);
        if (match != null) suspiciousNodes.add(match.group(1)!);
      }
      if (insight.contains('User ')) {
        final match = RegExp(r'User ([A-Za-z0-9_\-]+)').firstMatch(insight);
        if (match != null) suspiciousNodes.add(match.group(1)!);
      }
      if (insight.contains('Device ')) {
        final match = RegExp(r'Device ([A-Za-z0-9_\-\.]+)').firstMatch(insight);
        if (match != null) suspiciousNodes.add(match.group(1)!);
      }
    }

    for (final nodeObj in nodesRaw) {
      final n = nodeObj as Map<String, dynamic>;
      final id =
          n['properties']?['user_id'] ??
          n['properties']?['device_id'] ??
          n['properties']?['ip'] ??
          n['properties']?['bank_id'] ??
          n['id'].toString();
      final node = Node.Id(id);
      createdNodes[n['id'].toString()] = node;
      graph.addNode(node);
    }

    for (final edgeObj in edgesRaw) {
      final e = edgeObj as Map<String, dynamic>;
      final Node? src = createdNodes[e['source'].toString()];
      final Node? dst = createdNodes[e['target'].toString()];
      if (src != null && dst != null) {
        graph.addEdge(
          src,
          dst,
          paint: Paint()
            ..color = const Color(0xFF344054)
            ..strokeWidth = 1.5,
        );
      }
    }

    return _panel(
      title: 'Network Graph Visualization',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _graphInsights.isEmpty
              ? const SizedBox.shrink()
              : Column(
                  children: _graphInsights.map((insight) {
                    final isBotnet = insight.contains('Botnet');
                    final color = isBotnet
                        ? const Color(0xFFF04438)
                        : const Color(0xFFF79009);
                    return Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: color.withValues(alpha: 0.65),
                        ),
                      ),
                      child: Text(
                        insight,
                        style: const TextStyle(color: Color(0xFFF2F4F7)),
                      ),
                    );
                  }).toList(),
                ),
          const SizedBox(height: 10),
          SizedBox(
            height: 350,
            child: InteractiveViewer(
              constrained: false,
              boundaryMargin: const EdgeInsets.all(100),
              minScale: 0.1,
              maxScale: 3.0,
              child: GraphView(
                graph: graph,
                algorithm: FruchtermanReingoldAlgorithm(
                  FruchtermanReingoldConfiguration(),
                ),
                paint: Paint()
                  ..color = const Color(0xFF344054)
                  ..strokeWidth = 1.0
                  ..style = PaintingStyle.stroke,
                builder: (Node node) {
                  final nodeIdStr = node.key?.value.toString() ?? '';
                  final isSuspicious = suspiciousNodes.contains(nodeIdStr);

                  // Find node logic
                  final n = nodesRaw.firstWhere((x) {
                    final props = x['properties'] ?? {};
                    return (props['user_id'] == nodeIdStr ||
                        props['device_id'] == nodeIdStr ||
                        props['ip'] == nodeIdStr ||
                        props['bank_id'] == nodeIdStr ||
                        x['id'].toString() == nodeIdStr);
                  }, orElse: () => {'label': 'Unknown'});

                  final label = n['label']?.toString() ?? 'Unknown';

                  Color color;
                  switch (label) {
                    case 'User':
                      color = const Color(0xFF2E90FA);
                      break; // Blue
                    case 'Device':
                      color = const Color(0xFF12B76A);
                      break; // Green
                    case 'IP':
                      color = const Color(0xFFFDB022);
                      break; // Yellow
                    case 'Bank':
                      color = const Color(0xFF9E77ED);
                      break; // Purple
                    default:
                      color = Colors.grey;
                  }
                  if (isSuspicious) {
                    color = const Color(0xFFF04438); // Red for suspicious
                  }

                  return Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(6),
                      boxShadow: [
                        BoxShadow(
                          color: color.withValues(alpha: 0.4),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Text(
                      nodeIdStr,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildUserRiskTable() {
    final rows = _buildUserRiskRows();

    return _panel(
      title: 'User Risk Table',
      child: rows.isEmpty
          ? const Text(
              'No user risk rows available.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingTextStyle: const TextStyle(
                  color: Color(0xFFD0D5DD),
                  fontWeight: FontWeight.w700,
                ),
                dataTextStyle: const TextStyle(color: Color(0xFFF2F4F7)),
                columns: const [
                  DataColumn(label: Text('User ID')),
                  DataColumn(label: Text('Avg Risk')),
                  DataColumn(label: Text('Max Risk')),
                  DataColumn(label: Text('Status')),
                ],
                rows: rows.take(12).map((row) {
                  final status = row['status'].toString();
                  final color = _decisionColor(status);
                  return DataRow(
                    cells: [
                      DataCell(Text(row['user_id'].toString())),
                      DataCell(Text((row['avg'] as double).toStringAsFixed(3))),
                      DataCell(Text((row['max'] as double).toStringAsFixed(3))),
                      DataCell(
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: color.withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(status, style: TextStyle(color: color)),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
    );
  }

  Widget _buildAlertPanel() {
    final alerts = _buildAlerts();

    return _panel(
      title: 'Alert Panel',
      child: Column(
        children: alerts
            .map(
              (alert) => Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFF2A130F),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFB54708)),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.report_gmailerrorred_outlined,
                      color: Color(0xFFF79009),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        alert,
                        style: const TextStyle(color: Color(0xFFFEC84B)),
                      ),
                    ),
                  ],
                ),
              ),
            )
            .toList(),
      ),
    );
  }

  Widget _buildPendingApprovalsPanel() {
    return _panel(
      title: 'Pending User Approvals',
      child: _pendingUsers.isEmpty
          ? const Text(
              'No pending users for approval.',
              style: TextStyle(color: Color(0xFF98A2B3)),
            )
          : SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                headingTextStyle: const TextStyle(
                  color: Color(0xFFD0D5DD),
                  fontWeight: FontWeight.w700,
                ),
                dataTextStyle: const TextStyle(color: Color(0xFFF2F4F7)),
                columns: const [
                  DataColumn(label: Text('User')),
                  DataColumn(label: Text('Bank')),
                  DataColumn(label: Text('Status')),
                  DataColumn(label: Text('Created')),
                  DataColumn(label: Text('Action')),
                ],
                rows: _pendingUsers.map((user) {
                  final userId = (user['user_id'] ?? '').toString();
                  final status = (user['approval_status'] ?? 'PENDING')
                      .toString()
                      .toUpperCase();
                  final bankLabel =
                      (user['bank_name'] ?? user['bank_id'] ?? 'N/A')
                          .toString();
                  final userLabel =
                      (user['username'] ?? user['email'] ?? userId).toString();
                  final createdAt = user['created_at']?.toString() ?? 'N/A';
                  final isActing = _pendingUserActionId == userId;

                  return DataRow(
                    cells: [
                      DataCell(Text(userLabel)),
                      DataCell(Text(bankLabel)),
                      DataCell(
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFFF79009,
                            ).withValues(alpha: 0.16),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            status,
                            style: const TextStyle(color: Color(0xFFF79009)),
                          ),
                        ),
                      ),
                      DataCell(Text(createdAt)),
                      DataCell(
                        ElevatedButton(
                          key: Key('approve-user-$userId'),
                          onPressed: isActing
                              ? null
                              : () => _approvePendingUser(userId),
                          child: isActing
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Text('Approve'),
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: Key(
        widget.session.role == 'BANK'
            ? 'bank-dashboard-root'
            : 'admin-dashboard-root',
      ),
      backgroundColor: const Color(0xFF030712),
      appBar: AppBar(
        backgroundColor: const Color(0xFF111827),
        title: const Text('GraphShield Security Operations'),
        actions: [
          if (widget.session.role == 'BANK')
            OutlinedButton.icon(
              key: const Key('bank-subscribe-button'),
              onPressed: _openSubscribeDialog,
              icon: const Icon(
                Icons.workspace_premium,
                color: Color(0xFFD0D5DD),
              ),
              label: const Text(
                'Subscribe',
                style: TextStyle(color: Color(0xFFD0D5DD)),
              ),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Color(0xFF344054)),
              ),
            ),
          if (widget.session.role == 'BANK') const SizedBox(width: 8),
          OutlinedButton.icon(
            onPressed: _latestEvents.isEmpty ? null : _showSecurityInsights,
            icon: const Icon(Icons.insights_outlined, color: Color(0xFFD0D5DD)),
            label: const Text(
              'View Security Insights',
              style: TextStyle(color: Color(0xFFD0D5DD)),
            ),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: Color(0xFF344054)),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _refreshDashboard,
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
          const SizedBox(width: 6),
        ],
      ),
      body: _loading && _latestEvents.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _refreshDashboard,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  if (_error != null)
                    Container(
                      margin: const EdgeInsets.only(bottom: 12),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFFFDA29B)),
                        color: const Color(0xFF2A130F),
                      ),
                      child: Text(
                        _error!,
                        style: const TextStyle(color: Color(0xFFFDA29B)),
                      ),
                    ),
                  _buildSubscriptionStatusPanel(),
                  _buildSubscriptionApprovalsPanel(),
                  _buildSystemOverview(),
                  _buildAttemptsVsDaysChart(),
                  _buildPendingApprovalsPanel(),
                  _buildLiveThreatFeed(),
                  _buildGraphInsights(),
                  _buildUserRiskTable(),
                  _buildAlertPanel(),
                ],
              ),
            ),
    );
  }
}
