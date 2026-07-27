import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class WebSocketClient {
  final String url;
  final int conversationId;

  WebSocketChannel? _channel;
  final StreamController<Map<String, dynamic>> _messageController = StreamController<Map<String, dynamic>>.broadcast();
  bool _isDisposed = false;
  int _reconnectDelaySeconds = 1;
  Timer? _heartbeatTimer;

  WebSocketClient({
    String? baseUrl,
    this.conversationId = 1,
  }) : url = '${baseUrl ?? 'ws://127.0.0.1:8000'}/api/v1/streams?conversation_id=$conversationId';

  Stream<Map<String, dynamic>> get stream => _messageController.stream;

  void connect() {
    if (_isDisposed) return;

    try {
      _channel = WebSocketChannel.connect(Uri.parse(url));
      _reconnectDelaySeconds = 1;

      _channel!.stream.listen(
        (data) {
          try {
            final Map<String, dynamic> parsed = json.decode(data);
            _messageController.add(parsed);
          } catch (_) {}
        },
        onError: (err) {
          _handleDisconnect();
        },
        onDone: () {
          _handleDisconnect();
        },
      );

      _startHeartbeat();
    } catch (_) {
      _handleDisconnect();
    }
  }

  void _startHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer.periodic(const Duration(seconds: 30), (timer) {
      if (_channel != null) {
        try {
          _channel!.sink.add(json.encode({'type': 'PING'}));
        } catch (_) {}
      }
    });
  }

  void _handleDisconnect() {
    _heartbeatTimer?.cancel();
    if (_isDisposed) return;

    Timer(Duration(seconds: _reconnectDelaySeconds), () {
      if (_reconnectDelaySeconds < 60) {
        _reconnectDelaySeconds *= 2;
      }
      connect();
    });
  }

  void sendCommand(String action, Map<String, dynamic> payload) {
    if (_channel != null) {
      final requestId = 'req_${DateTime.now().millisecondsSinceEpoch}';
      _channel!.sink.add(json.encode({
        'request_id': requestId,
        'action': action,
        'payload': payload,
      }));
    }
  }

  void dispose() {
    _isDisposed = true;
    _heartbeatTimer?.cancel();
    _channel?.sink.close();
    _messageController.close();
  }
}
