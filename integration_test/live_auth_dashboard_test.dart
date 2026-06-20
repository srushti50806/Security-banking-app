import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'package:security_banking_app/main.dart' as app;

Future<void> _pumpUntilFound(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 20),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 250));
    if (finder.evaluate().isNotEmpty) {
      return;
    }
  }
  throw TestFailure('Timed out waiting for $finder.');
}

Future<void> _selectDropdownValue(
  WidgetTester tester,
  Key key,
  String value,
) async {
  await _pumpUntilFound(tester, find.byKey(key));
  await tester.tap(find.byKey(key));
  await tester.pumpAndSettle();
  await tester.tap(find.text(value).last);
  await tester.pumpAndSettle();
}

Future<void> _openRegisterTab(WidgetTester tester) async {
  await _pumpUntilFound(tester, find.byKey(const Key('register-tab')));
  await tester.tap(find.byKey(const Key('register-tab')));
  await tester.pumpAndSettle();
  await _pumpUntilFound(tester, find.byKey(const Key('register-role')));
}

Future<void> _login(
  WidgetTester tester, {
  required String role,
  required String email,
  required String password,
}) async {
  await _selectDropdownValue(tester, const Key('login-role'), role);
  await tester.enterText(find.byKey(const Key('login-email')), email);
  await tester.enterText(find.byKey(const Key('login-password')), password);
  await tester.tap(find.byKey(const Key('login-submit')));
  await tester.pump();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('registers and logs in bank, user, and admin in Chrome', (
    tester,
  ) async {
    final runId = DateTime.now().millisecondsSinceEpoch;
    final bankName = 'Chrome Demo Bank $runId';
    final bankEmail = 'bank_$runId@example.com';
    final adminEmail = 'admin_$runId@example.com';
    final userEmail = 'user_$runId@example.com';
    const password = 'Pass1234';

    await app.main();
    await tester.pump(const Duration(seconds: 2));
    await _pumpUntilFound(tester, find.text('GraphShield Security Access'));

    await _openRegisterTab(tester);

    await _selectDropdownValue(tester, const Key('register-role'), 'Bank');
    await tester.enterText(find.byKey(const Key('register-email')), bankEmail);
    await tester.enterText(
      find.byKey(const Key('register-password')),
      password,
    );
    await tester.enterText(
      find.byKey(const Key('register-bank-name')),
      bankName,
    );
    await tester.tap(find.byKey(const Key('register-submit')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await _openRegisterTab(tester);
    await _selectDropdownValue(tester, const Key('register-role'), 'Admin');
    await tester.enterText(find.byKey(const Key('register-email')), adminEmail);
    await tester.enterText(
      find.byKey(const Key('register-password')),
      password,
    );
    await _pumpUntilFound(tester, find.byKey(const Key('register-bank')));
    await _selectDropdownValue(tester, const Key('register-bank'), bankName);
    await tester.tap(find.byKey(const Key('register-submit')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await _openRegisterTab(tester);
    await _selectDropdownValue(tester, const Key('register-role'), 'User');
    await tester.enterText(find.byKey(const Key('register-email')), userEmail);
    await tester.enterText(
      find.byKey(const Key('register-password')),
      password,
    );
    await _selectDropdownValue(tester, const Key('register-bank'), bankName);
    await tester.tap(find.byKey(const Key('register-submit')));
    await tester.pump();
    await tester.pump(const Duration(seconds: 2));

    await _login(
      tester,
      role: 'Bank',
      email: bankEmail,
      password: password,
    );
    await _pumpUntilFound(tester, find.byKey(const Key('bank-dashboard-root')));
    await _pumpUntilFound(tester, find.byKey(const Key('bank-subscribe-button')));
    await tester.scrollUntilVisible(
      find.text('Approve'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Approve').first);
    await tester.pump();
    await _pumpUntilFound(tester, find.text('User approved successfully'));

    await tester.tap(find.byKey(const Key('dashboard-logout')));
    await tester.pumpAndSettle();
    await _pumpUntilFound(tester, find.text('GraphShield Security Access'));

    await _login(
      tester,
      role: 'User',
      email: userEmail,
      password: password,
    );
    await _pumpUntilFound(tester, find.byKey(const Key('user-dashboard-root')));
    expect(find.text('GraphShield User Security Panel'), findsOneWidget);

    await tester.tap(find.byKey(const Key('dashboard-logout')));
    await tester.pumpAndSettle();
    await _pumpUntilFound(tester, find.text('GraphShield Security Access'));

    await _login(
      tester,
      role: 'Admin',
      email: adminEmail,
      password: password,
    );
    await _pumpUntilFound(tester, find.byKey(const Key('admin-dashboard-root')));
    expect(find.byKey(const Key('bank-subscribe-button')), findsNothing);
    expect(find.text('GraphShield Security Operations'), findsOneWidget);
  });
}
