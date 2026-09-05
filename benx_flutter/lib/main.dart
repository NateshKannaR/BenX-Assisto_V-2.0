import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const BenXApp());

class BenXApp extends StatelessWidget {
  const BenXApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BenX',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF020405),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF60FFB9),
          secondary: Color(0xFF61D8FF),
          surface: Color(0xFF03080A),
        ),
      ),
      home: const SplashScreen(),
    );
  }
}

// ── Splash / Setup Screen ─────────────────────────────────────
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _checkSetup();
  }

  Future<void> _checkSetup() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString('server_url') ?? '';
    await Future.delayed(const Duration(milliseconds: 1200));
    if (!mounted) return;
    if (url.isEmpty) {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const SetupScreen()));
    } else {
      Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => ChatScreen(serverUrl: url)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('BenX', style: TextStyle(
              fontSize: 52, fontWeight: FontWeight.bold,
              color: const Color(0xFF60FFB9),
              letterSpacing: 6,
            )),
            const SizedBox(height: 12),
            Text('AI Assistant', style: TextStyle(
              color: Colors.white54, fontSize: 14, letterSpacing: 3,
            )),
            const SizedBox(height: 40),
            const CircularProgressIndicator(color: Color(0xFF60FFB9), strokeWidth: 2),
          ],
        ),
      ),
    );
  }
}

