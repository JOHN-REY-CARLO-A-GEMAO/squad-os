import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'chat_controller.dart';
import '../../../core/database/database.dart';
import '../../../core/plugins/plugin_ui_renderer.dart';

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _showHiddenSubEvents = false;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);
    final controller = ref.read(chatProvider.notifier);

    final topLevelEvents = state.events.where((e) => e.parentEventId == null).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        title: const Text('Squad OS Chat', style: TextStyle(fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () => _showCommandPalette(context),
          ),
        ],
      ),
      body: Column(
        children: [
          _buildContextChips(state, controller),

          const Divider(color: Colors.white10, height: 1),

          if (state.activeSnapshot != null && state.activeSnapshot!.status == 'IN_PROGRESS')
            _buildAISessionCard(state.activeSnapshot!),

          Expanded(
            child: RefreshIndicator(
              onRefresh: () => controller.loadTimeline(),
              child: state.isLoading
                  ? _buildLoadingSkeleton()
                  : topLevelEvents.isEmpty
                      ? _buildEmptyState()
                      : ListView.builder(
                          controller: _scrollController,
                          padding: const EdgeInsets.all(12),
                          itemCount: topLevelEvents.length,
                          itemBuilder: (context, index) {
                            final ev = topLevelEvents[index];
                            return _buildTimelineEventCard(ev, state.events);
                          },
                        ),
            ),
          ),

          _buildMessageInput(controller),
        ],
      ),
    );
  }

  Widget _buildContextChips(ChatState state, ChatController controller) {
    final branch = state.contextMemory['branch'] ?? 'feature/jwt';
    final framework = state.contextMemory['framework'] ?? 'Flutter';
    final env = state.contextMemory['environment'] ?? 'Supabase';

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _contextChip(context, '🌿 $branch', () => _showContextSheet(context, 'branch', controller)),
          _contextChip(context, '📱 $framework', () => _showContextSheet(context, 'framework', controller)),
          _contextChip(context, '☁️ $env', () => _showContextSheet(context, 'environment', controller)),
        ],
      ),
    );
  }

  Widget _contextChip(BuildContext context, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white10),
        ),
        child: Text(
          label,
          style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }

  Widget _buildAISessionCard(MissionSnapshot snapshot) {
    return Card(
      margin: const EdgeInsets.all(12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Color(0xFF10B981), width: 1.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10B981)),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Mission #${snapshot.missionId}: Executing',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0x3310B981),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${snapshot.confidence} CONFIDENCE',
                    style: const TextStyle(color: Color(0xFF10B981), fontSize: 10, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'ETA: ${snapshot.eta}s | Est. Cost: \$${snapshot.estimatedCost.toStringAsFixed(4)}',
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
                Text(
                  '${(snapshot.progress * 100).toInt()}%',
                  style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 12),
                ),
              ],
            ),
            const SizedBox(height: 6),
            LinearProgressIndicator(
              value: snapshot.progress,
              backgroundColor: Colors.white10,
              color: const Color(0xFF10B981),
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: 10),
            Text(
              'Latest Thought: "${snapshot.latestThought ?? 'Thinking...'}"',
              style: const TextStyle(fontStyle: FontStyle.italic, color: Colors.white70, fontSize: 12),
            ),
            const SizedBox(height: 6),
            Text(
              'Next Action: ${snapshot.nextAction ?? 'Preparing...'}',
              style: const TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimelineEventCard(ConversationEvent ev, List<ConversationEvent> allEvents) {
    final payload = json.decode(ev.payloadJson);

    if (ev.eventNamespace == 'PLUGIN' && ev.eventType == 'UI') {
      return PluginUiRenderer(payload: payload);
    }

    if (ev.eventNamespace == 'CHAT' && ev.eventType == 'MESSAGE') {
      final role = payload['role'];
      final content = payload['content'];
      final isUser = role == 'user';

      return Align(
        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isUser ? const Color(0xFF10B981) : const Color(0xFF1E1E1E),
            borderRadius: BorderRadius.circular(12),
          ),
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isUser ? 'You' : 'Assistant',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 11, color: isUser ? Colors.white70 : Colors.grey),
              ),
              const SizedBox(height: 4),
              Text(content, style: const TextStyle(color: Colors.white, fontSize: 14)),
            ],
          ),
        ),
      );
    }

    final subEvents = allEvents.where((child) => child.parentEventId == ev.id).toList();

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                ev.eventNamespace == 'ERROR' ? Icons.error_outline : Icons.smart_toy_outlined,
                color: ev.eventNamespace == 'ERROR' ? const Color(0xFFEF4444) : const Color(0xFF10B981),
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                ev.eventType == 'STARTED' ? 'Mission Started' : 'Execution Step',
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(payload['goal'] ?? payload['message'] ?? payload['error'] ?? '', style: const TextStyle(fontSize: 13, color: Colors.white70)),

          if (subEvents.isNotEmpty) ...[
            const SizedBox(height: 8),
            GestureDetector(
              onTap: () => setState(() => _showHiddenSubEvents = !_showHiddenSubEvents),
              child: Row(
                children: [
                  Text(
                    '${subEvents.length} detailed sub-events ${_showHiddenSubEvents ? 'hidden' : 'collapsed'}',
                    style: const TextStyle(color: Color(0xFF10B981), fontSize: 12, fontWeight: FontWeight.bold),
                  ),
                  Icon(
                    _showHiddenSubEvents ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                    color: const Color(0xFF10B981),
                    size: 16,
                  ),
                ],
              ),
            ),
            if (_showHiddenSubEvents)
              Padding(
                padding: const EdgeInsets.only(left: 12, top: 8),
                child: Column(
                  children: subEvents.map((subEv) {
                    final subPayload = json.decode(subEv.payloadJson);
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Row(
                        children: [
                          const Icon(Icons.subdirectory_arrow_right, size: 12, color: Colors.grey),
                          const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              subPayload['thought'] ?? subPayload['output'] ?? subPayload['error'] ?? '',
                              style: const TextStyle(fontSize: 11, color: Colors.grey),
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ),
          ],
        ],
      ),
    );
  }

  void _showContextSheet(BuildContext context, String key, ChatController controller) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E1E1E),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (context) {
        final items = key == 'branch'
            ? ['main', 'feature/jwt-refresh', 'feature/payment-sync', 'bugfix/login']
            : key == 'framework'
                ? ['Flutter', 'React Native', 'Kotlin', 'Swift']
                : ['Supabase Production', 'Staging', 'Local Docker Dev'];

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Select environmental $key',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const SizedBox(height: 12),
                ...items.map((val) => ListTile(
                      title: Text(val, style: const TextStyle(color: Colors.white70)),
                      onTap: () {
                        controller.updateContextField(key, val);
                        Navigator.pop(context);
                      },
                    )),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showCommandPalette(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        final controller = TextEditingController();
        final commands = [
          {'cmd': '/deploy', 'desc': 'Trigger CI/CD build and hot-reload.'},
          {'cmd': '/switch-workspace', 'desc': 'Select active operating worktree.'},
          {'cmd': '/create-mission', 'desc': 'Spawn a new coordinate agent squad.'},
          {'cmd': '/clear-cache', 'desc': 'Wipe Drift local database projection caches.'},
          {'cmd': '/reconnect', 'desc': 'Force immediate WebSocket stream handshake.'},
        ];

        return Dialog(
          backgroundColor: const Color(0xFF1A1A1A),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: controller,
                  decoration: const InputDecoration(
                    hintText: 'Search or fire global action... (Ctrl + K)',
                    prefixIcon: Icon(Icons.terminal, color: Color(0xFF10B981)),
                    border: InputBorder.none,
                  ),
                  style: const TextStyle(color: Colors.white),
                ),
                const Divider(color: Colors.white10),
                const SizedBox(height: 8),
                SizedBox(
                  height: 200,
                  child: ListView(
                    children: commands.map((c) => ListTile(
                          title: Text(c['cmd']!, style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold)),
                          subtitle: Text(c['desc']!, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                          onTap: () {
                            Navigator.pop(context);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text('Executed command: ${c['cmd']}')),
                            );
                          },
                        )).toList(),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildLoadingSkeleton() {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: 4,
      itemBuilder: (context, index) => Card(
        color: Colors.white12,
        child: Container(height: 80),
      ),
    );
  }

  Widget _buildEmptyState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.chat_bubble_outline, size: 48, color: Colors.grey),
          SizedBox(height: 12),
          Text('No messages yet. Send a goal to start!'),
        ],
      ),
    );
  }

  Widget _buildMessageInput(ChatController controller) {
    return Container(
      padding: const EdgeInsets.all(8),
      color: const Color(0xFF1E1E1E),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _messageController,
              decoration: const InputDecoration(
                hintText: 'Type goal description...',
                border: InputBorder.none,
              ),
              style: const TextStyle(color: Colors.white),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.send, color: Color(0xFF10B981)),
            onPressed: () {
              if (_messageController.text.trim().isNotEmpty) {
                controller.sendMessage(_messageController.text.trim());
                _messageController.clear();
              }
            },
          ),
        ],
      ),
    );
  }
}
