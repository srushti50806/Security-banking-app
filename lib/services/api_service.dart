import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

class ApiException implements Exception {
  ApiException({required this.message, this.statusCode, this.body});

  final String message;
  final int? statusCode;
  final Map<String, dynamic>? body;

  @override
  String toString() {
    if (statusCode == null) {
      return message;
    }
    return '[$statusCode] $message';
  }
}

class AuthSession {
  const AuthSession({
    required this.role,
    this.userId,
    this.sessionId,
    this.token,
    this.email,
    this.risk,
  });

  final String role;
  final String? userId;
  final String? sessionId;
  final String? token;
  final String? email;
  final Map<String, dynamic>? risk;

  bool get isAuthenticated => token != null;

  AuthSession copyWith({
    String? role,
    String? userId,
    String? sessionId,
    String? token,
    String? email,
    Map<String, dynamic>? risk,
  }) {
    return AuthSession(
      role: role ?? this.role,
      userId: userId ?? this.userId,
      sessionId: sessionId ?? this.sessionId,
      token: token ?? this.token,
      email: email ?? this.email,
      risk: risk ?? this.risk,
    );
  }

  static AuthSession fromAccessToken(
    String token, {
    String? email,
    String? sessionId,
    Map<String, dynamic>? risk,
  }) {
    final claims = ApiService.decodeJwtPayload(token);
    return AuthSession(
      role: (claims['role'] ?? 'USER').toString().toUpperCase(),
      userId: claims['user_id']?.toString(),
      sessionId: sessionId ?? claims['session_id']?.toString(),
      token: token,
      email: email,
      risk: risk,
    );
  }
}

class LoginResult {
  const LoginResult({required this.session, required this.raw});

  final AuthSession session;
  final Map<String, dynamic> raw;
}

class ApiService {
  ApiService();

  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'graphshield_access_token';

  String? _accessToken;
  VoidCallback? onUnauthorized;

  String get _baseUrl {
    final value = dotenv.env['API_BASE_URL'] ?? 'http://127.0.0.1:5000';
    return value.replaceAll(RegExp(r'/+$'), '');
  }

  String? get accessToken => _accessToken;

  Future<void> initialize() async {
    _accessToken = await _storage.read(key: _tokenKey);
  }

  Future<AuthSession?> restoreSession() async {
    final token = _accessToken;
    if (token == null || token.isEmpty) {
      return null;
    }
    final claims = decodeJwtPayload(token);
    if (claims.isEmpty) {
      await clearSession();
      return null;
    }
    return AuthSession.fromAccessToken(token);
  }

  Future<void> persistAccessToken(String token) async {
    _accessToken = token;
    await _storage.write(key: _tokenKey, value: token);
  }

  Future<void> clearSession() async {
    _accessToken = null;
    await _storage.delete(key: _tokenKey);
  }

  Future<List<Map<String, dynamic>>> fetchBanks() async {
    final response = await _request(
      'GET',
      '/api/v1/banks',
      requiresAuth: false,
      triggerUnauthorized: false,
    );
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! List) {
      throw _toException(response, body);
    }