// ── Setup Screen ──────────────────────────────────────────────
class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});
  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _ctrl = TextEditingController(text: 'ws://192.168.1.100:8000/ws');
  bool _testing = false;
  String _status = '';

  Future<void> _test() async {
    setState(() { _testing = true; _status = 'Testing...'; });
    try {
      final url = _ctrl.text.trim().replaceFirst('ws', 'http').replaceFirst('/ws', '/api/health');
      final res = await http.get(Uri.parse(url)).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        setState(() { _status = '✅ Connected!'; });
        await Future.delayed(const Duration(milliseconds: 800));
        _save();
      } else {
        setState(() { _status = '❌ Server error ${res.statusCode}'; });
      }
    } catch (e) {
      setState(() { _status = '❌ Cannot reach server'; });
    }
    setState(() { _testing = false; });
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', _ctrl.text.trim());
    if (!mounted) return;
    Navigator.pushReplacement(context, MaterialPageRoute(
      builder: (_) => ChatScreen(serverUrl: _ctrl.text.trim()),
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Setup BenX', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF60FFB9))),
            const SizedBox(height: 8),
            const Text('Enter your BenX server WebSocket URL', style: TextStyle(color: Colors.white54)),
            const SizedBox(height: 32),
            TextField(
              controller: _ctrl,
              style: const TextStyle(color: Colors.white, fontFamily: 'monospace'),
              decoration: InputDecoration(
                labelText: 'WebSocket URL',
                labelStyle: const TextStyle(color: Color(0xFF60FFB9)),
                hintText: 'ws://YOUR_IP:8000/ws',
                hintStyle: const TextStyle(color: Colors.white24),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFF60FFB9), width: 1),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFF60FFB9), width: 2),
                ),
              ),
            ),
            const SizedBox(height: 12),
            if (_status.isNotEmpty)
              Text(_status, style: TextStyle(
                color: _status.startsWith('✅') ? const Color(0xFF60FFB9) : Colors.redAccent,
              )),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _testing ? null : _test,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF60FFB9),
                  foregroundColor: Colors.black,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: _testing
                    ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                    : const Text('Connect', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
              ),
            ),
            const SizedBox(height: 12),
            Center(
              child: TextButton(
                onPressed: _save,
                child: const Text('Skip test & connect', style: TextStyle(color: Colors.white38)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Chat Message Model ────────────────────────────────────────
class ChatMessage {
  final String sender;
  final String text;
  final DateTime time;
  final bool isStreaming;

  ChatMessage({required this.sender, required this.text, required this.time, this.isStreaming = false});
  ChatMessage copyWith({String? text, bool? isStreaming}) =>
      ChatMessage(sender: sender, text: text ?? this.text, time: time, isStreaming: isStreaming ?? this.isStreaming);
}

// ── Main Chat Screen ──────────────────────────────────────────
class ChatScreen extends StatefulWidget {
  final String serverUrl;
  const ChatScreen({super.key, required this.serverUrl});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with TickerProviderStateMixin {
  WebSocketChannel? _channel;
  final _messages = <ChatMessage>[];
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _connected = false;
  bool _streaming = false;
  Map<String, dynamic> _metrics = {};
  Timer? _metricsTimer;
  Timer? _reconnectTimer;
  String _model = '';
  bool _agentMode = false;

  @override
  void initState() {
    super.initState();
    _connect();
    _startMetrics();
    _addMessage('BenX', 'Hello! I\'m BenX. Connected to your Linux system. What can I do for you?');
  }

  void _connect() {
    try {
      _channel = WebSocketChannel.connect(Uri.parse(widget.serverUrl));
      _channel!.stream.listen(
        (data) {
          try {
            final msg = jsonDecode(data as String);
            _handleMessage(msg);
          } catch (_) {}
        },
        onDone: () {
          setState(() => _connected = false);
          _scheduleReconnect();
        },
        onError: (_) {
          setState(() => _connected = false);
          _scheduleReconnect();
        },
      );
      setState(() => _connected = true);
    } catch (_) {
      setState(() => _connected = false);
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 4), _connect);
  }

  void _handleMessage(Map<String, dynamic> msg) {
    final type = msg['type'] as String? ?? '';
    switch (type) {
      case 'status':
        break;
      case 'chunk':
        final chunk = msg['text'] as String? ?? '';
        setState(() {
          if (_messages.isNotEmpty && _messages.last.sender == 'BenX' && _messages.last.isStreaming) {
            _messages[_messages.length - 1] = _messages.last.copyWith(
              text: _messages.last.text + chunk,
            );
          } else {
            _addMessage('BenX', chunk, isStreaming: true);
          }
        });
        _scrollToBottom();
        break;
      case 'command_result':
        setState(() {
          if (_messages.isNotEmpty && _messages.last.isStreaming) {
            _messages[_messages.length - 1] = _messages.last.copyWith(
              text: msg['text'] ?? '', isStreaming: false,
            );
          } else {
            _addMessage('BenX', msg['text'] ?? '');
          }
        });
        break;
      case 'done':
        setState(() {
          if (_messages.isNotEmpty && _messages.last.isStreaming) {
            _messages[_messages.length - 1] = _messages.last.copyWith(isStreaming: false);
          }
          _streaming = false;
        });
        break;
      case 'error':
        setState(() {
          _streaming = false;
          _addMessage('BenX', '❌ ${msg['text']}');
        });
        break;
      case 'metrics':
        setState(() => _metrics = Map<String, dynamic>.from(msg['data'] ?? {}));
        break;
    }
  }

  void _addMessage(String sender, String text, {bool isStreaming = false}) {
    _messages.add(ChatMessage(sender: sender, text: text, time: DateTime.now(), isStreaming: isStreaming));
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _send() {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty || _streaming || !_connected) return;
    setState(() {
      _addMessage('You', text);
      _streaming = true;
      _inputCtrl.clear();
    });
    _channel?.sink.add(jsonEncode({
      'type': 'chat',
      'message': text,
      'model': _model.isEmpty ? null : _model,
      'agent_mode': _agentMode,
      'device_id': 'mobile',
    }));
  }

  Future<void> _startMetrics() async {
    _metricsTimer = Timer.periodic(const Duration(seconds: 4), (_) async {
      if (_connected) {
        _channel?.sink.add(jsonEncode({'type': 'metrics'}));
      }
    });
  }

  @override
  void dispose() {
    _channel?.sink.close();
    _metricsTimer?.cancel();
    _reconnectTimer?.cancel();
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: _buildAppBar(),
      body: Column(
        children: [
          if (_metrics.isNotEmpty) _buildMetricsBar(),
          Expanded(child: _buildChatList()),
          _buildQuickChips(),
          _buildInputBar(),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: const Color(0xFF03080A),
      elevation: 0,
      title: Row(
        children: [
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: _connected ? const Color(0xFF60FFB9) : Colors.redAccent,
              boxShadow: _connected ? [BoxShadow(color: const Color(0xFF60FFB9).withOpacity(0.6), blurRadius: 6)] : [],
            ),
          ),
          const SizedBox(width: 10),
          const Text('BenX', style: TextStyle(
            color: Color(0xFF60FFB9), fontWeight: FontWeight.bold,
            fontSize: 20, letterSpacing: 2,
          )),
          const SizedBox(width: 8),
          Text(_connected ? 'Operational' : 'Reconnecting…',
            style: TextStyle(fontSize: 11, color: _connected ? Colors.white38 : Colors.redAccent),
          ),
        ],
      ),
      actions: [
        IconButton(
          icon: Icon(_agentMode ? Icons.auto_awesome : Icons.auto_awesome_outlined,
            color: _agentMode ? const Color(0xFF60FFB9) : Colors.white38),
          tooltip: 'Agent mode',
          onPressed: () => setState(() => _agentMode = !_agentMode),
        ),
        IconButton(
          icon: const Icon(Icons.settings_outlined, color: Colors.white38),
          onPressed: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => SettingsScreen(serverUrl: widget.serverUrl),
          )),
        ),
      ],
    );
  }

  Widget _buildMetricsBar() {
    final cpu = _metrics['cpu'] ?? 0;
    final ram = _metrics['ram'] ?? 0;
    final battery = _metrics['battery'];
    final charging = _metrics['charging'] ?? false;
    return Container(
      color: const Color(0xFF03080A),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          _metricChip('CPU', '${cpu}%', const Color(0xFF60FFB9)),
          const SizedBox(width: 12),
          _metricChip('RAM', '${ram}%', const Color(0xFF61D8FF)),
          if (battery != null) ...[
            const SizedBox(width: 12),
            _metricChip('BAT', '${battery}%${charging ? '⚡' : ''}', const Color(0xFFFFC45E)),
          ],
        ],
      ),
    );
  }

  Widget _metricChip(String label, String value, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: TextStyle(color: color.withOpacity(0.6), fontSize: 10, letterSpacing: 1)),
        const SizedBox(width: 4),
        Text(value, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildChatList() {
    return ListView.builder(
      controller: _scrollCtrl,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      itemCount: _messages.length,
      itemBuilder: (_, i) => _buildBubble(_messages[i]),
    );
  }

  Widget _buildBubble(ChatMessage msg) {
    final isUser = msg.sender == 'You';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.82),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF06120E) : const Color(0xFF03080A),
          border: Border.all(
            color: isUser
                ? const Color(0xFF60FFB9).withOpacity(0.2)
                : const Color(0xFF52FFAD).withOpacity(0.1),
          ),
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(msg.sender,
                    style: TextStyle(
                      color: isUser ? const Color(0xFF61D8FF) : const Color(0xFF60FFB9),
                      fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${msg.time.hour.toString().padLeft(2,'0')}:${msg.time.minute.toString().padLeft(2,'0')}',
                    style: const TextStyle(color: Colors.white24, fontSize: 10),
                  ),
                  if (!isUser)
                    IconButton(
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      iconSize: 14,
                      icon: const Icon(Icons.copy_outlined, color: Colors.white24),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: msg.text));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Copied'), duration: Duration(seconds: 1)),
                        );
                      },
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                msg.text + (msg.isStreaming ? '▋' : ''),
                style: const TextStyle(color: Color(0xFFE4F8F0), fontSize: 14, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuickChips() {
    final chips = ['system info', 'battery status', 'what\'s running', 'take screenshot'];
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) => ActionChip(
          label: Text(chips[i], style: const TextStyle(fontSize: 12, color: Color(0xFF60FFB9))),
          backgroundColor: const Color(0xFF03080A),
          side: const BorderSide(color: Color(0xFF60FFB9), width: 0.5),
          onPressed: () {
            _inputCtrl.text = chips[i];
            _send();
          },
        ),
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
      color: const Color(0xFF03080A),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _inputCtrl,
              style: const TextStyle(color: Colors.white),
              maxLines: null,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _send(),
              decoration: InputDecoration(
                hintText: 'Message BenX…',
                hintStyle: const TextStyle(color: Colors.white24),
                filled: true,
                fillColor: const Color(0xFF020405),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: const BorderSide(color: Color(0xFF52FFAD), width: 0.5),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: BorderSide(color: const Color(0xFF52FFAD).withOpacity(0.3), width: 0.5),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(16),
                  borderSide: const BorderSide(color: Color(0xFF60FFB9), width: 1.5),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: _send,
            child: Container(
              width: 46, height: 46,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF3DD6A0), Color(0xFF60FFB9)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [BoxShadow(color: const Color(0xFF60FFB9).withOpacity(0.3), blurRadius: 8)],
              ),
              child: const Icon(Icons.send_rounded, color: Color(0xFF02100B), size: 20),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Settings Screen ───────────────────────────────────────────
class SettingsScreen extends StatelessWidget {
  final String serverUrl;
  const SettingsScreen({super.key, required this.serverUrl});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings', style: TextStyle(color: Color(0xFF60FFB9))),
        backgroundColor: const Color(0xFF03080A),
        iconTheme: const IconThemeData(color: Color(0xFF60FFB9)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          _tile('Server URL', serverUrl, Icons.dns_outlined),
          _tile('Version', '2.0.0', Icons.info_outline),
          const SizedBox(height: 24),
          ListTile(
            leading: const Icon(Icons.edit_outlined, color: Color(0xFF60FFB9)),
            title: const Text('Change Server', style: TextStyle(color: Colors.white)),
            onTap: () {
              Navigator.pushAndRemoveUntil(
                context,
                MaterialPageRoute(builder: (_) => const SetupScreen()),
                (_) => false,
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _tile(String label, String value, IconData icon) {
    return ListTile(
      leading: Icon(icon, color: const Color(0xFF60FFB9)),
      title: Text(label, style: const TextStyle(color: Colors.white54, fontSize: 12)),
      subtitle: Text(value, style: const TextStyle(color: Colors.white, fontFamily: 'monospace')),
    );
  }
}
