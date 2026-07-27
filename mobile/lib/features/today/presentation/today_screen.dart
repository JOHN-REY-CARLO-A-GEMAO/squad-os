import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../chat/presentation/chat_controller.dart';
import '../../../core/database/database.dart';

class TodayScreen extends ConsumerStatefulWidget {
  const TodayScreen({super.key});

  @override
  ConsumerState<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends ConsumerState<TodayScreen> {
  String _selectedWorkspace = 'Squad OS Workspace';
  final List<String> _workspaces = ['Squad OS Workspace', 'Marketing Worktree', 'Personal Lab'];

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);
    final controller = ref.read(chatProvider.notifier);

    final activeSnapshot = state.activeSnapshot;

    final pendingApprovals = state.events.where((e) {
      if (e.eventNamespace != 'INBOX' || e.eventType != 'APPROVAL_REQUESTED') return false;
      try {
        final payload = json.decode(e.payloadJson);
        return payload['status'] == 'PENDING';
      } catch (_) {
        return false;
      }
    }).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        title: const Text('📅 TODAY', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        actions: [
          _buildWorkspaceSelector(context),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await controller.loadTimeline();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (pendingApprovals.isNotEmpty) ...[
              _sectionHeader('🚨 CRITICAL ACTION REQUIRED', Colors.redAccent),
              ...pendingApprovals.map((appr) => _buildCriticalActionCard(context, appr)),
              const SizedBox(height: 16),
            ],

            _sectionHeader('⚡ ACTIVE SQUAD EXECUTION', const Color(0xFF10B981)),
            if (activeSnapshot != null && activeSnapshot.status == 'IN_PROGRESS')
              _buildActiveMissionSummaryCard(activeSnapshot)
            else
              _buildNoActiveMissionsCard(),
            const SizedBox(height: 16),

            _buildMetricRibbon(activeSnapshot),
            const SizedBox(height: 16),

            _sectionHeader('✅ RECENT MILESTONES', Colors.grey),
            _buildRecentMilestones(state.events),
          ],
        ),
      ),
    );
  }

  Widget _buildWorkspaceSelector(BuildContext context) {
    return PopupMenuButton<String>(
      icon: const Icon(Icons.lan_outlined, color: Color(0xFF10B981)),
      onSelected: (val) {
        setState(() {
          _selectedWorkspace = val;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Switched workspace to: $val')),
        );
      },
      itemBuilder: (context) => _workspaces
          .map((w) => PopupMenuItem<String>(
                value: w,
                child: Text(w, style: const TextStyle(fontSize: 13)),
              ))
          .toList(),
    );
  }

  Widget _sectionHeader(String title, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Text(
        title,
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  Widget _buildCriticalActionCard(BuildContext context, ConversationEvent ev) {
    final payload = json.decode(ev.payloadJson);
    final msg = payload['message'] ?? 'Requires verification.';

    return Card(
      color: const Color(0xFF1C1C1C),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: Colors.redAccent, width: 0.5),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'AI INBOX: Review requested',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.redAccent),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              msg,
              style: const TextStyle(fontSize: 12, color: Colors.white70),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(
                  onPressed: () => context.go('/inbox'),
                  child: const Text('Review changes', style: TextStyle(color: Color(0xFF10B981), fontSize: 12)),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActiveMissionSummaryCard(MissionSnapshot snapshot) {
    return Card(
      color: const Color(0xFF1E1E1E),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    'Mission #${snapshot.missionId}: Running',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                ),
                Text(
                  '${(snapshot.progress * 100).toInt()}%',
                  style: const TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 13),
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
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _metricMini('ETA remaining', '${snapshot.eta}s'),
                _metricMini('Session Cost', '\$${snapshot.estimatedCost.toStringAsFixed(4)}'),
                _metricMini('Current Agent', 'CoderAgent'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricMini(String label, String val) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 10)),
        const SizedBox(height: 2),
        Text(val, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildNoActiveMissionsCard() {
    return const Card(
      color: Color(0xFF1E1E1E),
      child: Padding(
        padding: EdgeInsets.symmetric(vertical: 24, horizontal: 16),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.check_circle_outline_rounded, color: Color(0xFF10B981), size: 36),
              SizedBox(height: 8),
              Text('All squads idle. Ready for your instructions!', style: TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMetricRibbon(MissionSnapshot? snapshot) {
    return Row(
      children: [
        Expanded(child: _metricSquare('USD COST', '\$${(snapshot?.estimatedCost ?? 0.00).toStringAsFixed(4)}', Icons.monetization_on_outlined)),
        const SizedBox(width: 12),
        Expanded(child: _metricSquare('TOKENS', '${snapshot?.tokenUsage ?? 0}', Icons.data_usage_outlined)),
      ],
    );
  }

  Widget _metricSquare(String label, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.white10),
      ),
      child: Row(
        children: [
          Icon(icon, color: const Color(0xFF10B981), size: 22),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(color: Colors.grey, fontSize: 10)),
              const SizedBox(height: 2),
              Text(value, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRecentMilestones(List<ConversationEvent> events) {
    final completed = events.where((e) {
      if (e.eventNamespace != 'MISSION' && e.eventNamespace != 'TOOL') return false;
      return e.eventType == 'COMPLETE' || e.eventType == 'JOURNAL';
    }).toList();

    if (completed.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: const Text('No milestones reached yet today.', style: TextStyle(color: Colors.grey, fontSize: 12)),
      );
    }

    return Column(
      children: completed.map((m) {
        final payload = json.decode(m.payloadJson);
        final title = payload['message'] ?? payload['output'] ?? 'Task finalized successfully.';
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(
            children: [
              const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 12, color: Colors.white70),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
