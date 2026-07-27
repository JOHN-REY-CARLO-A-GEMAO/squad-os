import 'dart:io';
import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;

part 'database.g.dart';

class Conversations extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get workspaceId => integer()();
  TextColumn get title => text()();
  TextColumn get summary => text().nullable()();
  TextColumn get goal => text().nullable()();
  TextColumn get systemPrompt => text().nullable()();
  TextColumn get activeModel => text().withDefault(const Constant('claude-3-5-sonnet'))();
  RealColumn get temperature => real().withDefault(const Constant(0.2))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
}

class ConversationMemories extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get conversationId => integer()();
  TextColumn get memoryKey => text()();
  TextColumn get memoryValue => text().nullable()();
  DateTimeColumn get updatedAt => dateTime().withDefault(currentDateAndTime)();
}

class ConversationEvents extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get parentEventId => integer().nullable()();
  IntColumn get conversationId => integer()();
  IntColumn get sequenceId => integer()();
  TextColumn get eventNamespace => text()();
  TextColumn get eventType => text()();
  TextColumn get payloadJson => text()();
  IntColumn get missionId => integer().nullable()();
  IntColumn get payloadSchemaVersion => integer().withDefault(const Constant(1))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
}

class MissionSnapshots extends Table {
  IntColumn get missionId => integer()();
  TextColumn get status => text()();
  RealColumn get progress => real().withDefault(const Constant(0.0))();
  TextColumn get latestThought => text().nullable()();
  TextColumn get nextAction => text().nullable()();
  IntColumn get eta => integer().withDefault(const Constant(0))();
  TextColumn get confidence => text().withDefault(const Constant('HIGH'))();
  IntColumn get tokenUsage => integer().withDefault(const Constant(0))();
  RealColumn get estimatedCost => real().withDefault(const Constant(0.0))();
  DateTimeColumn get lastUpdated => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {missionId};
}

class Devices extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get userId => text().withDefault(const Constant('default_user'))();
  TextColumn get pushToken => text().unique()();
  TextColumn get platform => text()();
  TextColumn get deviceModel => text().nullable()();
  IntColumn get isActive => integer().withDefault(const Constant(1))();
  DateTimeColumn get registeredAt => dateTime().withDefault(currentDateAndTime)();
  DateTimeColumn get lastSeenAt => dateTime().withDefault(currentDateAndTime)();
}

class SystemNotifications extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get deviceId => integer()();
  TextColumn get title => text()();
  TextColumn get body => text()();
  TextColumn get deepLink => text().nullable()();
  TextColumn get status => text().withDefault(const Constant('PENDING'))();
  DateTimeColumn get sentAt => dateTime().nullable()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
}

@DriftDatabase(tables: [
  Conversations,
  ConversationMemories,
  ConversationEvents,
  MissionSnapshots,
  Devices,
  SystemNotifications,
])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  @override
  int get schemaVersion => 1;
}

QueryExecutor _openConnection() {
  return LazyDatabase(() async {
    final dbFolder = await getApplicationDocumentsDirectory();
    final file = File(p.join(dbFolder.path, 'squados_companion.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
