// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'database.dart';

// ignore_for_file: type=lint
class $ConversationsTable extends Conversations
    with TableInfo<$ConversationsTable, Conversation> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ConversationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _workspaceIdMeta = const VerificationMeta(
    'workspaceId',
  );
  @override
  late final GeneratedColumn<int> workspaceId = GeneratedColumn<int>(
    'workspace_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _summaryMeta = const VerificationMeta(
    'summary',
  );
  @override
  late final GeneratedColumn<String> summary = GeneratedColumn<String>(
    'summary',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _goalMeta = const VerificationMeta('goal');
  @override
  late final GeneratedColumn<String> goal = GeneratedColumn<String>(
    'goal',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _systemPromptMeta = const VerificationMeta(
    'systemPrompt',
  );
  @override
  late final GeneratedColumn<String> systemPrompt = GeneratedColumn<String>(
    'system_prompt',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _activeModelMeta = const VerificationMeta(
    'activeModel',
  );
  @override
  late final GeneratedColumn<String> activeModel = GeneratedColumn<String>(
    'active_model',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('claude-3-5-sonnet'),
  );
  static const VerificationMeta _temperatureMeta = const VerificationMeta(
    'temperature',
  );
  @override
  late final GeneratedColumn<double> temperature = GeneratedColumn<double>(
    'temperature',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(0.2),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    workspaceId,
    title,
    summary,
    goal,
    systemPrompt,
    activeModel,
    temperature,
    createdAt,
    updatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'conversations';
  @override
  VerificationContext validateIntegrity(
    Insertable<Conversation> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('workspace_id')) {
      context.handle(
        _workspaceIdMeta,
        workspaceId.isAcceptableOrUnknown(
          data['workspace_id']!,
          _workspaceIdMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_workspaceIdMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('summary')) {
      context.handle(
        _summaryMeta,
        summary.isAcceptableOrUnknown(data['summary']!, _summaryMeta),
      );
    }
    if (data.containsKey('goal')) {
      context.handle(
        _goalMeta,
        goal.isAcceptableOrUnknown(data['goal']!, _goalMeta),
      );
    }
    if (data.containsKey('system_prompt')) {
      context.handle(
        _systemPromptMeta,
        systemPrompt.isAcceptableOrUnknown(
          data['system_prompt']!,
          _systemPromptMeta,
        ),
      );
    }
    if (data.containsKey('active_model')) {
      context.handle(
        _activeModelMeta,
        activeModel.isAcceptableOrUnknown(
          data['active_model']!,
          _activeModelMeta,
        ),
      );
    }
    if (data.containsKey('temperature')) {
      context.handle(
        _temperatureMeta,
        temperature.isAcceptableOrUnknown(
          data['temperature']!,
          _temperatureMeta,
        ),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Conversation map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Conversation(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      workspaceId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}workspace_id'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      summary: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}summary'],
      ),
      goal: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}goal'],
      ),
      systemPrompt: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}system_prompt'],
      ),
      activeModel: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}active_model'],
      )!,
      temperature: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}temperature'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $ConversationsTable createAlias(String alias) {
    return $ConversationsTable(attachedDatabase, alias);
  }
}

