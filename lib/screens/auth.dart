import 'package:flutter/material.dart';

import '../services/api_service.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    super.key,
    required this.apiService,
    required this.onAuthenticated,
  });

  final ApiService apiService;
  final ValueChanged<AuthSession> onAuthenticated;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen>
    with SingleTickerProviderStateMixin {
  final _loginEmailController = TextEditingController();
  final _loginPasswordController = TextEditingController();
  final _registerEmailController = TextEditingController();
  final _registerPasswordController = TextEditingController();
  final _registerBankNameController = TextEditingController();

  late final TabController _tabController;

  String _loginRole = 'USER';
  String _registerRole = 'USER';
  List<Map<String, dynamic>> _banks = [];
  String? _selectedBankId;
  bool _banksLoading = false;
  bool _isSubmitting = false;
  String? _approvalStatus;
  String? _approvalStateMessage;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loadBanks();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginEmailController.dispose();
    _loginPasswordController.dispose();
    _registerEmailController.dispose();
    _registerPasswordController.dispose();
    _registerBankNameController.dispose();
    super.dispose();
  }

  Future<void> _loadBanks() async {
    setState(() => _banksLoading = true);
    try {
      final banks = await widget.apiService.fetchBanks();
      if (!mounted) {
        return;
      }

      setState(() {
        _banks = banks;
        if (_banks.isEmpty) {
          _selectedBankId = null;
        } else {
          final exists = _banks.any(
            (bank) => bank['bank_id'] == _selectedBankId,
          );
          if (!exists) {
            _selectedBankId = _banks.first['bank_id']?.toString();
          }
        }
      });
    } catch (_) {
      if (!mounted) {
        return;
      }
      setState(() {
        _banks = [];
        _selectedBankId = null;
      });
    } finally {
      if (mounted) {
        setState(() => _banksLoading = false);
      }
    }
  }

  Future<void> _submitLogin() async {
    final email = _loginEmailController.text.trim().toLowerCase();
    final password = _loginPasswordController.text;

    if (email.isEmpty || password.isEmpty) {
      _showMessage('Enter email and password', isError: true);
      return;
    }

    setState(() {
      _isSubmitting = true;
      _approvalStatus = null;
      _approvalStateMessage = null;
    });
    try {
      final result = await widget.apiService.login(
        email: email,
        password: password,
        role: _loginRole,
      );
      if (!mounted) {
        return;
      }
      widget.onAuthenticated(result.session);
    } on ApiException catch (e) {
      final approvalStatus = (e.body?['approval_status'] ?? '')
          .toString()
          .toUpperCase();
      final rejectionReason = (e.body?['reason'] ?? '').toString().trim();
      final looksLikeApprovalDecision =
          e.statusCode == 403 &&
          (approvalStatus.isNotEmpty ||
              e.message.toLowerCase().contains('approval') ||
              e.message.toLowerCase().contains('rejected'));
      if (looksLikeApprovalDecision) {
        final status = approvalStatus.isNotEmpty
            ? approvalStatus
            : e.message.toLowerCase().contains('rejected')
            ? 'REJECTED'
            : 'PENDING';
        setState(() {
          _approvalStatus = status;
          _approvalStateMessage = status == 'REJECTED' && rejectionReason.isNotEmpty
              ? 'Your account was rejected: $rejectionReason'
              : e.message;
        });
      }
      _showMessage(e.message, isError: true);
    } catch (_) {
      _showMessage('Login request failed', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  Future<void> _submitRegister() async {
    final email = _registerEmailController.text.trim().toLowerCase();
    final password = _registerPasswordController.text;
    final requiresBankSelection =
        _registerRole == 'USER' || _registerRole == 'ADMIN';

    if (email.isEmpty || password.isEmpty) {
      _showMessage('Enter email and password', isError: true);
      return;
    }

    if (requiresBankSelection &&
        (_selectedBankId == null || _selectedBankId!.isEmpty)) {
      _showMessage(
        _registerRole == 'ADMIN'
            ? 'Select a bank for admin registration'
            : 'Select a bank for user registration',
        isError: true,
      );
      return;
    }

    if (_registerRole == 'ADMIN' && _banks.isEmpty) {
      _showMessage(
        'Register a bank account first so the admin can be linked to it',
        isError: true,
      );
      return;
    }

    if (_registerRole == 'BANK' &&
        _registerBankNameController.text.trim().isEmpty) {
      _showMessage(
        'Bank name is required for bank registration',
        isError: true,
      );
      return;
    }

    setState(() => _isSubmitting = true);
    try {
      await widget.apiService.register(
        email: email,
        password: password,
        role: _registerRole,
        bankId: requiresBankSelection ? _selectedBankId : null,
        bankName: _registerRole == 'BANK'
            ? _registerBankNameController.text.trim()
            : null,
      );

      if (!mounted) {
        return;
      }

      _showMessage(
        _registerRole == 'USER'
            ? 'Registration successful. Awaiting bank approval.'
            : 'Registration successful. Please login.',
        isError: false,
      );
      _loginEmailController.text = email;
      _tabController.animateTo(0);
      if (_registerRole == 'BANK') {
        await _loadBanks();
      }
    } on ApiException catch (e) {
      _showMessage(e.message, isError: true);
    } catch (_) {
      _showMessage('Registration request failed', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isSubmitting = false);
      }
    }
  }

  void _showMessage(String message, {required bool isError}) {
    if (!mounted) {
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isError
            ? const Color(0xFFB42318)
            : const Color(0xFF067647),
      ),
    );
  }

  InputDecoration _fieldDecoration(String label, IconData icon) {
    return InputDecoration(
      labelText: label,
      prefixIcon: Icon(icon),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFB8C4D6)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFF0E7EA8), width: 1.4),
      ),
      filled: true,
      fillColor: Colors.white,
    );
  }

  Widget _buildLoginForm() {
    final isRejected = _approvalStatus == 'REJECTED';
    final approvalTitle = isRejected
        ? 'Bank Approval Rejected'
        : 'Awaiting Bank Approval';
    final approvalDescription = isRejected
        ? 'Your onboarding request was rejected by the bank. Please contact your bank administrator.'
        : 'Your account is under review by your bank.';

    return Column(
      children: [
        DropdownButtonFormField<String>(
          key: const Key('login-role'),
          initialValue: _loginRole,
          decoration: _fieldDecoration(
            'Login As',
            Icons.manage_accounts_outlined,
          ),
          onChanged: (value) {
            if (value == null) {
              return;
            }
            setState(() => _loginRole = value);
          },
          items: const [
            DropdownMenuItem(value: 'USER', child: Text('User')),
            DropdownMenuItem(value: 'BANK', child: Text('Bank')),
            DropdownMenuItem(value: 'ADMIN', child: Text('Admin')),
          ],
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('login-email'),
          controller: _loginEmailController,
          keyboardType: TextInputType.emailAddress,
          decoration: _fieldDecoration('Email', Icons.email_outlined),
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('login-password'),
          controller: _loginPasswordController,
          obscureText: true,
          decoration: _fieldDecoration('Password', Icons.lock_outline),
        ),
        const SizedBox(height: 18),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            key: const Key('login-submit'),
            onPressed: _isSubmitting ? null : _submitLogin,
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 50),
              backgroundColor: const Color(0xFF0E7EA8),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isSubmitting
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('LOGIN'),
          ),
        ),
        if (_approvalStateMessage != null) ...[
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isRejected
                    ? const Color(0xFFFDA29B)
                    : const Color(0xFFF79009),
              ),
              color: isRejected
                  ? const Color(0xFFFFF1F3)
                  : const Color(0xFFFFFAEB),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      isRejected
                          ? Icons.cancel_outlined
                          : Icons.hourglass_top_rounded,
                      color: isRejected
                          ? const Color(0xFFB42318)
                          : const Color(0xFFB54708),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      approvalTitle,
                      style: TextStyle(
                        color: isRejected
                            ? const Color(0xFFB42318)
                            : const Color(0xFFB54708),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  approvalDescription,
                  style: TextStyle(
                    color: isRejected
                        ? const Color(0xFF912018)
                        : const Color(0xFF7A2E0E),
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _approvalStateMessage!,
                  style: TextStyle(
                    color: isRejected
                        ? const Color(0xFFB42318)
                        : const Color(0xFFB54708),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerLeft,
                  child: OutlinedButton.icon(
                    onPressed: _isSubmitting ? null : _submitLogin,
                    icon: const Icon(Icons.refresh_outlined),
                    label: const Text('Refresh status'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildRegisterForm() {
    return Column(
      children: [
        DropdownButtonFormField<String>(
          key: const Key('register-role'),
          initialValue: _registerRole,
          decoration: _fieldDecoration('Register As', Icons.badge_outlined),
          onChanged: (value) {
            if (value == null) {
              return;
            }
            setState(() => _registerRole = value);
          },
          items: const [
            DropdownMenuItem(value: 'USER', child: Text('User')),
            DropdownMenuItem(value: 'BANK', child: Text('Bank')),
            DropdownMenuItem(value: 'ADMIN', child: Text('Admin')),
          ],
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('register-email'),
          controller: _registerEmailController,
          keyboardType: TextInputType.emailAddress,
          decoration: _fieldDecoration('Email', Icons.email_outlined),
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('register-password'),
          controller: _registerPasswordController,
          obscureText: true,
          decoration: _fieldDecoration('Password', Icons.lock_outline),
        ),
        if (_registerRole == 'USER' || _registerRole == 'ADMIN') ...[
          const SizedBox(height: 14),
          _banksLoading
              ? const LinearProgressIndicator()
              : _banks.isEmpty
              ? Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFF79009)),
                    color: const Color(0xFFFFFAEB),
                  ),
                  child: const Text(
                    'No registered banks available. Register a bank account first.',
                    style: TextStyle(color: Color(0xFFB54708)),
                  ),
                )
              : DropdownButtonFormField<String>(
                  key: const Key('register-bank'),
                  initialValue: _selectedBankId,
                  decoration: _fieldDecoration(
                    _registerRole == 'ADMIN' ? 'Assign Bank' : 'Select Bank',
                    Icons.account_balance_outlined,
                  ),
                  onChanged: (value) => setState(() => _selectedBankId = value),
                  items: _banks
                      .map(
                        (bank) => DropdownMenuItem(
                          value: bank['bank_id']?.toString(),
                          child: Text(
                            (bank['bank_name'] ?? bank['bank_id']).toString(),
                          ),
                        ),
                      )
                      .toList(),
                ),
        ],
        if (_registerRole == 'BANK') ...[
          const SizedBox(height: 14),
          TextField(
            key: const Key('register-bank-name'),
            controller: _registerBankNameController,
            decoration: _fieldDecoration('Bank Name', Icons.account_balance),
          ),
        ],
        const SizedBox(height: 18),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            key: const Key('register-submit'),
            onPressed: _isSubmitting ? null : _submitRegister,
            style: ElevatedButton.styleFrom(
              minimumSize: const Size(double.infinity, 50),
              backgroundColor: const Color(0xFF067647),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isSubmitting
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('REGISTER'),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0xFFF5FAFF), Color(0xFFEFF8FF), Color(0xFFF9FCFF)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 520),
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: const [
                      BoxShadow(
                        color: Color(0x1A101828),
                        blurRadius: 24,
                        offset: Offset(0, 10),
                      ),
                    ],
                    border: Border.all(color: const Color(0xFFE4E7EC)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Row(
                        children: [
                          Icon(
                            Icons.shield_outlined,
                            size: 34,
                            color: Color(0xFF0E7EA8),
                          ),
                          SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              'GraphShield Security Access',
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                color: Color(0xFF0C253E),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'AI + Graph-based zero-trust authentication',
                        style: TextStyle(color: Color(0xFF475467)),
                      ),
                      const SizedBox(height: 20),
                      TabBar(
                        controller: _tabController,
                        indicator: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          color: const Color(0xFF0E7EA8),
                        ),
                        labelColor: Colors.white,
                        unselectedLabelColor: const Color(0xFF475467),
                        indicatorSize: TabBarIndicatorSize.tab,
                        tabs: const [
                          Tab(key: Key('login-tab'), text: 'Login'),
                          Tab(key: Key('register-tab'), text: 'Register'),
                        ],
                      ),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 420,
                        child: TabBarView(
                          controller: _tabController,
                          children: [_buildLoginForm(), _buildRegisterForm()],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
