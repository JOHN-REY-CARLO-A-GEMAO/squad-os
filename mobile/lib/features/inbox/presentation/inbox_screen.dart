import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../chat/presentation/chat_controller.dart';
import '../../../core/database/database.dart';

class InboxScreen extends ConsumerStatefulWidget {
  const InboxScreen({super.key});

  @override
  ConsumerState<InboxScreen> createState() => _InboxScreenState();
}

class _InboxScreenState extends ConsumerState<InboxScreen> {
  String _selectedFilter = 'Needs Approval';
  final List<String> _filters = ['All', 'Needs Approval', 'Needs Attention', 'Warnings'];
  final TextEditingController _feedbackController = TextEditingController();
  bool _isDiffExpanded = false;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);
    final controller = ref.read(chatProvider.notifier);

    final inboxEvents = state.events.where((e) {
      if (_selectedFilter == 'All') {
        return e.eventNamespace == 'INBOX' || e.eventNamespace == 'ERROR';
      } else if (_selectedFilter == 'Needs Approval') {
        return e.eventNamespace == 'INBOX' && e.eventType == 'APPROVAL_REQUESTED';
      } else if (_selectedFilter == 'Needs Attention') {
        return e.eventNamespace == 'INBOX' && e.eventType == 'ATTENTION_REQUIRED';
      } else if (_selectedFilter == 'Warnings') {
        return e.eventNamespace == 'ERROR' || e.eventNamespace == 'WARNING';
      }
      return false;
    }).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        title: const Text('📥 AI INBOX', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
      ),
      body: Column(
        children: [
          _buildFilterBar(),

          const Divider(color: Colors.white10, height: 1),

          Expanded(
            child: RefreshIndicator(
              onRefresh: () => controller.loadTimeline(),
              child: inboxEvents.isEmpty
                  ? _buildEmptyInboxState()
                  : ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: inboxEvents.length,
                      itemBuilder: (context, index) {
                        final ev = inboxEvents[index];
                        return _buildInboxApprovalCard(ev, controller);
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar() {
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _filters.length,
        itemBuilder: (context, index) {
          final f = _filters[index];
          final isSelected = _selectedFilter == f;
          return GestureDetector(
            onTap: () {
              setState(() {
                _selectedFilter = f;
              });
            },
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 4),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
              decoration: BoxDecoration(
                color: isSelected ? const Color(0xFF10B981) : const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: isSelected ? Colors.transparent : Colors.white10),
              ),
              child: Center(
                child: Text(
                  f,
                  style: TextStyle(
                    color: isSelected ? Colors.white : Colors.grey,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildInboxApprovalCard(ConversationEvent ev, ChatController controller) {
    final payload = json.decode(ev.payloadJson);
    final approvalId = payload['approval_id'] ?? 1;
    final msg = payload['message'] ?? 'Confirm deletion of 4 outdated configurations.';

    const mockGitDiff = '''
--- config/secure/legacy_rsa.json
+++ config/secure/legacy_rsa.json (DELETED)
@@ -1,4 +1,0 @@
-{
-  "algorithm": "RSA-LEGACY",
-  "key_size": 1024,
-}
--- config/secure/temp_key.pem
+++ config/secure/temp_key.pem (DELETED)
@@ -1,3 +1,0 @@
------BEGIN RSA PRIVATE KEY-----
-MIICXAIBAAKBgQCs...
------END RSA PRIVATE KEY-----''';

    return Card(
      color: const Color(0xFF1A1A1A),
      margin: const EdgeInsets.symmetric(vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: const Color(0xFF10B981).withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Mission: #${ev.missionId ?? 91}',
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.grey),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0x2210B981),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'HIGH CONFIDENCE (91%)',
                    style: TextStyle(color: Color(0xFF10B981), fontSize: 9, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              '⚠️ ACTION REQUIRED',
              style: TextStyle(color: Color(0xFFF59E0B), fontWeight: FontWeight.bold, fontSize: 13, letterSpacing: 1.0),
            ),
            const SizedBox(height: 6),
            Text(
              msg,
              style: const TextStyle(fontSize: 14, color: Colors.white, fontWeight: FontWeight.w500),
            ),
            const SizedBox(height: 12),

            ExpansionTile(
              title: Text(
                '📂 View Proposed Deletion Diff (${ev.missionId == 91 ? '48 files' : '2 files'})',
                style: const TextStyle(color: Color(0xFF10B981), fontSize: 13, fontWeight: FontWeight.bold),
              ),
              trailing: Icon(
                _isDiffExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
                color: const Color(0xFF10B981),
              ),
              childrenPadding: const EdgeInsets.all(8),
              backgroundColor: const Color(0xFF111111),
              collapsedBackgroundColor: const Color(0xFF121212),
              onExpansionChanged: (expanded) {
                setState(() {
                  _isDiffExpanded = expanded;
                });
              },
              children: [
                _buildSyntacticGitDiff(mockGitDiff),
              ],
            ),

            const SizedBox(height: 16),

            TextField(
              controller: _feedbackController,
              decoration: InputDecoration(
                hintText: 'Optional instructions (e.g. Keep legacy_rsa.json)...',
                hintStyle: const TextStyle(fontSize: 12, color: Colors.grey),
                filled: true,
                fillColor: const Color(0xFF121212),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.mic, color: Color(0xFF10B981)),
                  onPressed: () {
                    setState(() {
                      _feedbackController.text = 'Approved. Please retain legacy configs inside workspace.';
                    });
                  },
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
              ),
              style: const TextStyle(fontSize: 13, color: Colors.white70),
            ),

            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    onPressed: () {
                      final notes = _feedbackController.text.trim();
                      controller.syncEngine.queueAction('INBOX.APPROVE', {
                        'approval_id': approvalId,
                        'notes': notes.isNotEmpty ? notes : 'Approved via mobile companion.',
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('✓ Sent Approval Command to Outbound Queue.')),
                      );
                    },
                    child: const Text('Approve Deletion', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFEF4444),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                    onPressed: () {
                      final notes = _feedbackController.text.trim();
                      controller.syncEngine.queueAction('INBOX.REJECT', {
                        'approval_id': approvalId,
                        'notes': notes.isNotEmpty ? notes : 'Rejected.',
                      });
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('❌ Sent Rejection Command to Outbound Queue.')),
                      );
                    },
                    child: const Text('Reject Deletion', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSyntacticGitDiff(String diffText) {
    final lines = diffText.split('\n');
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF0F0F0F),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: lines.map((line) {
          Color color = Colors.grey;
          Color bgColor = Colors.transparent;

          if (line.startsWith('+') && !line.startsWith('+++')) {
            color = const Color(0xFF10B981);
            bgColor = const Color(0x1F10B981);
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            color = const Color(0xFFEF4444);
            bgColor = const Color(0x1FEF4444);
          } else if (line.startsWith('@@')) {
            color = Colors.cyan;
          } else if (line.startsWith('---') || line.startsWith('+++')) {
            color = Colors.white70;
            bgColor = Colors.white12;
          }

          return Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 1.5),
            color: bgColor,
            child: Text(
              line,
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: 10.5,
                color: color,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildEmptyInboxState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.mark_email_read_outlined, size: 48, color: Colors.grey),
          SizedBox(height: 12),
          Text('All caught up! Inbox is clean.', style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }
}
