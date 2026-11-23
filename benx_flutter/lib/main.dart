import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

void main() => runApp(const BenXApp());

class BenXApp extends StatelessWidget {
  const BenXApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BenX',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF60FFB9),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: const CompanionScreen(),
    );
  }
}

class CompanionScreen extends StatefulWidget {
  const CompanionScreen({super.key});

  @override
  State<CompanionScreen> createState() => _CompanionScreenState();
}

class _CompanionScreenState extends State<CompanionScreen> {
  final _endpoint = TextEditingController();
  final _token = TextEditingController();
  final _layout = TextEditingController(text: 'work');
  WebSocketChannel? _channel;
  Timer? _pairingTimeout;
  bool _paired = false;
  bool _busy = false;
  String _status = 'Disconnected';
  String _result = '';

  Future<void> _connect() async {
    final uri = Uri.tryParse(_endpoint.text.trim());
    final token = _token.text.trim();
    if (uri == null ||
        uri.scheme != 'wss' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        token.length < 32) {
      setState(() => _status = 'Enter a wss:// URL and a valid pairing token.');
      return;
    }
    setState(() => _status = 'Pairing…');

    try {
      final channel = WebSocketChannel.connect(uri);
      _channel = channel;
      _pairingTimeout = Timer(
        const Duration(seconds: 10),
        () => _disconnected(channel, 'Pairing timed out.'),
      );
      channel.stream.listen(
        (data) => _handleMessage(channel, data),
        onDone: () => _disconnected(channel, 'Connection closed.'),
        onError: (Object error) => _disconnected(channel, 'Connection failed.'),
      );
      await channel.ready;
      if (mounted && identical(_channel, channel)) {
        channel.sink.add(jsonEncode({'type': 'pair', 'token': token}));
      }
    } catch (_) {
      if (!mounted) return;
      final channel = _channel;
      if (channel != null) {
        _disconnected(channel, 'Could not connect to BenX.');
      } else if (_status == 'Pairing…') {
        setState(() => _status = 'Could not connect to BenX.');
      }
    }
  }

  void _disconnected(WebSocketChannel channel, String status) {
    if (!mounted || !identical(_channel, channel)) return;
    _pairingTimeout?.cancel();
    setState(() {
      _channel = null;
      _status = status;
      _paired = false;
      _busy = false;
    });
    unawaited(channel.sink.close().catchError((Object _) {}));
  }

  Future<void> _handleMessage(WebSocketChannel channel, dynamic data) async {
    if (!mounted || !identical(_channel, channel)) return;
    final Object? decoded;
    try {
      decoded = jsonDecode(data as String);
    } on FormatException {
      return;
    } on TypeError {
      return;
    }
    if (decoded is! Map<String, dynamic>) return;
    final message = decoded;
    switch (message['type']) {
      case 'paired':
        _pairingTimeout?.cancel();
        _token.clear();
        setState(() {
          _paired = true;
          _status = 'Connected';
          _result = '';
        });
        break;
      case 'result':
        setState(() {
          _result = message['text']?.toString() ?? '';
          _busy = false;
        });
        break;
      case 'confirmation':
        final approved = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Confirm layout restore'),
            content: Text(message['text']?.toString() ?? ''),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: const Text('Restore'),
              ),
            ],
          ),
        );
        if (mounted && identical(_channel, channel)) {
          channel.sink.add(jsonEncode({
            'type': 'confirm',
            'id': message['id'],
            'approved': approved == true,
          }));
        }
        break;
    }
  }

  void _send(String type, {String? name}) {
    if (!_paired || _busy) return;
    setState(() => _busy = true);
    _channel?.sink
        .add(jsonEncode({'type': type, if (name != null) 'name': name}));
  }

  @override
  void dispose() {
    _pairingTimeout?.cancel();
    _channel?.sink.close().catchError((Object _) {});
    _endpoint.dispose();
    _token.dispose();
    _layout.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final channel = _channel;
    final canSend = _paired && !_busy;
    return Scaffold(
      appBar: AppBar(title: const Text('BenX Companion')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(_status, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),
          if (channel == null) ...[
            TextField(
              controller: _endpoint,
              decoration: const InputDecoration(
                labelText: 'WebSocket URL',
                hintText: 'wss://your-desktop.example/ws',
              ),
              keyboardType: TextInputType.url,
              autocorrect: false,
            ),
            TextField(
              controller: _token,
              decoration: const InputDecoration(labelText: 'Pairing token'),
              obscureText: true,
              autocorrect: false,
            ),
            const SizedBox(height: 16),
            FilledButton(
                onPressed: _connect, child: const Text('Pair desktop')),
          ] else ...[
            OutlinedButton(
              onPressed: () => _disconnected(channel, 'Disconnected'),
              child: const Text('Disconnect'),
            ),
            if (_paired) ...[
              FilledButton.tonal(
                onPressed: canSend ? () => _send('battery') : null,
                child: const Text('Battery status'),
              ),
              FilledButton.tonal(
                onPressed: canSend ? () => _send('list_layouts') : null,
                child: const Text('Saved layouts'),
              ),
              TextField(
                controller: _layout,
                decoration: const InputDecoration(labelText: 'Layout name'),
              ),
              FilledButton(
                onPressed: canSend
                    ? () => _send('restore_layout', name: _layout.text.trim())
                    : null,
                child: const Text('Restore layout'),
              ),
              if (_busy) const LinearProgressIndicator(),
              if (_result.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: SelectableText(_result),
                ),
            ],
          ],
        ],
      ),
    );
  }
}
