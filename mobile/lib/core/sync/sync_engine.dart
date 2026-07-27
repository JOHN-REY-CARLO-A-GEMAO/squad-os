import 'dart:async';
import 'dart:convert';
import 'package:drift/drift.dart';
import '../database/database.dart';
import '../api/api_client.dart';
import '../repository/squad_repository.dart';

class SyncEngine {
  final SquadRepository repository;
  final List<Map<String, dynamic>> _outboundQueue = [];
  bool _isSyncing = false;

  SyncEngine({required this.repository});

  List<Map<String, dynamic>> get outboundQueue => _outboundQueue;

  void queueAction(String action, Map<String, dynamic> payload) {
    _outboundQueue.add({
      'action': action,
      'payload': payload,
      'timestamp': DateTime.now().toIso8601String(),
    });
    triggerSync();
  }

  Future<void> triggerSync() async {
    if (_isSyncing) return;
    _isSyncing = true;

    try {
      while (_outboundQueue.isNotEmpty) {
        final item = _outboundQueue.first;
        final action = item['action'];
        final payload = item['payload'] as Map<String, dynamic>;

        bool success = false;
        if (action == 'INBOX.APPROVE') {
          final res = await repository.apiClient.dio.post('/api/v1/pair/request', data: {
            'pairing_url': 'squados://pair',
            'ticket_version': 1,
            'nonce': 'approved_offline',
            'device_id': 'companion',
          });
          success = res.statusCode == 200;
        } else if (action == 'UPDATE_CONTEXT') {
          final convId = payload['conversation_id'] as int;
          final memories = Map<String, String>.from(payload['context_memory']);
          await repository.updateMemoryContext(convId, memories);
          success = true;
        }

        if (success) {
          _outboundQueue.removeAt(0);
        } else {
          break;
        }
      }

      await performEventReplay(1);
    } catch (_) {}

    _isSyncing = false;
  }

  Future<void> performEventReplay(int conversationId) async {
    try {
      final query = repository.database.select(repository.database.conversationEvents)
        ..orderBy([(t) => OrderingTerm.desc(t.sequenceId)])
        ..limit(1);
      final latestLocal = await query.getSingleOrNull();
      final int sinceSeq = latestLocal?.sequenceId ?? 0;

      await repository.fetchUnifiedTimeline(conversationId, limit: 100);
    } catch (_) {}
  }
}