    return body
        .whereType<Map<String, dynamic>>()
        .where((row) => (row['bank_id'] ?? '').toString().isNotEmpty)
        .toList();
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String role,
    String? bankId,
    String? bankName,
  }) async {
    final payload = <String, dynamic>{
      'email': email.trim().toLowerCase(),
      'password': password,
      'role': role.toUpperCase(),
    };

    if ((bankId ?? '').trim().isNotEmpty) {
      payload['bank_id'] = bankId!.trim().toLowerCase();
    }
    if ((bankName ?? '').trim().isNotEmpty) {
      payload['bank_name'] = bankName!.trim();
    }

    final response = await _request(
      'POST',
      '/api/v1/register',
      body: payload,
      requiresAuth: false,
      triggerUnauthorized: false,
    );
    final body = _decodeJson(response.body);

    if (response.statusCode != 201 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<LoginResult> login({
    required String email,
    required String password,
    required String role,
    String deviceId = 'flutter_web_client',
  }) async {
    final normalizedRole = role.toUpperCase();
    final path = normalizedRole == 'BANK' ? '/api/v1/bank-login' : '/api/v1/login';

    final payload = <String, dynamic>{
      'email': email.trim().toLowerCase(),
      'password': password,
    };

    if (normalizedRole == 'BANK') {
      payload['role'] = 'BANK';
    } else {
      payload['role'] = normalizedRole;
      payload['device_id'] = deviceId;
    }

    final response = await _request(
      'POST',
      path,
      body: payload,
      requiresAuth: false,
      triggerUnauthorized: false,
    );
    final body = _decodeJson(response.body);

    if (response.statusCode == 200 && body is Map<String, dynamic>) {
      final token = body['token']?.toString();
      if (token == null || token.isEmpty) {
        throw ApiException(
          message: 'Token missing in login response',
          statusCode: response.statusCode,
          body: body,
        );
      }

      await persistAccessToken(token);
      final session = AuthSession.fromAccessToken(
        token,
        email: body['email']?.toString(),
        sessionId: body['session_id']?.toString(),
        risk: _asMap(body['risk']),
      );
      return LoginResult(session: session, raw: body);
    }

    throw _toException(response, body);
  }

  Future<void> logout() async {
    final token = _accessToken;
    if (token != null && token.isNotEmpty) {
      try {
        await _request(
          'POST',
          '/api/v1/logout',
          requiresAuth: true,
          triggerUnauthorized: false,
        );
      } catch (_) {
        // Ignore network/logout failure on client side and clear local token.
      }
    }

    await clearSession();
  }

  Future<Map<String, dynamic>> fetchUserDashboard() async {
    final response = await _request('GET', '/api/v1/user/dashboard');
    final body = _decodeJson(response.body);

    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<Map<String, dynamic>> fetchAdminDashboard() async {
    final response = await _request('GET', '/api/v1/admin/dashboard');
    final body = _decodeJson(response.body);

    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<List<String>> fetchGraphInsights() async {
    final response = await _request('GET', '/api/v1/admin/graph-insights');
    final body = _decodeJson(response.body);

    if (response.statusCode != 200 || body is! List) {
      throw _toException(response, body);
    }
    return body.map((item) => item.toString()).toList();
  }

  Future<Map<String, dynamic>> fetchGraphData() async {
    final response = await _request('GET', '/api/v1/admin/graph-data');
    final body = _decodeJson(response.body);

    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<List<Map<String, dynamic>>> fetchPendingApprovals({String? bankId}) async {
    var path = '/api/v1/admin/pending-users';
    if ((bankId ?? '').trim().isNotEmpty) {
      path = '$path?bank_id=${Uri.encodeQueryComponent(bankId!.trim().toLowerCase())}';
    }

    final response = await _request('GET', path);
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! List) {
      throw _toException(response, body);
    }
    return body.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> fetchSubscriptionStatus({String? bankId}) async {
    var path = '/api/v1/subscription/status';
    if ((bankId ?? '').trim().isNotEmpty) {
      path = '$path?bank_id=${Uri.encodeQueryComponent(bankId!.trim().toLowerCase())}';
    }
    final response = await _request('GET', path);
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<Map<String, dynamic>> submitSubscriptionRequest({
    required String planCode,
    required String paymentMethod,
    required String transactionNo,
  }) async {
    final response = await _request(
      'POST',
      '/api/v1/subscription/request',
      body: {
        'plan_code': planCode,
        'payment_method': paymentMethod,
        'transaction_no': transactionNo.trim(),
      },
    );
    final body = _decodeJson(response.body);
    if (response.statusCode != 201 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<List<Map<String, dynamic>>> fetchSubscriptionRequests({
    String status = 'PENDING',
  }) async {
    final path =
        '/api/v1/admin/subscription-requests?status=${Uri.encodeQueryComponent(status)}';
    final response = await _request('GET', path);
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! List) {
      throw _toException(response, body);
    }
    return body.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> decideSubscriptionRequest(
    String requestId, {
    required bool approve,
    String? reason,
  }) async {
    final response = await _request(
      'POST',
      '/api/v1/admin/subscription-requests/$requestId/decision',
      body: {
        'action': approve ? 'APPROVE' : 'REJECT',
        if (!approve) 'reason': (reason ?? '').trim(),
      },
    );
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<Map<String, dynamic>> approveUser(String userId) async {
    final response = await _request(
      'POST',
      '/api/v1/admin/approve-user',
      body: {'user_id': userId},
    );
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<Map<String, dynamic>> rejectUser(
    String userId, {
    required String reason,
  }) async {
    final response = await _request(
      'POST',
      '/api/v1/admin/reject-user',
      body: {'user_id': userId, 'reason': reason},
    );
    final body = _decodeJson(response.body);
    if (response.statusCode != 200 || body is! Map<String, dynamic>) {
      throw _toException(response, body);
    }
    return body;
  }

  Future<http.Response> _request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    String? tokenOverride,
    bool requiresAuth = true,
    bool triggerUnauthorized = true,
  }) async {
    final token = tokenOverride ?? _accessToken;
    final headers = <String, String>{'Content-Type': 'application/json'};

    if ((requiresAuth || tokenOverride != null) && token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    final uri = Uri.parse('$_baseUrl${path.startsWith('/') ? path : '/$path'}');

    late http.Response response;
    switch (method.toUpperCase()) {
      case 'GET':
        response = await http.get(uri, headers: headers);
        break;
      case 'POST':
        response = await http.post(uri, headers: headers, body: jsonEncode(body ?? {}));
        break;
      default:
        throw ApiException(message: 'Unsupported HTTP method: $method');
    }

    if (response.statusCode == 401 && triggerUnauthorized && requiresAuth) {
      await clearSession();
      onUnauthorized?.call();
    }

    return response;
  }

  static Map<String, dynamic> decodeJwtPayload(String token) {
    try {
      final segments = token.split('.');
      if (segments.length < 2) {
        return {};
      }
      final payload = base64Url.normalize(segments[1]);
      final decoded = utf8.decode(base64Url.decode(payload));
      final json = jsonDecode(decoded);
      if (json is Map<String, dynamic>) {
        return json;
      }
      return {};
    } catch (_) {
      return {};
    }
  }

  ApiException _toException(http.Response response, dynamic body) {
    final map = _asMap(body);
    final message = map['error']?.toString() ??
        map['message']?.toString() ??
        'Request failed with status ${response.statusCode}';
    return ApiException(message: message, statusCode: response.statusCode, body: map);
  }

  dynamic _decodeJson(String source) {
    if (source.trim().isEmpty) {
      return <String, dynamic>{};
    }
    try {
      return jsonDecode(source);
    } catch (_) {
      return <String, dynamic>{'error': source};
    }
  }

  static Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return value.map((key, val) => MapEntry(key.toString(), val));
    }
    return <String, dynamic>{};
  }
}
