import 'package:flutter/material.dart';

abstract class PluginComponentRenderer {
  Widget render(Map<String, dynamic> data, BuildContext context);
}

class HeaderComponentRenderer implements PluginComponentRenderer {
  @override
  Widget render(Map<String, dynamic> data, BuildContext context) {
    final text = data['text'] ?? 'Plugin Header';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(
        text,
        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.white),
      ),
    );
  }
}

class MetricRowComponentRenderer implements PluginComponentRenderer {
  @override
  Widget render(Map<String, dynamic> data, BuildContext context) {
    final label = data['label'] ?? '';
    final value = data['value'] ?? '';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white70)),
        ],
      ),
    );
  }
}

class StatusIndicatorComponentRenderer implements PluginComponentRenderer {
  @override
  Widget render(Map<String, dynamic> data, BuildContext context) {
    final state = data['state'] ?? 'SUCCESS';
    final text = data['text'] ?? '';
    final isSuccess = state == 'SUCCESS';

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 6),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: isSuccess ? const Color(0x1F10B981) : const Color(0x1FEF4444),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: isSuccess ? const Color(0xFF10B981) : const Color(0xFFEF4444), width: 0.5),
      ),
      child: Row(
        children: [
          Icon(
            isSuccess ? Icons.check_circle_outline : Icons.error_outline,
            color: isSuccess ? const Color(0xFF10B981) : const Color(0xFFEF4444),
            size: 14,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: isSuccess ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                fontSize: 11,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ButtonComponentRenderer implements PluginComponentRenderer {
  @override
  Widget render(Map<String, dynamic> data, BuildContext context) {
    final label = data['label'] ?? 'Action';
    final actionId = data['action_id'] ?? '';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF10B981),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
          ),
          onPressed: () {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Triggered Action: $actionId')),
            );
          },
          child: Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
        ),
      ),
    );
  }
}

class PluginUiRegistry {
  static final PluginUiRegistry _instance = PluginUiRegistry._internal();
  factory PluginUiRegistry() => _instance;

  final Map<String, PluginComponentRenderer> _renderers = {};

  PluginUiRegistry._internal() {
    register('HEADER', HeaderComponentRenderer());
    register('METRIC_ROW', MetricRowComponentRenderer());
    register('STATUS_INDICATOR', StatusIndicatorComponentRenderer());
    register('BUTTON', ButtonComponentRenderer());
  }

  void register(String type, PluginComponentRenderer renderer) {
    _renderers[type] = renderer;
  }

  Widget renderComponent(String type, Map<String, dynamic> data, BuildContext context) {
    final renderer = _renderers[type];
    if (renderer != null) {
      return renderer.render(data, context);
    }
    return const SizedBox.shrink();
  }
}

class PluginUiRenderer extends StatelessWidget {
  final Map<String, dynamic> payload;

  const PluginUiRenderer({super.key, required this.payload});

  @override
  Widget build(BuildContext context) {
    final title = payload['title'] ?? 'Plugin Widget';
    final components = payload['layout_components'] as List? ?? [];
    final registry = PluginUiRegistry();

    return Card(
      color: const Color(0xFF1C1C1C),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: Colors.white10),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.extension_outlined, color: Color(0xFF10B981), size: 16),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white70),
                ),
              ],
            ),
            const Divider(color: Colors.white10, height: 16),
            ...components.map((c) {
              final Map<String, dynamic> data = Map<String, dynamic>.from(c);
              final String type = data['type'] ?? '';
              return registry.renderComponent(type, data, context);
            }),
          ],
        ),
      ),
    );
  }
}
