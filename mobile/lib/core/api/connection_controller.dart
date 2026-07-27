import 'dart:async';
import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:nsd/nsd.dart';
import 'api_client.dart';
import '../websocket/websocket_client.dart';
import '../../features/chat/presentation/chat_controller.dart';

class DiscoveredServer {
  final String ip;
  final int port;
  final String hostname;
  final String version;
  final String url;

  DiscoveredServer({
    required this.ip,
    required this.port,
    required this.hostname,
    required this.version,
    required this.url,
  });
}

class CompanionConnectionState {
  final String serverUrl;
  final String? accessToken;
  final String? refreshToken;
  final String? deviceId;
  final List<DiscoveredServer> discoveredServers;
  final bool isScanning;
  final bool isConnected;
  final String? pairingStatus; // 'PENDING', 'AWAITING_APPROVAL', 'APPROVED', 'FAILED'

  CompanionConnectionState({
    required this.serverUrl,
    this.accessToken,
    this.refreshToken,
    this.deviceId,
    required this.discoveredServers,
    this.isScanning = false,
    this.isConnected = false,
    this.pairingStatus,
  });

  CompanionConnectionState copyWith({
    String? serverUrl,
    String? accessToken,
    String? refreshToken,
    String? deviceId,
    List<DiscoveredServer>? discoveredServers,
    bool? isScanning,
    bool? isConnected,
    String? pairingStatus,
  }) {
    return CompanionConnectionState(
      serverUrl: serverUrl ?? this.serverUrl,
      accessToken: accessToken ?? this.accessToken,
      refreshToken: refreshToken ?? this.refreshToken,
      deviceId: deviceId ?? this.deviceId,
      discoveredServers: discoveredServers ?? this.discoveredServers,
      isScanning: isScanning ?? this.isScanning,
      isConnected: isConnected ?? this.isConnected,
      pairingStatus: pairingStatus ?? this.pairingStatus,
    );
  }
}

class ConnectionController extends StateNotifier<CompanionConnectionState> {
  final ApiClient apiClient;
  final WebSocketClient webSocketClient;
  final FlutterSecureStorage secureStorage;
  Discovery? _discovery;
  Timer? _pairingTimer;

  ConnectionController({
    required this.apiClient,
    required this.webSocketClient,
    FlutterSecureStorage? storage,
  })  : secureStorage = storage ?? const FlutterSecureStorage(),
        super(CompanionConnectionState(
          serverUrl: 'http://127.0.0.1:8000',
          discoveredServers: [],
        )) {
    autoConnect();
  }

  Future<void> autoConnect() async {
    final savedUrl = await secureStorage.read(key: 'server_url');
    final savedAccess = await secureStorage.read(key: 'access_token');
    final savedRefresh = await secureStorage.read(key: 'refresh_token');
    final savedDeviceId = await secureStorage.read(key: 'device_id');

    if (savedUrl != null && savedAccess != null) {
      apiClient.setBaseUrl(savedUrl);
      try {
        final handshakeRes = await apiClient.handshake();
        if (handshakeRes.isNotEmpty) {
          webSocketClient.updateUrl(savedUrl);
          state = state.copyWith(
            serverUrl: savedUrl,
            accessToken: savedAccess,
            refreshToken: savedRefresh,
            deviceId: savedDeviceId ?? 'companion_device',
            isConnected: true,
          );
          return;
        }
      } catch (_) {
        // Handshake failed, fallback to discovery
      }
    }

    // If auto-connect fails or no credentials exist, start discovery automatically
    startMdnsDiscovery();
  }

  Future<void> startMdnsDiscovery() async {
    if (state.isScanning) return;
    state = state.copyWith(isScanning: true, discoveredServers: []);

    try {
      _discovery = await startDiscovery('_squados._tcp');
      _discovery!.addListener(() {
        _onDiscoveryUpdated();
      });
    } catch (_) {
      state = state.copyWith(isScanning: false);
    }
  }

  Future<void> stopMdnsDiscovery() async {
    if (_discovery != null) {
      await stopDiscovery(_discovery!);
      _discovery = null;
    }
    state = state.copyWith(isScanning: false);
  }

  void _onDiscoveryUpdated() async {
    if (_discovery == null) return;

    final List<DiscoveredServer> servers = [];
    for (final service in _discovery!.services) {
      try {
        final ipBytes = service.txt?['ip'];
        final portBytes = service.txt?['api_port'];
        final hostnameBytes = service.txt?['hostname'];
        final versionBytes = service.txt?['server_version'];

        final ip = ipBytes != null ? utf8.decode(ipBytes) : (service.host ?? '127.0.0.1');
        final port = portBytes != null ? int.parse(utf8.decode(portBytes)) : (service.port ?? 8000);
        final hostname = hostnameBytes != null ? utf8.decode(hostnameBytes) : (service.name ?? 'unknown');
        final version = versionBytes != null ? utf8.decode(versionBytes) : '2.0.4';

        final url = 'http://$ip:$port';

        // Handshake server to validate
        try {
          final res = await apiClient.handshake(urlOverride: url);
          if (res.isNotEmpty) {
            servers.add(DiscoveredServer(
              ip: ip,
              port: port,
              hostname: hostname,
              version: version,
              url: url,
            ));
          }
        } catch (_) {}
      } catch (_) {}
    }

    state = state.copyWith(discoveredServers: List.from(servers));
  }

