import 'dart:convert';
import 'package:drift/drift.dart';
import '../api/api_client.dart';
import '../database/database.dart';

class SquadRepository {
  final ApiClient apiClient;
  final AppDatabase database;

  SquadRepository({required this.apiClient, required this.database});

  // --- CONVERSATIONS ---

  Future<List<Conversation>> fetchConversations(int workspaceId) async {
    try {
      final response = await apiClient.dio.get('/api/v1/workspaces/$workspaceId/conversations');
      final list = response.data['conversations'] as List;

      final conversations = <Conversation>[];
      for (var item in list) {
        final conv = Conversation(
          id: item['id'],
          workspaceId: item['workspace_id'],
          title: item['title'],
          summary: item['summary'],
          goal: item['goal'],
          systemPrompt: item['system_prompt'],
          activeModel: item['active_model'] ?? 'claude-3-5-sonnet',
          temperature: (item['temperature'] as num?)?.toDouble() ?? 0.2,
          createdAt: DateTime.tryParse(item['created_at'] ?? '') ?? DateTime.now(),
          updatedAt: DateTime.tryParse(item['updated_at'] ?? '') ?? DateTime.now(),
        );
        conversations.add(conv);

        await database.into(database.conversations).insertOnConflictUpdate(
          ConversationsCompanion.insert(
            id: Value(conv.id),
            workspaceId: conv.workspaceId,
            title: conv.title,
            summary: Value(conv.summary),
            goal: Value(conv.goal),
            systemPrompt: Value(conv.systemPrompt),
            activeModel: Value(conv.activeModel),
            temperature: Value(conv.temperature),
            createdAt: Value(conv.createdAt),
            updatedAt: Value(conv.updatedAt),
          ),
        );
      }
      return conversations;
    } catch (_) {
      return await (database.select(database.conversations)).get();
    }
  }

  // --- UNIFIED TIMELINE (EVENTS) ---

  Future<List<ConversationEvent>> fetchUnifiedTimeline(int conversationId, {int limit = 50, bool parentOnly = false}) async {
    try {
      final response = await apiClient.dio.get('/api/v1/conversations/$conversationId', queryParameters: {
        'limit': limit,
        'parent_only': parentOnly,
      });
      final eventsList = response.data['events'] as List;

      final events = <ConversationEvent>[];
      for (var item in eventsList) {
        final ev = ConversationEvent(
          id: item['id'],
          parentEventId: item['parent_event_id'],
          conversationId: conversationId,
          sequenceId: item['sequence_id'],
          eventNamespace: item['event_namespace'],
          eventType: item['event_type'],
          payloadJson: json.encode(item['payload']),
          missionId: item['mission_id'],
          payloadSchemaVersion: item['payload_schema_version'] ?? 1,
          createdAt: DateTime.tryParse(item['created_at'] ?? '') ?? DateTime.now(),
        );
        events.add(ev);

        await database.into(database.conversationEvents).insertOnConflictUpdate(
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
      }
      return events;
    } catch (_) {
      return await (database.select(database.conversationEvents)
            ..where((t) => t.conversationId.equals(conversationId))
            ..orderBy([(t) => OrderingTerm.asc(t.sequenceId)]))
          .get();
    }
  }

  // --- UPDATE CONTEXT MEMORY ---

  Future<Map<String, String>> updateMemoryContext(int conversationId, Map<String, String> memories) async {
    try {
      await apiClient.dio.put('/api/v1/conversations/$conversationId/context', data: {
        'context_memory': memories,
      });
    } catch (_) {}

    for (var entry in memories.entries) {
      await database.into(database.conversationMemories).insertOnConflictUpdate(
        ConversationMemoriesCompanion.insert(
          conversationId: conversationId,
          memoryKey: entry.key,
          memoryValue: Value(entry.value),
          updatedAt: Value(DateTime.now()),
        ),
      );
    }
    return memories;
  }

  Future<Map<String, String>> getLocalMemoryContext(int conversationId) async {
    final rows = await (database.select(database.conversationMemories)
          ..where((t) => t.conversationId.equals(conversationId)))
        .get();
    return {for (var r in rows) r.memoryKey: r.memoryValue ?? ''};
  }

  // --- SNAPSHOTS ---

  Future<void> saveSnapshot(MissionSnapshot snapshot) async {
    await database.into(database.missionSnapshots).insertOnConflictUpdate(
      MissionSnapshotsCompanion.insert(
        missionId: Value(snapshot.missionId),
        status: snapshot.status,
        progress: Value(snapshot.progress),
        latestThought: Value(snapshot.latestThought),
        nextAction: Value(snapshot.nextAction),
        eta: Value(snapshot.eta),
        confidence: Value(snapshot.confidence),
        tokenUsage: Value(snapshot.tokenUsage),
        estimatedCost: Value(snapshot.estimatedCost),
        lastUpdated: Value(DateTime.now()),
      ),
    );
  }

  Future<List<MissionSnapshot>> getLocalSnapshots() async {
    return await database.select(database.missionSnapshots).get();
  }
}
