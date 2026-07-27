import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:drift/drift.dart';
import '../../../core/api/api_client.dart';
import '../../../core/database/database.dart';
import '../../../core/repository/squad_repository.dart';
import '../../../core/websocket/websocket_client.dart';
import '../../../core/sync/sync_engine.dart';

class ChatState {
  final List<ConversationEvent> events;
  final Map<String, String> contextMemory;
  final MissionSnapshot? activeSnapshot;
  final bool isLoading;

  ChatState({
    required this.events,
    required this.contextMemory,
    this.activeSnapshot,
    this.isLoading = false,
  });

  ChatState copyWith({
    List<ConversationEvent>? events,
    Map<String, String>? contextMemory,
    MissionSnapshot? activeSnapshot,
    bool? isLoading,
  }) {
    return ChatState(
      events: events ?? this.events,
      contextMemory: contextMemory ?? this.contextMemory,
      activeSnapshot: activeSnapshot ?? this.activeSnapshot,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class ChatController extends StateNotifier<ChatState> {
  final SquadRepository repository;
  final WebSocketClient webSocketClient;
  final SyncEngine syncEngine;
  final int conversationId;

  ChatController({
    required this.repository,
    required this.webSocketClient,
    required this.syncEngine,
    this.conversationId = 1,
  }) : super(ChatState(events: [], contextMemory: {}, isLoading: true)) {
    _init();
  }

  Future<void> _init() async {
    await loadTimeline();
    await loadContext();

    webSocketClient.connect();
    webSocketClient.stream.listen((event) {
      _handleIncomingEvent(event);
    });
  }

  Future<void> loadTimeline() async {
    state = state.copyWith(isLoading: true);
    final events = await repository.fetchUnifiedTimeline(conversationId);
    state = state.copyWith(events: events, isLoading: false);
  }

  Future<void> loadContext() async {
    final memory = await repository.getLocalMemoryContext(conversationId);
    state = state.copyWith(contextMemory: memory);
  }

  Future<void> updateContextField(String key, String value) async {
    final updatedMemories = Map<String, String>.from(state.contextMemory)..[key] = value;
    state = state.copyWith(contextMemory: updatedMemories);

    syncEngine.queueAction('UPDATE_CONTEXT', {
      'conversation_id': conversationId,
      'context_memory': {key: value},
    });
  }

  Future<void> sendMessage(String text) async {
    final userEvent = ConversationEvent(
      id: DateTime.now().millisecondsSinceEpoch,
      conversationId: conversationId,
      sequenceId: state.events.length + 1,
      eventNamespace: 'CHAT',
      eventType: 'MESSAGE',
      payloadJson: json.encode({'role': 'user', 'content': text}),
      createdAt: DateTime.now(),
      payloadSchemaVersion: 1,
    );

    state = state.copyWith(events: [...state.events, userEvent]);

    try {
      await repository.apiClient.dio.post('/missions/dispatch', data: {
        'goal': text,
      });
      await Future.delayed(const Duration(seconds: 1));
      await loadTimeline();
    } catch (_) {
      syncEngine.queueAction('SEND_MESSAGE', {'text': text});
    }
  }

  void _handleIncomingEvent(Map<String, dynamic> event) async {
    if (event['event_type'] == 'SNAPSHOT_UPDATE') {
      final payload = event['payload'];
      final snapshot = MissionSnapshot(
        missionId: payload['mission_id'],
        status: payload['status'],
        progress: (payload['progress'] as num?)?.toDouble() ?? 0.0,
        latestThought: payload['latest_thought'],
        nextAction: payload['next_action'],
        eta: payload['eta'] ?? 0,
        confidence: payload['confidence'] ?? 'HIGH',
        tokenUsage: payload['token_usage'] ?? 0,
        estimatedCost: (payload['estimated_cost'] as num?)?.toDouble() ?? 0.0,
        lastUpdated: DateTime.now(),
      );

      await repository.saveSnapshot(snapshot);
      state = state.copyWith(activeSnapshot: snapshot);
    } else if (event['type'] == 'EVENT') {
      final data = event['data'];
      final ev = ConversationEvent(
        id: data['id'],
        parentEventId: data['parent_event_id'],
        conversationId: conversationId,
        sequenceId: data['sequence_id'],
        eventNamespace: data['event_namespace'],
        eventType: data['event_type'],
        payloadJson: json.encode(data['payload']),
        missionId: data['mission_id'],
        payloadSchemaVersion: data['payload_schema_version'] ?? 1,
        createdAt: DateTime.tryParse(data['created_at'] ?? '') ?? DateTime.now(),
      );

      await repository.database.into(repository.database.conversationEvents).insertOnConflictUpdate(
        ConversationEventsCompanion.insert(
          id: Value(ev.id),
          parentEventId: Value(ev.parentEventId),
          conversationId: ev.conversationId,
          sequenceId: ev.sequenceId,
          eventNamespace: ev.eventNamespace,
          eventType: ev.eventType,
          payloadJson: ev.payloadJson,
          missionId: Value(ev.missionId),
          payloadSchemaVersion: Value(ev.payloadSchemaVersion),
          createdAt: Value(ev.createdAt),
        ),
      );

      state = state.copyWith(events: [...state.events, ev]);
    }
  }

  @override
  void dispose() {
    webSocketClient.dispose();
    super.dispose();
  }
}

final apiProvider = Provider<ApiClient>((ref) => ApiClient());
final dbProvider = Provider<AppDatabase>((ref) => AppDatabase());
final wsProvider = Provider<WebSocketClient>((ref) => WebSocketClient());
final repoProvider = Provider<SquadRepository>((ref) {
  final api = ref.watch(apiProvider);
  final db = ref.watch(dbProvider);
  return SquadRepository(apiClient: api, database: db);
});
final syncProvider = Provider<SyncEngine>((ref) {
  final repo = ref.watch(repoProvider);
  return SyncEngine(repository: repo);
});

final chatProvider = StateNotifierProvider<ChatController, ChatState>((ref) {
  final repo = ref.watch(repoProvider);
  final ws = ref.watch(wsProvider);
  final sync = ref.watch(syncProvider);
  return ChatController(repository: repo, webSocketClient: ws, syncEngine: sync);
});