class Conversation extends DataClass implements Insertable<Conversation> {
  final int id;
  final int workspaceId;
  final String title;
  final String? summary;
  final String? goal;
  final String? systemPrompt;
  final String activeModel;
  final double temperature;
  final DateTime createdAt;
  final DateTime updatedAt;
  const Conversation({
    required this.id,
    required this.workspaceId,
    required this.title,
    this.summary,
    this.goal,
    this.systemPrompt,
    required this.activeModel,
    required this.temperature,
    required this.createdAt,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['workspace_id'] = Variable<int>(workspaceId);
    map['title'] = Variable<String>(title);
    if (!nullToAbsent || summary != null) {
      map['summary'] = Variable<String>(summary);
    }
    if (!nullToAbsent || goal != null) {
      map['goal'] = Variable<String>(goal);
    }
    if (!nullToAbsent || systemPrompt != null) {
      map['system_prompt'] = Variable<String>(systemPrompt);
    }
    map['active_model'] = Variable<String>(activeModel);
    map['temperature'] = Variable<double>(temperature);
    map['created_at'] = Variable<DateTime>(createdAt);
    map['updated_at'] = Variable<DateTime>(updatedAt);
    return map;
  }

  ConversationsCompanion toCompanion(bool nullToAbsent) {
    return ConversationsCompanion(
      id: Value(id),
      workspaceId: Value(workspaceId),
      title: Value(title),
      summary: summary == null && nullToAbsent
          ? const Value.absent()
          : Value(summary),
      goal: goal == null && nullToAbsent ? const Value.absent() : Value(goal),
      systemPrompt: systemPrompt == null && nullToAbsent
          ? const Value.absent()
          : Value(systemPrompt),
      activeModel: Value(activeModel),
      temperature: Value(temperature),
      createdAt: Value(createdAt),
      updatedAt: Value(updatedAt),
    );
  }

  factory Conversation.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Conversation(
      id: serializer.fromJson<int>(json['id']),
      workspaceId: serializer.fromJson<int>(json['workspaceId']),
      title: serializer.fromJson<String>(json['title']),
      summary: serializer.fromJson<String?>(json['summary']),
      goal: serializer.fromJson<String?>(json['goal']),
      systemPrompt: serializer.fromJson<String?>(json['systemPrompt']),
      activeModel: serializer.fromJson<String>(json['activeModel']),
      temperature: serializer.fromJson<double>(json['temperature']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'workspaceId': serializer.toJson<int>(workspaceId),
      'title': serializer.toJson<String>(title),
      'summary': serializer.toJson<String?>(summary),
      'goal': serializer.toJson<String?>(goal),
      'systemPrompt': serializer.toJson<String?>(systemPrompt),
      'activeModel': serializer.toJson<String>(activeModel),
      'temperature': serializer.toJson<double>(temperature),
      'createdAt': serializer.toJson<DateTime>(createdAt),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
    };
  }

  Conversation copyWith({
    int? id,
    int? workspaceId,
    String? title,
    Value<String?> summary = const Value.absent(),
    Value<String?> goal = const Value.absent(),
    Value<String?> systemPrompt = const Value.absent(),
    String? activeModel,
    double? temperature,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) => Conversation(
    id: id ?? this.id,
    workspaceId: workspaceId ?? this.workspaceId,
    title: title ?? this.title,
    summary: summary.present ? summary.value : this.summary,
    goal: goal.present ? goal.value : this.goal,
    systemPrompt: systemPrompt.present ? systemPrompt.value : this.systemPrompt,
    activeModel: activeModel ?? this.activeModel,
    temperature: temperature ?? this.temperature,
    createdAt: createdAt ?? this.createdAt,
    updatedAt: updatedAt ?? this.updatedAt,
  );
  Conversation copyWithCompanion(ConversationsCompanion data) {
    return Conversation(
      id: data.id.present ? data.id.value : this.id,
      workspaceId: data.workspaceId.present
          ? data.workspaceId.value
          : this.workspaceId,
      title: data.title.present ? data.title.value : this.title,
      summary: data.summary.present ? data.summary.value : this.summary,
      goal: data.goal.present ? data.goal.value : this.goal,
      systemPrompt: data.systemPrompt.present
          ? data.systemPrompt.value
          : this.systemPrompt,
      activeModel: data.activeModel.present
          ? data.activeModel.value
          : this.activeModel,
      temperature: data.temperature.present
          ? data.temperature.value
          : this.temperature,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Conversation(')
          ..write('id: $id, ')
          ..write('workspaceId: $workspaceId, ')
          ..write('title: $title, ')
          ..write('summary: $summary, ')
          ..write('goal: $goal, ')
          ..write('systemPrompt: $systemPrompt, ')
          ..write('activeModel: $activeModel, ')
          ..write('temperature: $temperature, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    workspaceId,
    title,
    summary,
    goal,
    systemPrompt,
    activeModel,
    temperature,
    createdAt,
    updatedAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Conversation &&
          other.id == this.id &&
          other.workspaceId == this.workspaceId &&
          other.title == this.title &&
          other.summary == this.summary &&
          other.goal == this.goal &&
          other.systemPrompt == this.systemPrompt &&
          other.activeModel == this.activeModel &&
          other.temperature == this.temperature &&
          other.createdAt == this.createdAt &&
          other.updatedAt == this.updatedAt);
}

class ConversationsCompanion extends UpdateCompanion<Conversation> {
  final Value<int> id;
  final Value<int> workspaceId;
  final Value<String> title;
  final Value<String?> summary;
  final Value<String?> goal;
  final Value<String?> systemPrompt;
  final Value<String> activeModel;
  final Value<double> temperature;
  final Value<DateTime> createdAt;
  final Value<DateTime> updatedAt;
  const ConversationsCompanion({
    this.id = const Value.absent(),
    this.workspaceId = const Value.absent(),
    this.title = const Value.absent(),
    this.summary = const Value.absent(),
    this.goal = const Value.absent(),
    this.systemPrompt = const Value.absent(),
    this.activeModel = const Value.absent(),
    this.temperature = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  ConversationsCompanion.insert({
    this.id = const Value.absent(),
    required int workspaceId,
    required String title,
    this.summary = const Value.absent(),
    this.goal = const Value.absent(),
    this.systemPrompt = const Value.absent(),
    this.activeModel = const Value.absent(),
    this.temperature = const Value.absent(),
    this.createdAt = const Value.absent(),
    this.updatedAt = const Value.absent(),
  }) : workspaceId = Value(workspaceId),
       title = Value(title);
  static Insertable<Conversation> custom({
    Expression<int>? id,
    Expression<int>? workspaceId,
    Expression<String>? title,
    Expression<String>? summary,
    Expression<String>? goal,
    Expression<String>? systemPrompt,
    Expression<String>? activeModel,
    Expression<double>? temperature,
    Expression<DateTime>? createdAt,
    Expression<DateTime>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (workspaceId != null) 'workspace_id': workspaceId,
      if (title != null) 'title': title,
      if (summary != null) 'summary': summary,
      if (goal != null) 'goal': goal,
      if (systemPrompt != null) 'system_prompt': systemPrompt,
      if (activeModel != null) 'active_model': activeModel,
      if (temperature != null) 'temperature': temperature,
      if (createdAt != null) 'created_at': createdAt,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  ConversationsCompanion copyWith({
    Value<int>? id,
    Value<int>? workspaceId,
    Value<String>? title,
    Value<String?>? summary,
    Value<String?>? goal,
    Value<String?>? systemPrompt,
    Value<String>? activeModel,
    Value<double>? temperature,
    Value<DateTime>? createdAt,
    Value<DateTime>? updatedAt,
  }) {
    return ConversationsCompanion(
      id: id ?? this.id,
      workspaceId: workspaceId ?? this.workspaceId,
      title: title ?? this.title,
      summary: summary ?? this.summary,
      goal: goal ?? this.goal,
      systemPrompt: systemPrompt ?? this.systemPrompt,
      activeModel: activeModel ?? this.activeModel,
      temperature: temperature ?? this.temperature,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (workspaceId.present) {
      map['workspace_id'] = Variable<int>(workspaceId.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (summary.present) {
      map['summary'] = Variable<String>(summary.value);
    }
    if (goal.present) {
      map['goal'] = Variable<String>(goal.value);
    }
    if (systemPrompt.present) {
      map['system_prompt'] = Variable<String>(systemPrompt.value);
    }
    if (activeModel.present) {
      map['active_model'] = Variable<String>(activeModel.value);
    }
    if (temperature.present) {
      map['temperature'] = Variable<double>(temperature.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ConversationsCompanion(')
          ..write('id: $id, ')
          ..write('workspaceId: $workspaceId, ')
          ..write('title: $title, ')
          ..write('summary: $summary, ')
          ..write('goal: $goal, ')
          ..write('systemPrompt: $systemPrompt, ')
          ..write('activeModel: $activeModel, ')
          ..write('temperature: $temperature, ')
          ..write('createdAt: $createdAt, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $ConversationMemoriesTable extends ConversationMemories
    with TableInfo<$ConversationMemoriesTable, ConversationMemory> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ConversationMemoriesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _conversationIdMeta = const VerificationMeta(
    'conversationId',
  );
  @override
  late final GeneratedColumn<int> conversationId = GeneratedColumn<int>(
    'conversation_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _memoryKeyMeta = const VerificationMeta(
    'memoryKey',
  );
  @override
  late final GeneratedColumn<String> memoryKey = GeneratedColumn<String>(
    'memory_key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _memoryValueMeta = const VerificationMeta(
    'memoryValue',
  );
  @override
  late final GeneratedColumn<String> memoryValue = GeneratedColumn<String>(
    'memory_value',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _updatedAtMeta = const VerificationMeta(
    'updatedAt',
  );
  @override
  late final GeneratedColumn<DateTime> updatedAt = GeneratedColumn<DateTime>(
    'updated_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    conversationId,
    memoryKey,
    memoryValue,
    updatedAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'conversation_memories';
  @override
  VerificationContext validateIntegrity(
    Insertable<ConversationMemory> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('conversation_id')) {
      context.handle(
        _conversationIdMeta,
        conversationId.isAcceptableOrUnknown(
          data['conversation_id']!,
          _conversationIdMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_conversationIdMeta);
    }
    if (data.containsKey('memory_key')) {
      context.handle(
        _memoryKeyMeta,
        memoryKey.isAcceptableOrUnknown(data['memory_key']!, _memoryKeyMeta),
      );
    } else if (isInserting) {
      context.missing(_memoryKeyMeta);
    }
    if (data.containsKey('memory_value')) {
      context.handle(
        _memoryValueMeta,
        memoryValue.isAcceptableOrUnknown(
          data['memory_value']!,
          _memoryValueMeta,
        ),
      );
    }
    if (data.containsKey('updated_at')) {
      context.handle(
        _updatedAtMeta,
        updatedAt.isAcceptableOrUnknown(data['updated_at']!, _updatedAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ConversationMemory map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ConversationMemory(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      conversationId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}conversation_id'],
      )!,
      memoryKey: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}memory_key'],
      )!,
      memoryValue: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}memory_value'],
      ),
      updatedAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}updated_at'],
      )!,
    );
  }

  @override
  $ConversationMemoriesTable createAlias(String alias) {
    return $ConversationMemoriesTable(attachedDatabase, alias);
  }
}

class ConversationMemory extends DataClass
    implements Insertable<ConversationMemory> {
  final int id;
  final int conversationId;
  final String memoryKey;
  final String? memoryValue;
  final DateTime updatedAt;
  const ConversationMemory({
    required this.id,
    required this.conversationId,
    required this.memoryKey,
    this.memoryValue,
    required this.updatedAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['conversation_id'] = Variable<int>(conversationId);
    map['memory_key'] = Variable<String>(memoryKey);
    if (!nullToAbsent || memoryValue != null) {
      map['memory_value'] = Variable<String>(memoryValue);
    }
    map['updated_at'] = Variable<DateTime>(updatedAt);
    return map;
  }

  ConversationMemoriesCompanion toCompanion(bool nullToAbsent) {
    return ConversationMemoriesCompanion(
      id: Value(id),
      conversationId: Value(conversationId),
      memoryKey: Value(memoryKey),
      memoryValue: memoryValue == null && nullToAbsent
          ? const Value.absent()
          : Value(memoryValue),
      updatedAt: Value(updatedAt),
    );
  }

  factory ConversationMemory.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ConversationMemory(
      id: serializer.fromJson<int>(json['id']),
      conversationId: serializer.fromJson<int>(json['conversationId']),
      memoryKey: serializer.fromJson<String>(json['memoryKey']),
      memoryValue: serializer.fromJson<String?>(json['memoryValue']),
      updatedAt: serializer.fromJson<DateTime>(json['updatedAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'conversationId': serializer.toJson<int>(conversationId),
      'memoryKey': serializer.toJson<String>(memoryKey),
      'memoryValue': serializer.toJson<String?>(memoryValue),
      'updatedAt': serializer.toJson<DateTime>(updatedAt),
    };
  }

  ConversationMemory copyWith({
    int? id,
    int? conversationId,
    String? memoryKey,
    Value<String?> memoryValue = const Value.absent(),
    DateTime? updatedAt,
  }) => ConversationMemory(
    id: id ?? this.id,
    conversationId: conversationId ?? this.conversationId,
    memoryKey: memoryKey ?? this.memoryKey,
    memoryValue: memoryValue.present ? memoryValue.value : this.memoryValue,
    updatedAt: updatedAt ?? this.updatedAt,
  );
  ConversationMemory copyWithCompanion(ConversationMemoriesCompanion data) {
    return ConversationMemory(
      id: data.id.present ? data.id.value : this.id,
      conversationId: data.conversationId.present
          ? data.conversationId.value
          : this.conversationId,
      memoryKey: data.memoryKey.present ? data.memoryKey.value : this.memoryKey,
      memoryValue: data.memoryValue.present
          ? data.memoryValue.value
          : this.memoryValue,
      updatedAt: data.updatedAt.present ? data.updatedAt.value : this.updatedAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ConversationMemory(')
          ..write('id: $id, ')
          ..write('conversationId: $conversationId, ')
          ..write('memoryKey: $memoryKey, ')
          ..write('memoryValue: $memoryValue, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode =>
      Object.hash(id, conversationId, memoryKey, memoryValue, updatedAt);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ConversationMemory &&
          other.id == this.id &&
          other.conversationId == this.conversationId &&
          other.memoryKey == this.memoryKey &&
          other.memoryValue == this.memoryValue &&
          other.updatedAt == this.updatedAt);
}

class ConversationMemoriesCompanion
    extends UpdateCompanion<ConversationMemory> {
  final Value<int> id;
  final Value<int> conversationId;
  final Value<String> memoryKey;
  final Value<String?> memoryValue;
  final Value<DateTime> updatedAt;
  const ConversationMemoriesCompanion({
    this.id = const Value.absent(),
    this.conversationId = const Value.absent(),
    this.memoryKey = const Value.absent(),
    this.memoryValue = const Value.absent(),
    this.updatedAt = const Value.absent(),
  });
  ConversationMemoriesCompanion.insert({
    this.id = const Value.absent(),
    required int conversationId,
    required String memoryKey,
    this.memoryValue = const Value.absent(),
    this.updatedAt = const Value.absent(),
  }) : conversationId = Value(conversationId),
       memoryKey = Value(memoryKey);
  static Insertable<ConversationMemory> custom({
    Expression<int>? id,
    Expression<int>? conversationId,
    Expression<String>? memoryKey,
    Expression<String>? memoryValue,
    Expression<DateTime>? updatedAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (conversationId != null) 'conversation_id': conversationId,
      if (memoryKey != null) 'memory_key': memoryKey,
      if (memoryValue != null) 'memory_value': memoryValue,
      if (updatedAt != null) 'updated_at': updatedAt,
    });
  }

  ConversationMemoriesCompanion copyWith({
    Value<int>? id,
    Value<int>? conversationId,
    Value<String>? memoryKey,
    Value<String?>? memoryValue,
    Value<DateTime>? updatedAt,
  }) {
    return ConversationMemoriesCompanion(
      id: id ?? this.id,
      conversationId: conversationId ?? this.conversationId,
      memoryKey: memoryKey ?? this.memoryKey,
      memoryValue: memoryValue ?? this.memoryValue,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (conversationId.present) {
      map['conversation_id'] = Variable<int>(conversationId.value);
    }
    if (memoryKey.present) {
      map['memory_key'] = Variable<String>(memoryKey.value);
    }
    if (memoryValue.present) {
      map['memory_value'] = Variable<String>(memoryValue.value);
    }
    if (updatedAt.present) {
      map['updated_at'] = Variable<DateTime>(updatedAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ConversationMemoriesCompanion(')
          ..write('id: $id, ')
          ..write('conversationId: $conversationId, ')
          ..write('memoryKey: $memoryKey, ')
          ..write('memoryValue: $memoryValue, ')
          ..write('updatedAt: $updatedAt')
          ..write(')'))
        .toString();
  }
}

class $ConversationEventsTable extends ConversationEvents
    with TableInfo<$ConversationEventsTable, ConversationEvent> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ConversationEventsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _parentEventIdMeta = const VerificationMeta(
    'parentEventId',
  );
  @override
  late final GeneratedColumn<int> parentEventId = GeneratedColumn<int>(
    'parent_event_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _conversationIdMeta = const VerificationMeta(
    'conversationId',
  );
  @override
  late final GeneratedColumn<int> conversationId = GeneratedColumn<int>(
    'conversation_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _sequenceIdMeta = const VerificationMeta(
    'sequenceId',
  );
  @override
  late final GeneratedColumn<int> sequenceId = GeneratedColumn<int>(
    'sequence_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _eventNamespaceMeta = const VerificationMeta(
    'eventNamespace',
  );
  @override
  late final GeneratedColumn<String> eventNamespace = GeneratedColumn<String>(
    'event_namespace',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _eventTypeMeta = const VerificationMeta(
    'eventType',
  );
  @override
  late final GeneratedColumn<String> eventType = GeneratedColumn<String>(
    'event_type',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _payloadJsonMeta = const VerificationMeta(
    'payloadJson',
  );
  @override
  late final GeneratedColumn<String> payloadJson = GeneratedColumn<String>(
    'payload_json',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _missionIdMeta = const VerificationMeta(
    'missionId',
  );
  @override
  late final GeneratedColumn<int> missionId = GeneratedColumn<int>(
    'mission_id',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _payloadSchemaVersionMeta =
      const VerificationMeta('payloadSchemaVersion');
  @override
  late final GeneratedColumn<int> payloadSchemaVersion = GeneratedColumn<int>(
    'payload_schema_version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    parentEventId,
    conversationId,
    sequenceId,
    eventNamespace,
    eventType,
    payloadJson,
    missionId,
    payloadSchemaVersion,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'conversation_events';
  @override
  VerificationContext validateIntegrity(
    Insertable<ConversationEvent> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('parent_event_id')) {
      context.handle(
        _parentEventIdMeta,
        parentEventId.isAcceptableOrUnknown(
          data['parent_event_id']!,
          _parentEventIdMeta,
        ),
      );
    }
    if (data.containsKey('conversation_id')) {
      context.handle(
        _conversationIdMeta,
        conversationId.isAcceptableOrUnknown(
          data['conversation_id']!,
          _conversationIdMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_conversationIdMeta);
    }
    if (data.containsKey('sequence_id')) {
      context.handle(
        _sequenceIdMeta,
        sequenceId.isAcceptableOrUnknown(data['sequence_id']!, _sequenceIdMeta),
      );
    } else if (isInserting) {
      context.missing(_sequenceIdMeta);
    }
    if (data.containsKey('event_namespace')) {
      context.handle(
        _eventNamespaceMeta,
        eventNamespace.isAcceptableOrUnknown(
          data['event_namespace']!,
          _eventNamespaceMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_eventNamespaceMeta);
    }
    if (data.containsKey('event_type')) {
      context.handle(
        _eventTypeMeta,
        eventType.isAcceptableOrUnknown(data['event_type']!, _eventTypeMeta),
      );
    } else if (isInserting) {
      context.missing(_eventTypeMeta);
    }
    if (data.containsKey('payload_json')) {
      context.handle(
        _payloadJsonMeta,
        payloadJson.isAcceptableOrUnknown(
          data['payload_json']!,
          _payloadJsonMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_payloadJsonMeta);
    }
    if (data.containsKey('mission_id')) {
      context.handle(
        _missionIdMeta,
        missionId.isAcceptableOrUnknown(data['mission_id']!, _missionIdMeta),
      );
    }
    if (data.containsKey('payload_schema_version')) {
      context.handle(
        _payloadSchemaVersionMeta,
        payloadSchemaVersion.isAcceptableOrUnknown(
          data['payload_schema_version']!,
          _payloadSchemaVersionMeta,
        ),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  ConversationEvent map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ConversationEvent(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      parentEventId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}parent_event_id'],
      ),
      conversationId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}conversation_id'],
      )!,
      sequenceId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}sequence_id'],
      )!,
      eventNamespace: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}event_namespace'],
      )!,
      eventType: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}event_type'],
      )!,
      payloadJson: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}payload_json'],
      )!,
      missionId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}mission_id'],
      ),
      payloadSchemaVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}payload_schema_version'],
      )!,
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $ConversationEventsTable createAlias(String alias) {
    return $ConversationEventsTable(attachedDatabase, alias);
  }
}

class ConversationEvent extends DataClass
    implements Insertable<ConversationEvent> {
  final int id;
  final int? parentEventId;
  final int conversationId;
  final int sequenceId;
  final String eventNamespace;
  final String eventType;
  final String payloadJson;
  final int? missionId;
  final int payloadSchemaVersion;
  final DateTime createdAt;
  const ConversationEvent({
    required this.id,
    this.parentEventId,
    required this.conversationId,
    required this.sequenceId,
    required this.eventNamespace,
    required this.eventType,
    required this.payloadJson,
    this.missionId,
    required this.payloadSchemaVersion,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    if (!nullToAbsent || parentEventId != null) {
      map['parent_event_id'] = Variable<int>(parentEventId);
    }
    map['conversation_id'] = Variable<int>(conversationId);
    map['sequence_id'] = Variable<int>(sequenceId);
    map['event_namespace'] = Variable<String>(eventNamespace);
    map['event_type'] = Variable<String>(eventType);
    map['payload_json'] = Variable<String>(payloadJson);
    if (!nullToAbsent || missionId != null) {
      map['mission_id'] = Variable<int>(missionId);
    }
    map['payload_schema_version'] = Variable<int>(payloadSchemaVersion);
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  ConversationEventsCompanion toCompanion(bool nullToAbsent) {
    return ConversationEventsCompanion(
      id: Value(id),
      parentEventId: parentEventId == null && nullToAbsent
          ? const Value.absent()
          : Value(parentEventId),
      conversationId: Value(conversationId),
      sequenceId: Value(sequenceId),
      eventNamespace: Value(eventNamespace),
      eventType: Value(eventType),
      payloadJson: Value(payloadJson),
      missionId: missionId == null && nullToAbsent
          ? const Value.absent()
          : Value(missionId),
      payloadSchemaVersion: Value(payloadSchemaVersion),
      createdAt: Value(createdAt),
    );
  }

  factory ConversationEvent.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ConversationEvent(
      id: serializer.fromJson<int>(json['id']),
      parentEventId: serializer.fromJson<int?>(json['parentEventId']),
      conversationId: serializer.fromJson<int>(json['conversationId']),
      sequenceId: serializer.fromJson<int>(json['sequenceId']),
      eventNamespace: serializer.fromJson<String>(json['eventNamespace']),
      eventType: serializer.fromJson<String>(json['eventType']),
      payloadJson: serializer.fromJson<String>(json['payloadJson']),
      missionId: serializer.fromJson<int?>(json['missionId']),
      payloadSchemaVersion: serializer.fromJson<int>(
        json['payloadSchemaVersion'],
      ),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'parentEventId': serializer.toJson<int?>(parentEventId),
      'conversationId': serializer.toJson<int>(conversationId),
      'sequenceId': serializer.toJson<int>(sequenceId),
      'eventNamespace': serializer.toJson<String>(eventNamespace),
      'eventType': serializer.toJson<String>(eventType),
      'payloadJson': serializer.toJson<String>(payloadJson),
      'missionId': serializer.toJson<int?>(missionId),
      'payloadSchemaVersion': serializer.toJson<int>(payloadSchemaVersion),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  ConversationEvent copyWith({
    int? id,
    Value<int?> parentEventId = const Value.absent(),
    int? conversationId,
    int? sequenceId,
    String? eventNamespace,
    String? eventType,
    String? payloadJson,
    Value<int?> missionId = const Value.absent(),
    int? payloadSchemaVersion,
    DateTime? createdAt,
  }) => ConversationEvent(
    id: id ?? this.id,
    parentEventId: parentEventId.present
        ? parentEventId.value
        : this.parentEventId,
    conversationId: conversationId ?? this.conversationId,
    sequenceId: sequenceId ?? this.sequenceId,
    eventNamespace: eventNamespace ?? this.eventNamespace,
    eventType: eventType ?? this.eventType,
    payloadJson: payloadJson ?? this.payloadJson,
    missionId: missionId.present ? missionId.value : this.missionId,
    payloadSchemaVersion: payloadSchemaVersion ?? this.payloadSchemaVersion,
    createdAt: createdAt ?? this.createdAt,
  );
  ConversationEvent copyWithCompanion(ConversationEventsCompanion data) {
    return ConversationEvent(
      id: data.id.present ? data.id.value : this.id,
      parentEventId: data.parentEventId.present
          ? data.parentEventId.value
          : this.parentEventId,
      conversationId: data.conversationId.present
          ? data.conversationId.value
          : this.conversationId,
      sequenceId: data.sequenceId.present
          ? data.sequenceId.value
          : this.sequenceId,
      eventNamespace: data.eventNamespace.present
          ? data.eventNamespace.value
          : this.eventNamespace,
      eventType: data.eventType.present ? data.eventType.value : this.eventType,
      payloadJson: data.payloadJson.present
          ? data.payloadJson.value
          : this.payloadJson,
      missionId: data.missionId.present ? data.missionId.value : this.missionId,
      payloadSchemaVersion: data.payloadSchemaVersion.present
          ? data.payloadSchemaVersion.value
          : this.payloadSchemaVersion,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ConversationEvent(')
          ..write('id: $id, ')
          ..write('parentEventId: $parentEventId, ')
          ..write('conversationId: $conversationId, ')
          ..write('sequenceId: $sequenceId, ')
          ..write('eventNamespace: $eventNamespace, ')
          ..write('eventType: $eventType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('missionId: $missionId, ')
          ..write('payloadSchemaVersion: $payloadSchemaVersion, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    parentEventId,
    conversationId,
    sequenceId,
    eventNamespace,
    eventType,
    payloadJson,
    missionId,
    payloadSchemaVersion,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ConversationEvent &&
          other.id == this.id &&
          other.parentEventId == this.parentEventId &&
          other.conversationId == this.conversationId &&
          other.sequenceId == this.sequenceId &&
          other.eventNamespace == this.eventNamespace &&
          other.eventType == this.eventType &&
          other.payloadJson == this.payloadJson &&
          other.missionId == this.missionId &&
          other.payloadSchemaVersion == this.payloadSchemaVersion &&
          other.createdAt == this.createdAt);
}

class ConversationEventsCompanion extends UpdateCompanion<ConversationEvent> {
  final Value<int> id;
  final Value<int?> parentEventId;
  final Value<int> conversationId;
  final Value<int> sequenceId;
  final Value<String> eventNamespace;
  final Value<String> eventType;
  final Value<String> payloadJson;
  final Value<int?> missionId;
  final Value<int> payloadSchemaVersion;
  final Value<DateTime> createdAt;
  const ConversationEventsCompanion({
    this.id = const Value.absent(),
    this.parentEventId = const Value.absent(),
    this.conversationId = const Value.absent(),
    this.sequenceId = const Value.absent(),
    this.eventNamespace = const Value.absent(),
    this.eventType = const Value.absent(),
    this.payloadJson = const Value.absent(),
    this.missionId = const Value.absent(),
    this.payloadSchemaVersion = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  ConversationEventsCompanion.insert({
    this.id = const Value.absent(),
    this.parentEventId = const Value.absent(),
    required int conversationId,
    required int sequenceId,
    required String eventNamespace,
    required String eventType,
    required String payloadJson,
    this.missionId = const Value.absent(),
    this.payloadSchemaVersion = const Value.absent(),
    this.createdAt = const Value.absent(),
  }) : conversationId = Value(conversationId),
       sequenceId = Value(sequenceId),
       eventNamespace = Value(eventNamespace),
       eventType = Value(eventType),
       payloadJson = Value(payloadJson);
  static Insertable<ConversationEvent> custom({
    Expression<int>? id,
    Expression<int>? parentEventId,
    Expression<int>? conversationId,
    Expression<int>? sequenceId,
    Expression<String>? eventNamespace,
    Expression<String>? eventType,
    Expression<String>? payloadJson,
    Expression<int>? missionId,
    Expression<int>? payloadSchemaVersion,
    Expression<DateTime>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (parentEventId != null) 'parent_event_id': parentEventId,
      if (conversationId != null) 'conversation_id': conversationId,
      if (sequenceId != null) 'sequence_id': sequenceId,
      if (eventNamespace != null) 'event_namespace': eventNamespace,
      if (eventType != null) 'event_type': eventType,
      if (payloadJson != null) 'payload_json': payloadJson,
      if (missionId != null) 'mission_id': missionId,
      if (payloadSchemaVersion != null)
        'payload_schema_version': payloadSchemaVersion,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  ConversationEventsCompanion copyWith({
    Value<int>? id,
    Value<int?>? parentEventId,
    Value<int>? conversationId,
    Value<int>? sequenceId,
    Value<String>? eventNamespace,
    Value<String>? eventType,
    Value<String>? payloadJson,
    Value<int?>? missionId,
    Value<int>? payloadSchemaVersion,
    Value<DateTime>? createdAt,
  }) {
    return ConversationEventsCompanion(
      id: id ?? this.id,
      parentEventId: parentEventId ?? this.parentEventId,
      conversationId: conversationId ?? this.conversationId,
      sequenceId: sequenceId ?? this.sequenceId,
      eventNamespace: eventNamespace ?? this.eventNamespace,
      eventType: eventType ?? this.eventType,
      payloadJson: payloadJson ?? this.payloadJson,
      missionId: missionId ?? this.missionId,
      payloadSchemaVersion: payloadSchemaVersion ?? this.payloadSchemaVersion,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (parentEventId.present) {
      map['parent_event_id'] = Variable<int>(parentEventId.value);
    }
    if (conversationId.present) {
      map['conversation_id'] = Variable<int>(conversationId.value);
    }
    if (sequenceId.present) {
      map['sequence_id'] = Variable<int>(sequenceId.value);
    }
    if (eventNamespace.present) {
      map['event_namespace'] = Variable<String>(eventNamespace.value);
    }
    if (eventType.present) {
      map['event_type'] = Variable<String>(eventType.value);
    }
    if (payloadJson.present) {
      map['payload_json'] = Variable<String>(payloadJson.value);
    }
    if (missionId.present) {
      map['mission_id'] = Variable<int>(missionId.value);
    }
    if (payloadSchemaVersion.present) {
      map['payload_schema_version'] = Variable<int>(payloadSchemaVersion.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ConversationEventsCompanion(')
          ..write('id: $id, ')
          ..write('parentEventId: $parentEventId, ')
          ..write('conversationId: $conversationId, ')
          ..write('sequenceId: $sequenceId, ')
          ..write('eventNamespace: $eventNamespace, ')
          ..write('eventType: $eventType, ')
          ..write('payloadJson: $payloadJson, ')
          ..write('missionId: $missionId, ')
          ..write('payloadSchemaVersion: $payloadSchemaVersion, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

class $MissionSnapshotsTable extends MissionSnapshots
    with TableInfo<$MissionSnapshotsTable, MissionSnapshot> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $MissionSnapshotsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _missionIdMeta = const VerificationMeta(
    'missionId',
  );
  @override
  late final GeneratedColumn<int> missionId = GeneratedColumn<int>(
    'mission_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _progressMeta = const VerificationMeta(
    'progress',
  );
  @override
  late final GeneratedColumn<double> progress = GeneratedColumn<double>(
    'progress',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(0.0),
  );
  static const VerificationMeta _latestThoughtMeta = const VerificationMeta(
    'latestThought',
  );
  @override
  late final GeneratedColumn<String> latestThought = GeneratedColumn<String>(
    'latest_thought',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _nextActionMeta = const VerificationMeta(
    'nextAction',
  );
  @override
  late final GeneratedColumn<String> nextAction = GeneratedColumn<String>(
    'next_action',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _etaMeta = const VerificationMeta('eta');
  @override
  late final GeneratedColumn<int> eta = GeneratedColumn<int>(
    'eta',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _confidenceMeta = const VerificationMeta(
    'confidence',
  );
  @override
  late final GeneratedColumn<String> confidence = GeneratedColumn<String>(
    'confidence',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('HIGH'),
  );
  static const VerificationMeta _tokenUsageMeta = const VerificationMeta(
    'tokenUsage',
  );
  @override
  late final GeneratedColumn<int> tokenUsage = GeneratedColumn<int>(
    'token_usage',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(0),
  );
  static const VerificationMeta _estimatedCostMeta = const VerificationMeta(
    'estimatedCost',
  );
  @override
  late final GeneratedColumn<double> estimatedCost = GeneratedColumn<double>(
    'estimated_cost',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(0.0),
  );
  static const VerificationMeta _lastUpdatedMeta = const VerificationMeta(
    'lastUpdated',
  );
  @override
  late final GeneratedColumn<DateTime> lastUpdated = GeneratedColumn<DateTime>(
    'last_updated',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    missionId,
    status,
    progress,
    latestThought,
    nextAction,
    eta,
    confidence,
    tokenUsage,
    estimatedCost,
    lastUpdated,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'mission_snapshots';
  @override
  VerificationContext validateIntegrity(
    Insertable<MissionSnapshot> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('mission_id')) {
      context.handle(
        _missionIdMeta,
        missionId.isAcceptableOrUnknown(data['mission_id']!, _missionIdMeta),
      );
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    } else if (isInserting) {
      context.missing(_statusMeta);
    }
    if (data.containsKey('progress')) {
      context.handle(
        _progressMeta,
        progress.isAcceptableOrUnknown(data['progress']!, _progressMeta),
      );
    }
    if (data.containsKey('latest_thought')) {
      context.handle(
        _latestThoughtMeta,
        latestThought.isAcceptableOrUnknown(
          data['latest_thought']!,
          _latestThoughtMeta,
        ),
      );
    }
    if (data.containsKey('next_action')) {
      context.handle(
        _nextActionMeta,
        nextAction.isAcceptableOrUnknown(data['next_action']!, _nextActionMeta),
      );
    }
    if (data.containsKey('eta')) {
      context.handle(
        _etaMeta,
        eta.isAcceptableOrUnknown(data['eta']!, _etaMeta),
      );
    }
    if (data.containsKey('confidence')) {
      context.handle(
        _confidenceMeta,
        confidence.isAcceptableOrUnknown(data['confidence']!, _confidenceMeta),
      );
    }
    if (data.containsKey('token_usage')) {
      context.handle(
        _tokenUsageMeta,
        tokenUsage.isAcceptableOrUnknown(data['token_usage']!, _tokenUsageMeta),
      );
    }
    if (data.containsKey('estimated_cost')) {
      context.handle(
        _estimatedCostMeta,
        estimatedCost.isAcceptableOrUnknown(
          data['estimated_cost']!,
          _estimatedCostMeta,
        ),
      );
    }
    if (data.containsKey('last_updated')) {
      context.handle(
        _lastUpdatedMeta,
        lastUpdated.isAcceptableOrUnknown(
          data['last_updated']!,
          _lastUpdatedMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {missionId};
  @override
  MissionSnapshot map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return MissionSnapshot(
      missionId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}mission_id'],
      )!,
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      progress: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}progress'],
      )!,
      latestThought: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}latest_thought'],
      ),
      nextAction: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}next_action'],
      ),
      eta: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}eta'],
      )!,
      confidence: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}confidence'],
      )!,
      tokenUsage: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}token_usage'],
      )!,
      estimatedCost: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}estimated_cost'],
      )!,
      lastUpdated: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_updated'],
      )!,
    );
  }

  @override
  $MissionSnapshotsTable createAlias(String alias) {
    return $MissionSnapshotsTable(attachedDatabase, alias);
  }
}

class MissionSnapshot extends DataClass implements Insertable<MissionSnapshot> {
  final int missionId;
  final String status;
  final double progress;
  final String? latestThought;
  final String? nextAction;
  final int eta;
  final String confidence;
  final int tokenUsage;
  final double estimatedCost;
  final DateTime lastUpdated;
  const MissionSnapshot({
    required this.missionId,
    required this.status,
    required this.progress,
    this.latestThought,
    this.nextAction,
    required this.eta,
    required this.confidence,
    required this.tokenUsage,
    required this.estimatedCost,
    required this.lastUpdated,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['mission_id'] = Variable<int>(missionId);
    map['status'] = Variable<String>(status);
    map['progress'] = Variable<double>(progress);
    if (!nullToAbsent || latestThought != null) {
      map['latest_thought'] = Variable<String>(latestThought);
    }
    if (!nullToAbsent || nextAction != null) {
      map['next_action'] = Variable<String>(nextAction);
    }
    map['eta'] = Variable<int>(eta);
    map['confidence'] = Variable<String>(confidence);
    map['token_usage'] = Variable<int>(tokenUsage);
    map['estimated_cost'] = Variable<double>(estimatedCost);
    map['last_updated'] = Variable<DateTime>(lastUpdated);
    return map;
  }

  MissionSnapshotsCompanion toCompanion(bool nullToAbsent) {
    return MissionSnapshotsCompanion(
      missionId: Value(missionId),
      status: Value(status),
      progress: Value(progress),
      latestThought: latestThought == null && nullToAbsent
          ? const Value.absent()
          : Value(latestThought),
      nextAction: nextAction == null && nullToAbsent
          ? const Value.absent()
          : Value(nextAction),
      eta: Value(eta),
      confidence: Value(confidence),
      tokenUsage: Value(tokenUsage),
      estimatedCost: Value(estimatedCost),
      lastUpdated: Value(lastUpdated),
    );
  }

  factory MissionSnapshot.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return MissionSnapshot(
      missionId: serializer.fromJson<int>(json['missionId']),
      status: serializer.fromJson<String>(json['status']),
      progress: serializer.fromJson<double>(json['progress']),
      latestThought: serializer.fromJson<String?>(json['latestThought']),
      nextAction: serializer.fromJson<String?>(json['nextAction']),
      eta: serializer.fromJson<int>(json['eta']),
      confidence: serializer.fromJson<String>(json['confidence']),
      tokenUsage: serializer.fromJson<int>(json['tokenUsage']),
      estimatedCost: serializer.fromJson<double>(json['estimatedCost']),
      lastUpdated: serializer.fromJson<DateTime>(json['lastUpdated']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'missionId': serializer.toJson<int>(missionId),
      'status': serializer.toJson<String>(status),
      'progress': serializer.toJson<double>(progress),
      'latestThought': serializer.toJson<String?>(latestThought),
      'nextAction': serializer.toJson<String?>(nextAction),
      'eta': serializer.toJson<int>(eta),
      'confidence': serializer.toJson<String>(confidence),
      'tokenUsage': serializer.toJson<int>(tokenUsage),
      'estimatedCost': serializer.toJson<double>(estimatedCost),
      'lastUpdated': serializer.toJson<DateTime>(lastUpdated),
    };
  }

  MissionSnapshot copyWith({
    int? missionId,
    String? status,
    double? progress,
    Value<String?> latestThought = const Value.absent(),
    Value<String?> nextAction = const Value.absent(),
    int? eta,
    String? confidence,
    int? tokenUsage,
    double? estimatedCost,
    DateTime? lastUpdated,
  }) => MissionSnapshot(
    missionId: missionId ?? this.missionId,
    status: status ?? this.status,
    progress: progress ?? this.progress,
    latestThought: latestThought.present
        ? latestThought.value
        : this.latestThought,
    nextAction: nextAction.present ? nextAction.value : this.nextAction,
    eta: eta ?? this.eta,
    confidence: confidence ?? this.confidence,
    tokenUsage: tokenUsage ?? this.tokenUsage,
    estimatedCost: estimatedCost ?? this.estimatedCost,
    lastUpdated: lastUpdated ?? this.lastUpdated,
  );
  MissionSnapshot copyWithCompanion(MissionSnapshotsCompanion data) {
    return MissionSnapshot(
      missionId: data.missionId.present ? data.missionId.value : this.missionId,
      status: data.status.present ? data.status.value : this.status,
      progress: data.progress.present ? data.progress.value : this.progress,
      latestThought: data.latestThought.present
          ? data.latestThought.value
          : this.latestThought,
      nextAction: data.nextAction.present
          ? data.nextAction.value
          : this.nextAction,
      eta: data.eta.present ? data.eta.value : this.eta,
      confidence: data.confidence.present
          ? data.confidence.value
          : this.confidence,
      tokenUsage: data.tokenUsage.present
          ? data.tokenUsage.value
          : this.tokenUsage,
      estimatedCost: data.estimatedCost.present
          ? data.estimatedCost.value
          : this.estimatedCost,
      lastUpdated: data.lastUpdated.present
          ? data.lastUpdated.value
          : this.lastUpdated,
    );
  }

  @override
  String toString() {
    return (StringBuffer('MissionSnapshot(')
          ..write('missionId: $missionId, ')
          ..write('status: $status, ')
          ..write('progress: $progress, ')
          ..write('latestThought: $latestThought, ')
          ..write('nextAction: $nextAction, ')
          ..write('eta: $eta, ')
          ..write('confidence: $confidence, ')
          ..write('tokenUsage: $tokenUsage, ')
          ..write('estimatedCost: $estimatedCost, ')
          ..write('lastUpdated: $lastUpdated')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    missionId,
    status,
    progress,
    latestThought,
    nextAction,
    eta,
    confidence,
    tokenUsage,
    estimatedCost,
    lastUpdated,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is MissionSnapshot &&
          other.missionId == this.missionId &&
          other.status == this.status &&
          other.progress == this.progress &&
          other.latestThought == this.latestThought &&
          other.nextAction == this.nextAction &&
          other.eta == this.eta &&
          other.confidence == this.confidence &&
          other.tokenUsage == this.tokenUsage &&
          other.estimatedCost == this.estimatedCost &&
          other.lastUpdated == this.lastUpdated);
}

class MissionSnapshotsCompanion extends UpdateCompanion<MissionSnapshot> {
  final Value<int> missionId;
  final Value<String> status;
  final Value<double> progress;
  final Value<String?> latestThought;
  final Value<String?> nextAction;
  final Value<int> eta;
  final Value<String> confidence;
  final Value<int> tokenUsage;
  final Value<double> estimatedCost;
  final Value<DateTime> lastUpdated;
  const MissionSnapshotsCompanion({
    this.missionId = const Value.absent(),
    this.status = const Value.absent(),
    this.progress = const Value.absent(),
    this.latestThought = const Value.absent(),
    this.nextAction = const Value.absent(),
    this.eta = const Value.absent(),
    this.confidence = const Value.absent(),
    this.tokenUsage = const Value.absent(),
    this.estimatedCost = const Value.absent(),
    this.lastUpdated = const Value.absent(),
  });
  MissionSnapshotsCompanion.insert({
    this.missionId = const Value.absent(),
    required String status,
    this.progress = const Value.absent(),
    this.latestThought = const Value.absent(),
    this.nextAction = const Value.absent(),
    this.eta = const Value.absent(),
    this.confidence = const Value.absent(),
    this.tokenUsage = const Value.absent(),
    this.estimatedCost = const Value.absent(),
    this.lastUpdated = const Value.absent(),
  }) : status = Value(status);
  static Insertable<MissionSnapshot> custom({
    Expression<int>? missionId,
    Expression<String>? status,
    Expression<double>? progress,
    Expression<String>? latestThought,
    Expression<String>? nextAction,
    Expression<int>? eta,
    Expression<String>? confidence,
    Expression<int>? tokenUsage,
    Expression<double>? estimatedCost,
    Expression<DateTime>? lastUpdated,
  }) {
    return RawValuesInsertable({
      if (missionId != null) 'mission_id': missionId,
      if (status != null) 'status': status,
      if (progress != null) 'progress': progress,
      if (latestThought != null) 'latest_thought': latestThought,
      if (nextAction != null) 'next_action': nextAction,
      if (eta != null) 'eta': eta,
      if (confidence != null) 'confidence': confidence,
      if (tokenUsage != null) 'token_usage': tokenUsage,
      if (estimatedCost != null) 'estimated_cost': estimatedCost,
      if (lastUpdated != null) 'last_updated': lastUpdated,
    });
  }

  MissionSnapshotsCompanion copyWith({
    Value<int>? missionId,
    Value<String>? status,
    Value<double>? progress,
    Value<String?>? latestThought,
    Value<String?>? nextAction,
    Value<int>? eta,
    Value<String>? confidence,
    Value<int>? tokenUsage,
    Value<double>? estimatedCost,
    Value<DateTime>? lastUpdated,
  }) {
    return MissionSnapshotsCompanion(
      missionId: missionId ?? this.missionId,
      status: status ?? this.status,
      progress: progress ?? this.progress,
      latestThought: latestThought ?? this.latestThought,
      nextAction: nextAction ?? this.nextAction,
      eta: eta ?? this.eta,
      confidence: confidence ?? this.confidence,
      tokenUsage: tokenUsage ?? this.tokenUsage,
      estimatedCost: estimatedCost ?? this.estimatedCost,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (missionId.present) {
      map['mission_id'] = Variable<int>(missionId.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (progress.present) {
      map['progress'] = Variable<double>(progress.value);
    }
    if (latestThought.present) {
      map['latest_thought'] = Variable<String>(latestThought.value);
    }
    if (nextAction.present) {
      map['next_action'] = Variable<String>(nextAction.value);
    }
    if (eta.present) {
      map['eta'] = Variable<int>(eta.value);
    }
    if (confidence.present) {
      map['confidence'] = Variable<String>(confidence.value);
    }
    if (tokenUsage.present) {
      map['token_usage'] = Variable<int>(tokenUsage.value);
    }
    if (estimatedCost.present) {
      map['estimated_cost'] = Variable<double>(estimatedCost.value);
    }
    if (lastUpdated.present) {
      map['last_updated'] = Variable<DateTime>(lastUpdated.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('MissionSnapshotsCompanion(')
          ..write('missionId: $missionId, ')
          ..write('status: $status, ')
          ..write('progress: $progress, ')
          ..write('latestThought: $latestThought, ')
          ..write('nextAction: $nextAction, ')
          ..write('eta: $eta, ')
          ..write('confidence: $confidence, ')
          ..write('tokenUsage: $tokenUsage, ')
          ..write('estimatedCost: $estimatedCost, ')
          ..write('lastUpdated: $lastUpdated')
          ..write(')'))
        .toString();
  }
}

class $DevicesTable extends Devices with TableInfo<$DevicesTable, Device> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $DevicesTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _userIdMeta = const VerificationMeta('userId');
  @override
  late final GeneratedColumn<String> userId = GeneratedColumn<String>(
    'user_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('default_user'),
  );
  static const VerificationMeta _pushTokenMeta = const VerificationMeta(
    'pushToken',
  );
  @override
  late final GeneratedColumn<String> pushToken = GeneratedColumn<String>(
    'push_token',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
    defaultConstraints: GeneratedColumn.constraintIsAlways('UNIQUE'),
  );
  static const VerificationMeta _platformMeta = const VerificationMeta(
    'platform',
  );
  @override
  late final GeneratedColumn<String> platform = GeneratedColumn<String>(
    'platform',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deviceModelMeta = const VerificationMeta(
    'deviceModel',
  );
  @override
  late final GeneratedColumn<String> deviceModel = GeneratedColumn<String>(
    'device_model',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _isActiveMeta = const VerificationMeta(
    'isActive',
  );
  @override
  late final GeneratedColumn<int> isActive = GeneratedColumn<int>(
    'is_active',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(1),
  );
  static const VerificationMeta _registeredAtMeta = const VerificationMeta(
    'registeredAt',
  );
  @override
  late final GeneratedColumn<DateTime> registeredAt = GeneratedColumn<DateTime>(
    'registered_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  static const VerificationMeta _lastSeenAtMeta = const VerificationMeta(
    'lastSeenAt',
  );
  @override
  late final GeneratedColumn<DateTime> lastSeenAt = GeneratedColumn<DateTime>(
    'last_seen_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    userId,
    pushToken,
    platform,
    deviceModel,
    isActive,
    registeredAt,
    lastSeenAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'devices';
  @override
  VerificationContext validateIntegrity(
    Insertable<Device> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('user_id')) {
      context.handle(
        _userIdMeta,
        userId.isAcceptableOrUnknown(data['user_id']!, _userIdMeta),
      );
    }
    if (data.containsKey('push_token')) {
      context.handle(
        _pushTokenMeta,
        pushToken.isAcceptableOrUnknown(data['push_token']!, _pushTokenMeta),
      );
    } else if (isInserting) {
      context.missing(_pushTokenMeta);
    }
    if (data.containsKey('platform')) {
      context.handle(
        _platformMeta,
        platform.isAcceptableOrUnknown(data['platform']!, _platformMeta),
      );
    } else if (isInserting) {
      context.missing(_platformMeta);
    }
    if (data.containsKey('device_model')) {
      context.handle(
        _deviceModelMeta,
        deviceModel.isAcceptableOrUnknown(
          data['device_model']!,
          _deviceModelMeta,
        ),
      );
    }
    if (data.containsKey('is_active')) {
      context.handle(
        _isActiveMeta,
        isActive.isAcceptableOrUnknown(data['is_active']!, _isActiveMeta),
      );
    }
    if (data.containsKey('registered_at')) {
      context.handle(
        _registeredAtMeta,
        registeredAt.isAcceptableOrUnknown(
          data['registered_at']!,
          _registeredAtMeta,
        ),
      );
    }
    if (data.containsKey('last_seen_at')) {
      context.handle(
        _lastSeenAtMeta,
        lastSeenAt.isAcceptableOrUnknown(
          data['last_seen_at']!,
          _lastSeenAtMeta,
        ),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  Device map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return Device(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      userId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}user_id'],
      )!,
      pushToken: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}push_token'],
      )!,
      platform: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}platform'],
      )!,
      deviceModel: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}device_model'],
      ),
      isActive: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}is_active'],
      )!,
      registeredAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}registered_at'],
      )!,
      lastSeenAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}last_seen_at'],
      )!,
    );
  }

  @override
  $DevicesTable createAlias(String alias) {
    return $DevicesTable(attachedDatabase, alias);
  }
}

class Device extends DataClass implements Insertable<Device> {
  final int id;
  final String userId;
  final String pushToken;
  final String platform;
  final String? deviceModel;
  final int isActive;
  final DateTime registeredAt;
  final DateTime lastSeenAt;
  const Device({
    required this.id,
    required this.userId,
    required this.pushToken,
    required this.platform,
    this.deviceModel,
    required this.isActive,
    required this.registeredAt,
    required this.lastSeenAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['user_id'] = Variable<String>(userId);
    map['push_token'] = Variable<String>(pushToken);
    map['platform'] = Variable<String>(platform);
    if (!nullToAbsent || deviceModel != null) {
      map['device_model'] = Variable<String>(deviceModel);
    }
    map['is_active'] = Variable<int>(isActive);
    map['registered_at'] = Variable<DateTime>(registeredAt);
    map['last_seen_at'] = Variable<DateTime>(lastSeenAt);
    return map;
  }

  DevicesCompanion toCompanion(bool nullToAbsent) {
    return DevicesCompanion(
      id: Value(id),
      userId: Value(userId),
      pushToken: Value(pushToken),
      platform: Value(platform),
      deviceModel: deviceModel == null && nullToAbsent
          ? const Value.absent()
          : Value(deviceModel),
      isActive: Value(isActive),
      registeredAt: Value(registeredAt),
      lastSeenAt: Value(lastSeenAt),
    );
  }

  factory Device.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return Device(
      id: serializer.fromJson<int>(json['id']),
      userId: serializer.fromJson<String>(json['userId']),
      pushToken: serializer.fromJson<String>(json['pushToken']),
      platform: serializer.fromJson<String>(json['platform']),
      deviceModel: serializer.fromJson<String?>(json['deviceModel']),
      isActive: serializer.fromJson<int>(json['isActive']),
      registeredAt: serializer.fromJson<DateTime>(json['registeredAt']),
      lastSeenAt: serializer.fromJson<DateTime>(json['lastSeenAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'userId': serializer.toJson<String>(userId),
      'pushToken': serializer.toJson<String>(pushToken),
      'platform': serializer.toJson<String>(platform),
      'deviceModel': serializer.toJson<String?>(deviceModel),
      'isActive': serializer.toJson<int>(isActive),
      'registeredAt': serializer.toJson<DateTime>(registeredAt),
      'lastSeenAt': serializer.toJson<DateTime>(lastSeenAt),
    };
  }

  Device copyWith({
    int? id,
    String? userId,
    String? pushToken,
    String? platform,
    Value<String?> deviceModel = const Value.absent(),
    int? isActive,
    DateTime? registeredAt,
    DateTime? lastSeenAt,
  }) => Device(
    id: id ?? this.id,
    userId: userId ?? this.userId,
    pushToken: pushToken ?? this.pushToken,
    platform: platform ?? this.platform,
    deviceModel: deviceModel.present ? deviceModel.value : this.deviceModel,
    isActive: isActive ?? this.isActive,
    registeredAt: registeredAt ?? this.registeredAt,
    lastSeenAt: lastSeenAt ?? this.lastSeenAt,
  );
  Device copyWithCompanion(DevicesCompanion data) {
    return Device(
      id: data.id.present ? data.id.value : this.id,
      userId: data.userId.present ? data.userId.value : this.userId,
      pushToken: data.pushToken.present ? data.pushToken.value : this.pushToken,
      platform: data.platform.present ? data.platform.value : this.platform,
      deviceModel: data.deviceModel.present
          ? data.deviceModel.value
          : this.deviceModel,
      isActive: data.isActive.present ? data.isActive.value : this.isActive,
      registeredAt: data.registeredAt.present
          ? data.registeredAt.value
          : this.registeredAt,
      lastSeenAt: data.lastSeenAt.present
          ? data.lastSeenAt.value
          : this.lastSeenAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('Device(')
          ..write('id: $id, ')
          ..write('userId: $userId, ')
          ..write('pushToken: $pushToken, ')
          ..write('platform: $platform, ')
          ..write('deviceModel: $deviceModel, ')
          ..write('isActive: $isActive, ')
          ..write('registeredAt: $registeredAt, ')
          ..write('lastSeenAt: $lastSeenAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    userId,
    pushToken,
    platform,
    deviceModel,
    isActive,
    registeredAt,
    lastSeenAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is Device &&
          other.id == this.id &&
          other.userId == this.userId &&
          other.pushToken == this.pushToken &&
          other.platform == this.platform &&
          other.deviceModel == this.deviceModel &&
          other.isActive == this.isActive &&
          other.registeredAt == this.registeredAt &&
          other.lastSeenAt == this.lastSeenAt);
}

class DevicesCompanion extends UpdateCompanion<Device> {
  final Value<int> id;
  final Value<String> userId;
  final Value<String> pushToken;
  final Value<String> platform;
  final Value<String?> deviceModel;
  final Value<int> isActive;
  final Value<DateTime> registeredAt;
  final Value<DateTime> lastSeenAt;
  const DevicesCompanion({
    this.id = const Value.absent(),
    this.userId = const Value.absent(),
    this.pushToken = const Value.absent(),
    this.platform = const Value.absent(),
    this.deviceModel = const Value.absent(),
    this.isActive = const Value.absent(),
    this.registeredAt = const Value.absent(),
    this.lastSeenAt = const Value.absent(),
  });
  DevicesCompanion.insert({
    this.id = const Value.absent(),
    this.userId = const Value.absent(),
    required String pushToken,
    required String platform,
    this.deviceModel = const Value.absent(),
    this.isActive = const Value.absent(),
    this.registeredAt = const Value.absent(),
    this.lastSeenAt = const Value.absent(),
  }) : pushToken = Value(pushToken),
       platform = Value(platform);
  static Insertable<Device> custom({
    Expression<int>? id,
    Expression<String>? userId,
    Expression<String>? pushToken,
    Expression<String>? platform,
    Expression<String>? deviceModel,
    Expression<int>? isActive,
    Expression<DateTime>? registeredAt,
    Expression<DateTime>? lastSeenAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (userId != null) 'user_id': userId,
      if (pushToken != null) 'push_token': pushToken,
      if (platform != null) 'platform': platform,
      if (deviceModel != null) 'device_model': deviceModel,
      if (isActive != null) 'is_active': isActive,
      if (registeredAt != null) 'registered_at': registeredAt,
      if (lastSeenAt != null) 'last_seen_at': lastSeenAt,
    });
  }

  DevicesCompanion copyWith({
    Value<int>? id,
    Value<String>? userId,
    Value<String>? pushToken,
    Value<String>? platform,
    Value<String?>? deviceModel,
    Value<int>? isActive,
    Value<DateTime>? registeredAt,
    Value<DateTime>? lastSeenAt,
  }) {
    return DevicesCompanion(
      id: id ?? this.id,
      userId: userId ?? this.userId,
      pushToken: pushToken ?? this.pushToken,
      platform: platform ?? this.platform,
      deviceModel: deviceModel ?? this.deviceModel,
      isActive: isActive ?? this.isActive,
      registeredAt: registeredAt ?? this.registeredAt,
      lastSeenAt: lastSeenAt ?? this.lastSeenAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (userId.present) {
      map['user_id'] = Variable<String>(userId.value);
    }
    if (pushToken.present) {
      map['push_token'] = Variable<String>(pushToken.value);
    }
    if (platform.present) {
      map['platform'] = Variable<String>(platform.value);
    }
    if (deviceModel.present) {
      map['device_model'] = Variable<String>(deviceModel.value);
    }
    if (isActive.present) {
      map['is_active'] = Variable<int>(isActive.value);
    }
    if (registeredAt.present) {
      map['registered_at'] = Variable<DateTime>(registeredAt.value);
    }
    if (lastSeenAt.present) {
      map['last_seen_at'] = Variable<DateTime>(lastSeenAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('DevicesCompanion(')
          ..write('id: $id, ')
          ..write('userId: $userId, ')
          ..write('pushToken: $pushToken, ')
          ..write('platform: $platform, ')
          ..write('deviceModel: $deviceModel, ')
          ..write('isActive: $isActive, ')
          ..write('registeredAt: $registeredAt, ')
          ..write('lastSeenAt: $lastSeenAt')
          ..write(')'))
        .toString();
  }
}

class $SystemNotificationsTable extends SystemNotifications
    with TableInfo<$SystemNotificationsTable, SystemNotification> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $SystemNotificationsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _deviceIdMeta = const VerificationMeta(
    'deviceId',
  );
  @override
  late final GeneratedColumn<int> deviceId = GeneratedColumn<int>(
    'device_id',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _titleMeta = const VerificationMeta('title');
  @override
  late final GeneratedColumn<String> title = GeneratedColumn<String>(
    'title',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _bodyMeta = const VerificationMeta('body');
  @override
  late final GeneratedColumn<String> body = GeneratedColumn<String>(
    'body',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _deepLinkMeta = const VerificationMeta(
    'deepLink',
  );
  @override
  late final GeneratedColumn<String> deepLink = GeneratedColumn<String>(
    'deep_link',
    aliasedName,
    true,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _statusMeta = const VerificationMeta('status');
  @override
  late final GeneratedColumn<String> status = GeneratedColumn<String>(
    'status',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('PENDING'),
  );
  static const VerificationMeta _sentAtMeta = const VerificationMeta('sentAt');
  @override
  late final GeneratedColumn<DateTime> sentAt = GeneratedColumn<DateTime>(
    'sent_at',
    aliasedName,
    true,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _createdAtMeta = const VerificationMeta(
    'createdAt',
  );
  @override
  late final GeneratedColumn<DateTime> createdAt = GeneratedColumn<DateTime>(
    'created_at',
    aliasedName,
    false,
    type: DriftSqlType.dateTime,
    requiredDuringInsert: false,
    defaultValue: currentDateAndTime,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    deviceId,
    title,
    body,
    deepLink,
    status,
    sentAt,
    createdAt,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'system_notifications';
  @override
  VerificationContext validateIntegrity(
    Insertable<SystemNotification> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('device_id')) {
      context.handle(
        _deviceIdMeta,
        deviceId.isAcceptableOrUnknown(data['device_id']!, _deviceIdMeta),
      );
    } else if (isInserting) {
      context.missing(_deviceIdMeta);
    }
    if (data.containsKey('title')) {
      context.handle(
        _titleMeta,
        title.isAcceptableOrUnknown(data['title']!, _titleMeta),
      );
    } else if (isInserting) {
      context.missing(_titleMeta);
    }
    if (data.containsKey('body')) {
      context.handle(
        _bodyMeta,
        body.isAcceptableOrUnknown(data['body']!, _bodyMeta),
      );
    } else if (isInserting) {
      context.missing(_bodyMeta);
    }
    if (data.containsKey('deep_link')) {
      context.handle(
        _deepLinkMeta,
        deepLink.isAcceptableOrUnknown(data['deep_link']!, _deepLinkMeta),
      );
    }
    if (data.containsKey('status')) {
      context.handle(
        _statusMeta,
        status.isAcceptableOrUnknown(data['status']!, _statusMeta),
      );
    }
    if (data.containsKey('sent_at')) {
      context.handle(
        _sentAtMeta,
        sentAt.isAcceptableOrUnknown(data['sent_at']!, _sentAtMeta),
      );
    }
    if (data.containsKey('created_at')) {
      context.handle(
        _createdAtMeta,
        createdAt.isAcceptableOrUnknown(data['created_at']!, _createdAtMeta),
      );
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  SystemNotification map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return SystemNotification(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      deviceId: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}device_id'],
      )!,
      title: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}title'],
      )!,
      body: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}body'],
      )!,
      deepLink: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}deep_link'],
      ),
      status: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}status'],
      )!,
      sentAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}sent_at'],
      ),
      createdAt: attachedDatabase.typeMapping.read(
        DriftSqlType.dateTime,
        data['${effectivePrefix}created_at'],
      )!,
    );
  }

  @override
  $SystemNotificationsTable createAlias(String alias) {
    return $SystemNotificationsTable(attachedDatabase, alias);
  }
}

class SystemNotification extends DataClass
    implements Insertable<SystemNotification> {
  final int id;
  final int deviceId;
  final String title;
  final String body;
  final String? deepLink;
  final String status;
  final DateTime? sentAt;
  final DateTime createdAt;
  const SystemNotification({
    required this.id,
    required this.deviceId,
    required this.title,
    required this.body,
    this.deepLink,
    required this.status,
    this.sentAt,
    required this.createdAt,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['device_id'] = Variable<int>(deviceId);
    map['title'] = Variable<String>(title);
    map['body'] = Variable<String>(body);
    if (!nullToAbsent || deepLink != null) {
      map['deep_link'] = Variable<String>(deepLink);
    }
    map['status'] = Variable<String>(status);
    if (!nullToAbsent || sentAt != null) {
      map['sent_at'] = Variable<DateTime>(sentAt);
    }
    map['created_at'] = Variable<DateTime>(createdAt);
    return map;
  }

  SystemNotificationsCompanion toCompanion(bool nullToAbsent) {
    return SystemNotificationsCompanion(
      id: Value(id),
      deviceId: Value(deviceId),
      title: Value(title),
      body: Value(body),
      deepLink: deepLink == null && nullToAbsent
          ? const Value.absent()
          : Value(deepLink),
      status: Value(status),
      sentAt: sentAt == null && nullToAbsent
          ? const Value.absent()
          : Value(sentAt),
      createdAt: Value(createdAt),
    );
  }

  factory SystemNotification.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return SystemNotification(
      id: serializer.fromJson<int>(json['id']),
      deviceId: serializer.fromJson<int>(json['deviceId']),
      title: serializer.fromJson<String>(json['title']),
      body: serializer.fromJson<String>(json['body']),
      deepLink: serializer.fromJson<String?>(json['deepLink']),
      status: serializer.fromJson<String>(json['status']),
      sentAt: serializer.fromJson<DateTime?>(json['sentAt']),
      createdAt: serializer.fromJson<DateTime>(json['createdAt']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'deviceId': serializer.toJson<int>(deviceId),
      'title': serializer.toJson<String>(title),
      'body': serializer.toJson<String>(body),
      'deepLink': serializer.toJson<String?>(deepLink),
      'status': serializer.toJson<String>(status),
      'sentAt': serializer.toJson<DateTime?>(sentAt),
      'createdAt': serializer.toJson<DateTime>(createdAt),
    };
  }

  SystemNotification copyWith({
    int? id,
    int? deviceId,
    String? title,
    String? body,
    Value<String?> deepLink = const Value.absent(),
    String? status,
    Value<DateTime?> sentAt = const Value.absent(),
    DateTime? createdAt,
  }) => SystemNotification(
    id: id ?? this.id,
    deviceId: deviceId ?? this.deviceId,
    title: title ?? this.title,
    body: body ?? this.body,
    deepLink: deepLink.present ? deepLink.value : this.deepLink,
    status: status ?? this.status,
    sentAt: sentAt.present ? sentAt.value : this.sentAt,
    createdAt: createdAt ?? this.createdAt,
  );
  SystemNotification copyWithCompanion(SystemNotificationsCompanion data) {
    return SystemNotification(
      id: data.id.present ? data.id.value : this.id,
      deviceId: data.deviceId.present ? data.deviceId.value : this.deviceId,
      title: data.title.present ? data.title.value : this.title,
      body: data.body.present ? data.body.value : this.body,
      deepLink: data.deepLink.present ? data.deepLink.value : this.deepLink,
      status: data.status.present ? data.status.value : this.status,
      sentAt: data.sentAt.present ? data.sentAt.value : this.sentAt,
      createdAt: data.createdAt.present ? data.createdAt.value : this.createdAt,
    );
  }

  @override
  String toString() {
    return (StringBuffer('SystemNotification(')
          ..write('id: $id, ')
          ..write('deviceId: $deviceId, ')
          ..write('title: $title, ')
          ..write('body: $body, ')
          ..write('deepLink: $deepLink, ')
          ..write('status: $status, ')
          ..write('sentAt: $sentAt, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    deviceId,
    title,
    body,
    deepLink,
    status,
    sentAt,
    createdAt,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is SystemNotification &&
          other.id == this.id &&
          other.deviceId == this.deviceId &&
          other.title == this.title &&
          other.body == this.body &&
          other.deepLink == this.deepLink &&
          other.status == this.status &&
          other.sentAt == this.sentAt &&
          other.createdAt == this.createdAt);
}

class SystemNotificationsCompanion extends UpdateCompanion<SystemNotification> {
  final Value<int> id;
  final Value<int> deviceId;
  final Value<String> title;
  final Value<String> body;
  final Value<String?> deepLink;
  final Value<String> status;
  final Value<DateTime?> sentAt;
  final Value<DateTime> createdAt;
  const SystemNotificationsCompanion({
    this.id = const Value.absent(),
    this.deviceId = const Value.absent(),
    this.title = const Value.absent(),
    this.body = const Value.absent(),
    this.deepLink = const Value.absent(),
    this.status = const Value.absent(),
    this.sentAt = const Value.absent(),
    this.createdAt = const Value.absent(),
  });
  SystemNotificationsCompanion.insert({
    this.id = const Value.absent(),
    required int deviceId,
    required String title,
    required String body,
    this.deepLink = const Value.absent(),
    this.status = const Value.absent(),
    this.sentAt = const Value.absent(),
    this.createdAt = const Value.absent(),
  }) : deviceId = Value(deviceId),
       title = Value(title),
       body = Value(body);
  static Insertable<SystemNotification> custom({
    Expression<int>? id,
    Expression<int>? deviceId,
    Expression<String>? title,
    Expression<String>? body,
    Expression<String>? deepLink,
    Expression<String>? status,
    Expression<DateTime>? sentAt,
    Expression<DateTime>? createdAt,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (deviceId != null) 'device_id': deviceId,
      if (title != null) 'title': title,
      if (body != null) 'body': body,
      if (deepLink != null) 'deep_link': deepLink,
      if (status != null) 'status': status,
      if (sentAt != null) 'sent_at': sentAt,
      if (createdAt != null) 'created_at': createdAt,
    });
  }

  SystemNotificationsCompanion copyWith({
    Value<int>? id,
    Value<int>? deviceId,
    Value<String>? title,
    Value<String>? body,
    Value<String?>? deepLink,
    Value<String>? status,
    Value<DateTime?>? sentAt,
    Value<DateTime>? createdAt,
  }) {
    return SystemNotificationsCompanion(
      id: id ?? this.id,
      deviceId: deviceId ?? this.deviceId,
      title: title ?? this.title,
      body: body ?? this.body,
      deepLink: deepLink ?? this.deepLink,
      status: status ?? this.status,
      sentAt: sentAt ?? this.sentAt,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (deviceId.present) {
      map['device_id'] = Variable<int>(deviceId.value);
    }
    if (title.present) {
      map['title'] = Variable<String>(title.value);
    }
    if (body.present) {
      map['body'] = Variable<String>(body.value);
    }
    if (deepLink.present) {
      map['deep_link'] = Variable<String>(deepLink.value);
    }
    if (status.present) {
      map['status'] = Variable<String>(status.value);
    }
    if (sentAt.present) {
      map['sent_at'] = Variable<DateTime>(sentAt.value);
    }
    if (createdAt.present) {
      map['created_at'] = Variable<DateTime>(createdAt.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('SystemNotificationsCompanion(')
          ..write('id: $id, ')
          ..write('deviceId: $deviceId, ')
          ..write('title: $title, ')
          ..write('body: $body, ')
          ..write('deepLink: $deepLink, ')
          ..write('status: $status, ')
          ..write('sentAt: $sentAt, ')
          ..write('createdAt: $createdAt')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $ConversationsTable conversations = $ConversationsTable(this);
  late final $ConversationMemoriesTable conversationMemories =
      $ConversationMemoriesTable(this);
  late final $ConversationEventsTable conversationEvents =
      $ConversationEventsTable(this);
  late final $MissionSnapshotsTable missionSnapshots = $MissionSnapshotsTable(
    this,
  );
  late final $DevicesTable devices = $DevicesTable(this);
  late final $SystemNotificationsTable systemNotifications =
      $SystemNotificationsTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    conversations,
    conversationMemories,
    conversationEvents,
    missionSnapshots,
    devices,
    systemNotifications,
  ];
}

typedef $$ConversationsTableCreateCompanionBuilder =
    ConversationsCompanion Function({
      Value<int> id,
      required int workspaceId,
      required String title,
      Value<String?> summary,
      Value<String?> goal,
      Value<String?> systemPrompt,
      Value<String> activeModel,
      Value<double> temperature,
      Value<DateTime> createdAt,
      Value<DateTime> updatedAt,
    });
typedef $$ConversationsTableUpdateCompanionBuilder =
    ConversationsCompanion Function({
      Value<int> id,
      Value<int> workspaceId,
      Value<String> title,
      Value<String?> summary,
      Value<String?> goal,
      Value<String?> systemPrompt,
      Value<String> activeModel,
      Value<double> temperature,
      Value<DateTime> createdAt,
      Value<DateTime> updatedAt,
    });

class $$ConversationsTableFilterComposer
    extends Composer<_$AppDatabase, $ConversationsTable> {
  $$ConversationsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get workspaceId => $composableBuilder(
    column: $table.workspaceId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get summary => $composableBuilder(
    column: $table.summary,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get goal => $composableBuilder(
    column: $table.goal,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get systemPrompt => $composableBuilder(
    column: $table.systemPrompt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get activeModel => $composableBuilder(
    column: $table.activeModel,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get temperature => $composableBuilder(
    column: $table.temperature,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ConversationsTableOrderingComposer
    extends Composer<_$AppDatabase, $ConversationsTable> {
  $$ConversationsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get workspaceId => $composableBuilder(
    column: $table.workspaceId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get summary => $composableBuilder(
    column: $table.summary,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get goal => $composableBuilder(
    column: $table.goal,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get systemPrompt => $composableBuilder(
    column: $table.systemPrompt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get activeModel => $composableBuilder(
    column: $table.activeModel,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get temperature => $composableBuilder(
    column: $table.temperature,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ConversationsTableAnnotationComposer
    extends Composer<_$AppDatabase, $ConversationsTable> {
  $$ConversationsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get workspaceId => $composableBuilder(
    column: $table.workspaceId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get summary =>
      $composableBuilder(column: $table.summary, builder: (column) => column);

  GeneratedColumn<String> get goal =>
      $composableBuilder(column: $table.goal, builder: (column) => column);

  GeneratedColumn<String> get systemPrompt => $composableBuilder(
    column: $table.systemPrompt,
    builder: (column) => column,
  );

  GeneratedColumn<String> get activeModel => $composableBuilder(
    column: $table.activeModel,
    builder: (column) => column,
  );

  GeneratedColumn<double> get temperature => $composableBuilder(
    column: $table.temperature,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$ConversationsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ConversationsTable,
          Conversation,
          $$ConversationsTableFilterComposer,
          $$ConversationsTableOrderingComposer,
          $$ConversationsTableAnnotationComposer,
          $$ConversationsTableCreateCompanionBuilder,
          $$ConversationsTableUpdateCompanionBuilder,
          (
            Conversation,
            BaseReferences<_$AppDatabase, $ConversationsTable, Conversation>,
          ),
          Conversation,
          PrefetchHooks Function()
        > {
  $$ConversationsTableTableManager(_$AppDatabase db, $ConversationsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ConversationsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ConversationsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ConversationsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> workspaceId = const Value.absent(),
                Value<String> title = const Value.absent(),
                Value<String?> summary = const Value.absent(),
                Value<String?> goal = const Value.absent(),
                Value<String?> systemPrompt = const Value.absent(),
                Value<String> activeModel = const Value.absent(),
                Value<double> temperature = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
              }) => ConversationsCompanion(
                id: id,
                workspaceId: workspaceId,
                title: title,
                summary: summary,
                goal: goal,
                systemPrompt: systemPrompt,
                activeModel: activeModel,
                temperature: temperature,
                createdAt: createdAt,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int workspaceId,
                required String title,
                Value<String?> summary = const Value.absent(),
                Value<String?> goal = const Value.absent(),
                Value<String?> systemPrompt = const Value.absent(),
                Value<String> activeModel = const Value.absent(),
                Value<double> temperature = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
              }) => ConversationsCompanion.insert(
                id: id,
                workspaceId: workspaceId,
                title: title,
                summary: summary,
                goal: goal,
                systemPrompt: systemPrompt,
                activeModel: activeModel,
                temperature: temperature,
                createdAt: createdAt,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ConversationsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ConversationsTable,
      Conversation,
      $$ConversationsTableFilterComposer,
      $$ConversationsTableOrderingComposer,
      $$ConversationsTableAnnotationComposer,
      $$ConversationsTableCreateCompanionBuilder,
      $$ConversationsTableUpdateCompanionBuilder,
      (
        Conversation,
        BaseReferences<_$AppDatabase, $ConversationsTable, Conversation>,
      ),
      Conversation,
      PrefetchHooks Function()
    >;
typedef $$ConversationMemoriesTableCreateCompanionBuilder =
    ConversationMemoriesCompanion Function({
      Value<int> id,
      required int conversationId,
      required String memoryKey,
      Value<String?> memoryValue,
      Value<DateTime> updatedAt,
    });
typedef $$ConversationMemoriesTableUpdateCompanionBuilder =
    ConversationMemoriesCompanion Function({
      Value<int> id,
      Value<int> conversationId,
      Value<String> memoryKey,
      Value<String?> memoryValue,
      Value<DateTime> updatedAt,
    });

class $$ConversationMemoriesTableFilterComposer
    extends Composer<_$AppDatabase, $ConversationMemoriesTable> {
  $$ConversationMemoriesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get memoryKey => $composableBuilder(
    column: $table.memoryKey,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get memoryValue => $composableBuilder(
    column: $table.memoryValue,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ConversationMemoriesTableOrderingComposer
    extends Composer<_$AppDatabase, $ConversationMemoriesTable> {
  $$ConversationMemoriesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get memoryKey => $composableBuilder(
    column: $table.memoryKey,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get memoryValue => $composableBuilder(
    column: $table.memoryValue,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get updatedAt => $composableBuilder(
    column: $table.updatedAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ConversationMemoriesTableAnnotationComposer
    extends Composer<_$AppDatabase, $ConversationMemoriesTable> {
  $$ConversationMemoriesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get memoryKey =>
      $composableBuilder(column: $table.memoryKey, builder: (column) => column);

  GeneratedColumn<String> get memoryValue => $composableBuilder(
    column: $table.memoryValue,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get updatedAt =>
      $composableBuilder(column: $table.updatedAt, builder: (column) => column);
}

class $$ConversationMemoriesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ConversationMemoriesTable,
          ConversationMemory,
          $$ConversationMemoriesTableFilterComposer,
          $$ConversationMemoriesTableOrderingComposer,
          $$ConversationMemoriesTableAnnotationComposer,
          $$ConversationMemoriesTableCreateCompanionBuilder,
          $$ConversationMemoriesTableUpdateCompanionBuilder,
          (
            ConversationMemory,
            BaseReferences<
              _$AppDatabase,
              $ConversationMemoriesTable,
              ConversationMemory
            >,
          ),
          ConversationMemory,
          PrefetchHooks Function()
        > {
  $$ConversationMemoriesTableTableManager(
    _$AppDatabase db,
    $ConversationMemoriesTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ConversationMemoriesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ConversationMemoriesTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$ConversationMemoriesTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> conversationId = const Value.absent(),
                Value<String> memoryKey = const Value.absent(),
                Value<String?> memoryValue = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
              }) => ConversationMemoriesCompanion(
                id: id,
                conversationId: conversationId,
                memoryKey: memoryKey,
                memoryValue: memoryValue,
                updatedAt: updatedAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int conversationId,
                required String memoryKey,
                Value<String?> memoryValue = const Value.absent(),
                Value<DateTime> updatedAt = const Value.absent(),
              }) => ConversationMemoriesCompanion.insert(
                id: id,
                conversationId: conversationId,
                memoryKey: memoryKey,
                memoryValue: memoryValue,
                updatedAt: updatedAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ConversationMemoriesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ConversationMemoriesTable,
      ConversationMemory,
      $$ConversationMemoriesTableFilterComposer,
      $$ConversationMemoriesTableOrderingComposer,
      $$ConversationMemoriesTableAnnotationComposer,
      $$ConversationMemoriesTableCreateCompanionBuilder,
      $$ConversationMemoriesTableUpdateCompanionBuilder,
      (
        ConversationMemory,
        BaseReferences<
          _$AppDatabase,
          $ConversationMemoriesTable,
          ConversationMemory
        >,
      ),
      ConversationMemory,
      PrefetchHooks Function()
    >;
typedef $$ConversationEventsTableCreateCompanionBuilder =
    ConversationEventsCompanion Function({
      Value<int> id,
      Value<int?> parentEventId,
      required int conversationId,
      required int sequenceId,
      required String eventNamespace,
      required String eventType,
      required String payloadJson,
      Value<int?> missionId,
      Value<int> payloadSchemaVersion,
      Value<DateTime> createdAt,
    });
typedef $$ConversationEventsTableUpdateCompanionBuilder =
    ConversationEventsCompanion Function({
      Value<int> id,
      Value<int?> parentEventId,
      Value<int> conversationId,
      Value<int> sequenceId,
      Value<String> eventNamespace,
      Value<String> eventType,
      Value<String> payloadJson,
      Value<int?> missionId,
      Value<int> payloadSchemaVersion,
      Value<DateTime> createdAt,
    });

class $$ConversationEventsTableFilterComposer
    extends Composer<_$AppDatabase, $ConversationEventsTable> {
  $$ConversationEventsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get parentEventId => $composableBuilder(
    column: $table.parentEventId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get sequenceId => $composableBuilder(
    column: $table.sequenceId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get eventNamespace => $composableBuilder(
    column: $table.eventNamespace,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get eventType => $composableBuilder(
    column: $table.eventType,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get missionId => $composableBuilder(
    column: $table.missionId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get payloadSchemaVersion => $composableBuilder(
    column: $table.payloadSchemaVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ConversationEventsTableOrderingComposer
    extends Composer<_$AppDatabase, $ConversationEventsTable> {
  $$ConversationEventsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get parentEventId => $composableBuilder(
    column: $table.parentEventId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get sequenceId => $composableBuilder(
    column: $table.sequenceId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get eventNamespace => $composableBuilder(
    column: $table.eventNamespace,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get eventType => $composableBuilder(
    column: $table.eventType,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get missionId => $composableBuilder(
    column: $table.missionId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get payloadSchemaVersion => $composableBuilder(
    column: $table.payloadSchemaVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ConversationEventsTableAnnotationComposer
    extends Composer<_$AppDatabase, $ConversationEventsTable> {
  $$ConversationEventsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get parentEventId => $composableBuilder(
    column: $table.parentEventId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get conversationId => $composableBuilder(
    column: $table.conversationId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get sequenceId => $composableBuilder(
    column: $table.sequenceId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get eventNamespace => $composableBuilder(
    column: $table.eventNamespace,
    builder: (column) => column,
  );

  GeneratedColumn<String> get eventType =>
      $composableBuilder(column: $table.eventType, builder: (column) => column);

  GeneratedColumn<String> get payloadJson => $composableBuilder(
    column: $table.payloadJson,
    builder: (column) => column,
  );

  GeneratedColumn<int> get missionId =>
      $composableBuilder(column: $table.missionId, builder: (column) => column);

  GeneratedColumn<int> get payloadSchemaVersion => $composableBuilder(
    column: $table.payloadSchemaVersion,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$ConversationEventsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ConversationEventsTable,
          ConversationEvent,
          $$ConversationEventsTableFilterComposer,
          $$ConversationEventsTableOrderingComposer,
          $$ConversationEventsTableAnnotationComposer,
          $$ConversationEventsTableCreateCompanionBuilder,
          $$ConversationEventsTableUpdateCompanionBuilder,
          (
            ConversationEvent,
            BaseReferences<
              _$AppDatabase,
              $ConversationEventsTable,
              ConversationEvent
            >,
          ),
          ConversationEvent,
          PrefetchHooks Function()
        > {
  $$ConversationEventsTableTableManager(
    _$AppDatabase db,
    $ConversationEventsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ConversationEventsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ConversationEventsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ConversationEventsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int?> parentEventId = const Value.absent(),
                Value<int> conversationId = const Value.absent(),
                Value<int> sequenceId = const Value.absent(),
                Value<String> eventNamespace = const Value.absent(),
                Value<String> eventType = const Value.absent(),
                Value<String> payloadJson = const Value.absent(),
                Value<int?> missionId = const Value.absent(),
                Value<int> payloadSchemaVersion = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => ConversationEventsCompanion(
                id: id,
                parentEventId: parentEventId,
                conversationId: conversationId,
                sequenceId: sequenceId,
                eventNamespace: eventNamespace,
                eventType: eventType,
                payloadJson: payloadJson,
                missionId: missionId,
                payloadSchemaVersion: payloadSchemaVersion,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int?> parentEventId = const Value.absent(),
                required int conversationId,
                required int sequenceId,
                required String eventNamespace,
                required String eventType,
                required String payloadJson,
                Value<int?> missionId = const Value.absent(),
                Value<int> payloadSchemaVersion = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => ConversationEventsCompanion.insert(
                id: id,
                parentEventId: parentEventId,
                conversationId: conversationId,
                sequenceId: sequenceId,
                eventNamespace: eventNamespace,
                eventType: eventType,
                payloadJson: payloadJson,
                missionId: missionId,
                payloadSchemaVersion: payloadSchemaVersion,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ConversationEventsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ConversationEventsTable,
      ConversationEvent,
      $$ConversationEventsTableFilterComposer,
      $$ConversationEventsTableOrderingComposer,
      $$ConversationEventsTableAnnotationComposer,
      $$ConversationEventsTableCreateCompanionBuilder,
      $$ConversationEventsTableUpdateCompanionBuilder,
      (
        ConversationEvent,
        BaseReferences<
          _$AppDatabase,
          $ConversationEventsTable,
          ConversationEvent
        >,
      ),
      ConversationEvent,
      PrefetchHooks Function()
    >;
typedef $$MissionSnapshotsTableCreateCompanionBuilder =
    MissionSnapshotsCompanion Function({
      Value<int> missionId,
      required String status,
      Value<double> progress,
      Value<String?> latestThought,
      Value<String?> nextAction,
      Value<int> eta,
      Value<String> confidence,
      Value<int> tokenUsage,
      Value<double> estimatedCost,
      Value<DateTime> lastUpdated,
    });
typedef $$MissionSnapshotsTableUpdateCompanionBuilder =
    MissionSnapshotsCompanion Function({
      Value<int> missionId,
      Value<String> status,
      Value<double> progress,
      Value<String?> latestThought,
      Value<String?> nextAction,
      Value<int> eta,
      Value<String> confidence,
      Value<int> tokenUsage,
      Value<double> estimatedCost,
      Value<DateTime> lastUpdated,
    });

class $$MissionSnapshotsTableFilterComposer
    extends Composer<_$AppDatabase, $MissionSnapshotsTable> {
  $$MissionSnapshotsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get missionId => $composableBuilder(
    column: $table.missionId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get progress => $composableBuilder(
    column: $table.progress,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get latestThought => $composableBuilder(
    column: $table.latestThought,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get nextAction => $composableBuilder(
    column: $table.nextAction,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get eta => $composableBuilder(
    column: $table.eta,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get tokenUsage => $composableBuilder(
    column: $table.tokenUsage,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get estimatedCost => $composableBuilder(
    column: $table.estimatedCost,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastUpdated => $composableBuilder(
    column: $table.lastUpdated,
    builder: (column) => ColumnFilters(column),
  );
}

class $$MissionSnapshotsTableOrderingComposer
    extends Composer<_$AppDatabase, $MissionSnapshotsTable> {
  $$MissionSnapshotsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get missionId => $composableBuilder(
    column: $table.missionId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get progress => $composableBuilder(
    column: $table.progress,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get latestThought => $composableBuilder(
    column: $table.latestThought,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get nextAction => $composableBuilder(
    column: $table.nextAction,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get eta => $composableBuilder(
    column: $table.eta,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get tokenUsage => $composableBuilder(
    column: $table.tokenUsage,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get estimatedCost => $composableBuilder(
    column: $table.estimatedCost,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastUpdated => $composableBuilder(
    column: $table.lastUpdated,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$MissionSnapshotsTableAnnotationComposer
    extends Composer<_$AppDatabase, $MissionSnapshotsTable> {
  $$MissionSnapshotsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get missionId =>
      $composableBuilder(column: $table.missionId, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<double> get progress =>
      $composableBuilder(column: $table.progress, builder: (column) => column);

  GeneratedColumn<String> get latestThought => $composableBuilder(
    column: $table.latestThought,
    builder: (column) => column,
  );

  GeneratedColumn<String> get nextAction => $composableBuilder(
    column: $table.nextAction,
    builder: (column) => column,
  );

  GeneratedColumn<int> get eta =>
      $composableBuilder(column: $table.eta, builder: (column) => column);

  GeneratedColumn<String> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => column,
  );

  GeneratedColumn<int> get tokenUsage => $composableBuilder(
    column: $table.tokenUsage,
    builder: (column) => column,
  );

  GeneratedColumn<double> get estimatedCost => $composableBuilder(
    column: $table.estimatedCost,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get lastUpdated => $composableBuilder(
    column: $table.lastUpdated,
    builder: (column) => column,
  );
}

class $$MissionSnapshotsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $MissionSnapshotsTable,
          MissionSnapshot,
          $$MissionSnapshotsTableFilterComposer,
          $$MissionSnapshotsTableOrderingComposer,
          $$MissionSnapshotsTableAnnotationComposer,
          $$MissionSnapshotsTableCreateCompanionBuilder,
          $$MissionSnapshotsTableUpdateCompanionBuilder,
          (
            MissionSnapshot,
            BaseReferences<
              _$AppDatabase,
              $MissionSnapshotsTable,
              MissionSnapshot
            >,
          ),
          MissionSnapshot,
          PrefetchHooks Function()
        > {
  $$MissionSnapshotsTableTableManager(
    _$AppDatabase db,
    $MissionSnapshotsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$MissionSnapshotsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$MissionSnapshotsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$MissionSnapshotsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> missionId = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<double> progress = const Value.absent(),
                Value<String?> latestThought = const Value.absent(),
                Value<String?> nextAction = const Value.absent(),
                Value<int> eta = const Value.absent(),
                Value<String> confidence = const Value.absent(),
                Value<int> tokenUsage = const Value.absent(),
                Value<double> estimatedCost = const Value.absent(),
                Value<DateTime> lastUpdated = const Value.absent(),
              }) => MissionSnapshotsCompanion(
                missionId: missionId,
                status: status,
                progress: progress,
                latestThought: latestThought,
                nextAction: nextAction,
                eta: eta,
                confidence: confidence,
                tokenUsage: tokenUsage,
                estimatedCost: estimatedCost,
                lastUpdated: lastUpdated,
              ),
          createCompanionCallback:
              ({
                Value<int> missionId = const Value.absent(),
                required String status,
                Value<double> progress = const Value.absent(),
                Value<String?> latestThought = const Value.absent(),
                Value<String?> nextAction = const Value.absent(),
                Value<int> eta = const Value.absent(),
                Value<String> confidence = const Value.absent(),
                Value<int> tokenUsage = const Value.absent(),
                Value<double> estimatedCost = const Value.absent(),
                Value<DateTime> lastUpdated = const Value.absent(),
              }) => MissionSnapshotsCompanion.insert(
                missionId: missionId,
                status: status,
                progress: progress,
                latestThought: latestThought,
                nextAction: nextAction,
                eta: eta,
                confidence: confidence,
                tokenUsage: tokenUsage,
                estimatedCost: estimatedCost,
                lastUpdated: lastUpdated,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$MissionSnapshotsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $MissionSnapshotsTable,
      MissionSnapshot,
      $$MissionSnapshotsTableFilterComposer,
      $$MissionSnapshotsTableOrderingComposer,
      $$MissionSnapshotsTableAnnotationComposer,
      $$MissionSnapshotsTableCreateCompanionBuilder,
      $$MissionSnapshotsTableUpdateCompanionBuilder,
      (
        MissionSnapshot,
        BaseReferences<_$AppDatabase, $MissionSnapshotsTable, MissionSnapshot>,
      ),
      MissionSnapshot,
      PrefetchHooks Function()
    >;
typedef $$DevicesTableCreateCompanionBuilder =
    DevicesCompanion Function({
      Value<int> id,
      Value<String> userId,
      required String pushToken,
      required String platform,
      Value<String?> deviceModel,
      Value<int> isActive,
      Value<DateTime> registeredAt,
      Value<DateTime> lastSeenAt,
    });
typedef $$DevicesTableUpdateCompanionBuilder =
    DevicesCompanion Function({
      Value<int> id,
      Value<String> userId,
      Value<String> pushToken,
      Value<String> platform,
      Value<String?> deviceModel,
      Value<int> isActive,
      Value<DateTime> registeredAt,
      Value<DateTime> lastSeenAt,
    });

class $$DevicesTableFilterComposer
    extends Composer<_$AppDatabase, $DevicesTable> {
  $$DevicesTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get pushToken => $composableBuilder(
    column: $table.pushToken,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get platform => $composableBuilder(
    column: $table.platform,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get deviceModel => $composableBuilder(
    column: $table.deviceModel,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get isActive => $composableBuilder(
    column: $table.isActive,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get registeredAt => $composableBuilder(
    column: $table.registeredAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get lastSeenAt => $composableBuilder(
    column: $table.lastSeenAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$DevicesTableOrderingComposer
    extends Composer<_$AppDatabase, $DevicesTable> {
  $$DevicesTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get userId => $composableBuilder(
    column: $table.userId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get pushToken => $composableBuilder(
    column: $table.pushToken,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get platform => $composableBuilder(
    column: $table.platform,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get deviceModel => $composableBuilder(
    column: $table.deviceModel,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get isActive => $composableBuilder(
    column: $table.isActive,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get registeredAt => $composableBuilder(
    column: $table.registeredAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get lastSeenAt => $composableBuilder(
    column: $table.lastSeenAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$DevicesTableAnnotationComposer
    extends Composer<_$AppDatabase, $DevicesTable> {
  $$DevicesTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get userId =>
      $composableBuilder(column: $table.userId, builder: (column) => column);

  GeneratedColumn<String> get pushToken =>
      $composableBuilder(column: $table.pushToken, builder: (column) => column);

  GeneratedColumn<String> get platform =>
      $composableBuilder(column: $table.platform, builder: (column) => column);

  GeneratedColumn<String> get deviceModel => $composableBuilder(
    column: $table.deviceModel,
    builder: (column) => column,
  );

  GeneratedColumn<int> get isActive =>
      $composableBuilder(column: $table.isActive, builder: (column) => column);

  GeneratedColumn<DateTime> get registeredAt => $composableBuilder(
    column: $table.registeredAt,
    builder: (column) => column,
  );

  GeneratedColumn<DateTime> get lastSeenAt => $composableBuilder(
    column: $table.lastSeenAt,
    builder: (column) => column,
  );
}

class $$DevicesTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $DevicesTable,
          Device,
          $$DevicesTableFilterComposer,
          $$DevicesTableOrderingComposer,
          $$DevicesTableAnnotationComposer,
          $$DevicesTableCreateCompanionBuilder,
          $$DevicesTableUpdateCompanionBuilder,
          (Device, BaseReferences<_$AppDatabase, $DevicesTable, Device>),
          Device,
          PrefetchHooks Function()
        > {
  $$DevicesTableTableManager(_$AppDatabase db, $DevicesTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$DevicesTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$DevicesTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$DevicesTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> userId = const Value.absent(),
                Value<String> pushToken = const Value.absent(),
                Value<String> platform = const Value.absent(),
                Value<String?> deviceModel = const Value.absent(),
                Value<int> isActive = const Value.absent(),
                Value<DateTime> registeredAt = const Value.absent(),
                Value<DateTime> lastSeenAt = const Value.absent(),
              }) => DevicesCompanion(
                id: id,
                userId: userId,
                pushToken: pushToken,
                platform: platform,
                deviceModel: deviceModel,
                isActive: isActive,
                registeredAt: registeredAt,
                lastSeenAt: lastSeenAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> userId = const Value.absent(),
                required String pushToken,
                required String platform,
                Value<String?> deviceModel = const Value.absent(),
                Value<int> isActive = const Value.absent(),
                Value<DateTime> registeredAt = const Value.absent(),
                Value<DateTime> lastSeenAt = const Value.absent(),
              }) => DevicesCompanion.insert(
                id: id,
                userId: userId,
                pushToken: pushToken,
                platform: platform,
                deviceModel: deviceModel,
                isActive: isActive,
                registeredAt: registeredAt,
                lastSeenAt: lastSeenAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$DevicesTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $DevicesTable,
      Device,
      $$DevicesTableFilterComposer,
      $$DevicesTableOrderingComposer,
      $$DevicesTableAnnotationComposer,
      $$DevicesTableCreateCompanionBuilder,
      $$DevicesTableUpdateCompanionBuilder,
      (Device, BaseReferences<_$AppDatabase, $DevicesTable, Device>),
      Device,
      PrefetchHooks Function()
    >;
typedef $$SystemNotificationsTableCreateCompanionBuilder =
    SystemNotificationsCompanion Function({
      Value<int> id,
      required int deviceId,
      required String title,
      required String body,
      Value<String?> deepLink,
      Value<String> status,
      Value<DateTime?> sentAt,
      Value<DateTime> createdAt,
    });
typedef $$SystemNotificationsTableUpdateCompanionBuilder =
    SystemNotificationsCompanion Function({
      Value<int> id,
      Value<int> deviceId,
      Value<String> title,
      Value<String> body,
      Value<String?> deepLink,
      Value<String> status,
      Value<DateTime?> sentAt,
      Value<DateTime> createdAt,
    });

class $$SystemNotificationsTableFilterComposer
    extends Composer<_$AppDatabase, $SystemNotificationsTable> {
  $$SystemNotificationsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get deviceId => $composableBuilder(
    column: $table.deviceId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get body => $composableBuilder(
    column: $table.body,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get deepLink => $composableBuilder(
    column: $table.deepLink,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get sentAt => $composableBuilder(
    column: $table.sentAt,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnFilters(column),
  );
}

class $$SystemNotificationsTableOrderingComposer
    extends Composer<_$AppDatabase, $SystemNotificationsTable> {
  $$SystemNotificationsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get deviceId => $composableBuilder(
    column: $table.deviceId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get title => $composableBuilder(
    column: $table.title,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get body => $composableBuilder(
    column: $table.body,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get deepLink => $composableBuilder(
    column: $table.deepLink,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get status => $composableBuilder(
    column: $table.status,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get sentAt => $composableBuilder(
    column: $table.sentAt,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<DateTime> get createdAt => $composableBuilder(
    column: $table.createdAt,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$SystemNotificationsTableAnnotationComposer
    extends Composer<_$AppDatabase, $SystemNotificationsTable> {
  $$SystemNotificationsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<int> get deviceId =>
      $composableBuilder(column: $table.deviceId, builder: (column) => column);

  GeneratedColumn<String> get title =>
      $composableBuilder(column: $table.title, builder: (column) => column);

  GeneratedColumn<String> get body =>
      $composableBuilder(column: $table.body, builder: (column) => column);

  GeneratedColumn<String> get deepLink =>
      $composableBuilder(column: $table.deepLink, builder: (column) => column);

  GeneratedColumn<String> get status =>
      $composableBuilder(column: $table.status, builder: (column) => column);

  GeneratedColumn<DateTime> get sentAt =>
      $composableBuilder(column: $table.sentAt, builder: (column) => column);

  GeneratedColumn<DateTime> get createdAt =>
      $composableBuilder(column: $table.createdAt, builder: (column) => column);
}

class $$SystemNotificationsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $SystemNotificationsTable,
          SystemNotification,
          $$SystemNotificationsTableFilterComposer,
          $$SystemNotificationsTableOrderingComposer,
          $$SystemNotificationsTableAnnotationComposer,
          $$SystemNotificationsTableCreateCompanionBuilder,
          $$SystemNotificationsTableUpdateCompanionBuilder,
          (
            SystemNotification,
            BaseReferences<
              _$AppDatabase,
              $SystemNotificationsTable,
              SystemNotification
            >,
          ),
          SystemNotification,
          PrefetchHooks Function()
        > {
  $$SystemNotificationsTableTableManager(
    _$AppDatabase db,
    $SystemNotificationsTable table,
  ) : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$SystemNotificationsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$SystemNotificationsTableOrderingComposer(
                $db: db,
                $table: table,
              ),
          createComputedFieldComposer: () =>
              $$SystemNotificationsTableAnnotationComposer(
                $db: db,
                $table: table,
              ),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<int> deviceId = const Value.absent(),
                Value<String> title = const Value.absent(),
                Value<String> body = const Value.absent(),
                Value<String?> deepLink = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<DateTime?> sentAt = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => SystemNotificationsCompanion(
                id: id,
                deviceId: deviceId,
                title: title,
                body: body,
                deepLink: deepLink,
                status: status,
                sentAt: sentAt,
                createdAt: createdAt,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required int deviceId,
                required String title,
                required String body,
                Value<String?> deepLink = const Value.absent(),
                Value<String> status = const Value.absent(),
                Value<DateTime?> sentAt = const Value.absent(),
                Value<DateTime> createdAt = const Value.absent(),
              }) => SystemNotificationsCompanion.insert(
                id: id,
                deviceId: deviceId,
                title: title,
                body: body,
                deepLink: deepLink,
                status: status,
                sentAt: sentAt,
                createdAt: createdAt,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$SystemNotificationsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $SystemNotificationsTable,
      SystemNotification,
      $$SystemNotificationsTableFilterComposer,
      $$SystemNotificationsTableOrderingComposer,
      $$SystemNotificationsTableAnnotationComposer,
      $$SystemNotificationsTableCreateCompanionBuilder,
      $$SystemNotificationsTableUpdateCompanionBuilder,
      (
        SystemNotification,
        BaseReferences<
          _$AppDatabase,
          $SystemNotificationsTable,
          SystemNotification
        >,
      ),
      SystemNotification,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$ConversationsTableTableManager get conversations =>
      $$ConversationsTableTableManager(_db, _db.conversations);
  $$ConversationMemoriesTableTableManager get conversationMemories =>
      $$ConversationMemoriesTableTableManager(_db, _db.conversationMemories);
  $$ConversationEventsTableTableManager get conversationEvents =>
      $$ConversationEventsTableTableManager(_db, _db.conversationEvents);
  $$MissionSnapshotsTableTableManager get missionSnapshots =>
      $$MissionSnapshotsTableTableManager(_db, _db.missionSnapshots);
  $$DevicesTableTableManager get devices =>
      $$DevicesTableTableManager(_db, _db.devices);
  $$SystemNotificationsTableTableManager get systemNotifications =>
      $$SystemNotificationsTableTableManager(_db, _db.systemNotifications);
}