  Future<bool> connectToDiscoveredServer(DiscoveredServer server) async {
    apiClient.setBaseUrl(server.url);
    try {
      final res = await apiClient.handshake();
      if (res.isNotEmpty) {
        webSocketClient.updateUrl(server.url);
        await secureStorage.write(key: 'server_url', value: server.url);
        state = state.copyWith(
          serverUrl: server.url,
          isConnected: true,
        );
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<bool> manualConnect(String rawUrl) async {
    String formattedUrl = rawUrl.trim();
    if (!formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
      formattedUrl = 'http://$formattedUrl';
    }

    apiClient.setBaseUrl(formattedUrl);
    try {
      final res = await apiClient.handshake();
      if (res.isNotEmpty) {
        webSocketClient.updateUrl(formattedUrl);
        await secureStorage.write(key: 'server_url', value: formattedUrl);
        state = state.copyWith(
          serverUrl: formattedUrl,
          isConnected: true,
        );
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<void> pairWithServer({
    required String host,
    required int port,
    required String nonce,
    required int ticketVersion,
    String? deviceId,
  }) async {
    final devId = deviceId ?? 'companion_${DateTime.now().millisecondsSinceEpoch}';
    final targetUrl = 'http://$host:$port';
    apiClient.setBaseUrl(targetUrl);

    state = state.copyWith(
      serverUrl: targetUrl,
      deviceId: devId,
      pairingStatus: 'AWAITING_APPROVAL',
    );

    try {
      // 1. Send pairing request to backend
      final res = await apiClient.dio.post('/api/v1/pair/request', data: {
        'pairing_url': 'squados://pair?host=$host&port=$port&nonce=$nonce',
        'ticket_version': ticketVersion,
        'nonce': nonce,
        'device_id': devId,
      });

      if (res.statusCode == 200) {
        // 2. Poll for approved pairing token
        _pairingTimer?.cancel();
        int attempts = 0;
        _pairingTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
          attempts++;
          if (attempts > 40) { // 2 minutes timeout
            timer.cancel();
            state = state.copyWith(pairingStatus: 'FAILED');
            return;
          }

          try {
            final tokenRes = await apiClient.dio.get('/api/v1/pair/token', queryParameters: {
              'device_id': devId,
              'nonce': nonce,
            });

            if (tokenRes.statusCode == 200) {
              timer.cancel();
              final data = tokenRes.data;
              final access = data['access_token'];
              final refresh = data['refresh_token'];

              await secureStorage.write(key: 'server_url', value: targetUrl);
              await secureStorage.write(key: 'access_token', value: access);
              await secureStorage.write(key: 'refresh_token', value: refresh);
              await secureStorage.write(key: 'device_id', value: devId);

              webSocketClient.updateUrl(targetUrl);

              state = state.copyWith(
                serverUrl: targetUrl,
                accessToken: access,
                refreshToken: refresh,
                deviceId: devId,
                pairingStatus: 'APPROVED',
                isConnected: true,
              );
            }
          } on DioException catch (e) {
            if (e.response?.statusCode != 202) {
              timer.cancel();
              state = state.copyWith(pairingStatus: 'FAILED');
            }
          } catch (_) {
            timer.cancel();
            state = state.copyWith(pairingStatus: 'FAILED');
          }
        });
      } else {
        state = state.copyWith(pairingStatus: 'FAILED');
      }
    } catch (_) {
      state = state.copyWith(pairingStatus: 'FAILED');
    }
  }

  Future<void> parseAndPairFromUri(String pairingUri) async {
    try {
      final uri = Uri.parse(pairingUri.trim());
      final host = uri.queryParameters['host'];
      final portStr = uri.queryParameters['port'];
      final nonce = uri.queryParameters['nonce'];
      final ticketVersionStr = uri.queryParameters['ticket_version'];

      if (host != null && portStr != null && nonce != null) {
        final port = int.parse(portStr);
        final ticketVersion = int.tryParse(ticketVersionStr ?? '1') ?? 1;
        await pairWithServer(
          host: host,
          port: port,
          nonce: nonce,
          ticketVersion: ticketVersion,
        );
      } else {
        state = state.copyWith(pairingStatus: 'FAILED');
      }
    } catch (_) {
      state = state.copyWith(pairingStatus: 'FAILED');
    }
  }

  Future<void> disconnect() async {
    _pairingTimer?.cancel();
    await secureStorage.delete(key: 'server_url');
    await secureStorage.delete(key: 'access_token');
    await secureStorage.delete(key: 'refresh_token');
    state = state.copyWith(
      accessToken: null,
      refreshToken: null,
      isConnected: false,
      pairingStatus: null,
    );
  }

  @override
  void dispose() {
    _pairingTimer?.cancel();
    stopMdnsDiscovery();
    super.dispose();
  }
}

final connectionProvider = StateNotifierProvider<ConnectionController, CompanionConnectionState>((ref) {
  final api = ref.watch(apiProvider);
  final ws = ref.watch(wsProvider);
  return ConnectionController(apiClient: api, webSocketClient: ws);
});
