import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../chat/presentation/chat_controller.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final TextEditingController _serverController = TextEditingController(text: 'http://127.0.0.1:8000');
  bool _notificationsEnabled = true;

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);
    final controller = ref.read(chatProvider.notifier);

    final queueCount = controller.syncEngine.outboundQueue.length;
    final wsConnected = controller.webSocketClient.url.isNotEmpty;

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        title: const Text('⚙️ SETTINGS', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _sectionHeader('SERVER CONFIGURATION'),
          _buildServerConfigCard(),
          const SizedBox(height: 16),

          _sectionHeader('TRUSTED PAIRING HANDSHAKE'),
          _buildQRPairingCard(context),
          const SizedBox(height: 16),

          _sectionHeader('AUTHORIZED COMPANION DEVICES'),
          _buildDevicesRegistryCard(),
          const SizedBox(height: 16),

          _sectionHeader('BACKGROUND SYNC DIAGNOSTICS'),
          _buildDiagnosticsCard(queueCount, wsConnected),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, top: 4),
      child: Text(
        title,
        style: const TextStyle(
          color: Colors.grey,
          fontSize: 10,
          fontWeight: FontWeight.bold,
          letterSpacing: 1.5,
        ),
      ),
    );
  }

  Widget _buildServerConfigCard() {
    return Card(
      color: const Color(0xFF1E1E1E),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            TextField(
              controller: _serverController,
              decoration: const InputDecoration(
                labelText: 'Coordinator Host URL',
                labelStyle: TextStyle(color: Color(0xFF10B981), fontSize: 13),
                prefixIcon: Icon(Icons.dns, color: Color(0xFF10B981)),
                border: UnderlineInputBorder(),
              ),
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              title: const Text('Background Notifications', style: TextStyle(fontSize: 13)),
              value: _notificationsEnabled,
              activeColor: const Color(0xFF10B981),
              contentPadding: EdgeInsets.zero,
              onChanged: (val) {
                setState(() {
                  _notificationsEnabled = val;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQRPairingCard(BuildContext context) {
    return Card(
      color: const Color(0xFF1E1E1E),
      child: ListTile(
        leading: const Icon(Icons.qr_code_scanner, color: Color(0xFF10B981), size: 28),
        title: const Text('Scan Secure Pairing QR', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
        subtitle: const Text('Authorize this companion to run commands.', style: TextStyle(color: Colors.grey, fontSize: 11)),
        trailing: const Icon(Icons.chevron_right, color: Colors.grey),
        onTap: () => _triggerMockQRPairing(context),
      ),
    );
  }

  Widget _buildDevicesRegistryCard() {
    final devices = [
      {'name': 'iPhone 15 Pro (This device)', 'id': 'device_ios_01', 'active': true},
      {'name': 'Pixel 8 Lab Testing', 'id': 'device_android_99', 'active': false},
    ];

    return Card(
      color: const Color(0xFF1E1E1E),
      child: Column(
        children: devices.map((dev) => ListTile(
              leading: Icon(Icons.phone_android, color: dev['active'] as bool ? const Color(0xFF10B981) : Colors.grey),
              title: Text(dev['name'] as String, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              subtitle: Text('Fingerprint ID: ${dev['id']}', style: const TextStyle(color: Colors.grey, fontSize: 10)),
              trailing: IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.redAccent, size: 20),
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Revoked paired device: ${dev['name']}')),
                  );
                },
              ),
            )).toList(),
      ),
    );
  }

  Widget _buildDiagnosticsCard(int queueCount, bool wsConnected) {
    return Card(
      color: const Color(0xFF1E1E1E),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            _diagnosticRow('WSS Stream Handshake', wsConnected ? 'CONNECTED' : 'DISCONNECTED', wsConnected ? const Color(0xFF10B981) : Colors.redAccent),
            const Divider(color: Colors.white10),
            _diagnosticRow('Outbound Sync Queue', '$queueCount items pending', queueCount == 0 ? const Color(0xFF10B981) : const Color(0xFFF59E0B)),
            const Divider(color: Colors.white10),
            _diagnosticRow('Ping Latency Tracker', '14ms', const Color(0xFF10B981)),
            const Divider(color: Colors.white10),
            _diagnosticRow('Local Database Size', '142 KB', Colors.grey),
          ],
        ),
      ),
    );
  }

  Widget _diagnosticRow(String label, String val, Color valColor) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.white70)),
        Text(val, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: valColor)),
      ],
    );
  }

  void _triggerMockQRPairing(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        backgroundColor: const Color(0xFF121212),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.qr_code_scanner, color: Color(0xFF10B981), size: 48),
              const SizedBox(height: 16),
              const Text(
                'Handshake Camera Scanner',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: Colors.white),
              ),
              const SizedBox(height: 8),
              const Text(
                'Simulating scanner... Hovering over desktop pairing code.',
                style: TextStyle(fontSize: 11, color: Colors.grey),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              Container(
                width: 140,
                height: 140,
                decoration: BoxDecoration(
                  border: Border.all(color: const Color(0xFF10B981), width: 2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Center(
                  child: Icon(Icons.center_focus_strong, color: Color(0xFF10B981), size: 36),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF10B981),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () {
                  Navigator.pop(context);
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('✓ Secure Pairing Token acquired via asymmetric key handshake!')),
                  );
                },
                child: const Text('Acquire Token', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
