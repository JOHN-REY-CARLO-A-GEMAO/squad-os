import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  final Dio dio;
  final FlutterSecureStorage secureStorage;
  final String baseUrl;

  ApiClient({
    String? baseUrl,
    Dio? dioClient,
    FlutterSecureStorage? storage,
  })  : baseUrl = baseUrl ?? 'http://127.0.0.1:8000',
        dio = dioClient ?? Dio(),
        secureStorage = storage ?? const FlutterSecureStorage() {
    dio.options.baseUrl = this.baseUrl;
    dio.options.connectTimeout = const Duration(seconds: 10);
    dio.options.receiveTimeout = const Duration(seconds: 10);

    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final accessToken = await secureStorage.read(key: 'access_token');
          if (accessToken != null) {
            options.headers['Authorization'] = 'Bearer $accessToken';
          }
          return handler.next(options);
        },
        onError: (err, handler) async {
          if (err.response?.statusCode == 401) {
            final refreshed = await attemptTokenRefresh();
            if (refreshed) {
              final accessToken = await secureStorage.read(key: 'access_token');
              err.requestOptions.headers['Authorization'] = 'Bearer $accessToken';
              final cloneReq = await dio.fetch(err.requestOptions);
              return handler.resolve(cloneReq);
            }
          }
          return handler.next(err);
        },
      ),
    );
  }

  Future<bool> attemptTokenRefresh() async {
    try {
      final refreshToken = await secureStorage.read(key: 'refresh_token');
      if (refreshToken == null) return false;

      final response = await dio.get('/api/v1/pair/token', queryParameters: {
        'device_id': 'SquadCompanionDevice',
        'nonce': 'rotated_nonce',
      });

      if (response.statusCode == 200) {
        final data = response.data;
        await secureStorage.write(key: 'access_token', value: data['access_token']);
        await secureStorage.write(key: 'refresh_token', value: data['refresh_token']);
        return true;
      }
    } catch (_) {}
    return false;
  }

  Future<Map<String, dynamic>> handshake() async {
    final response = await dio.post('/api/v1/handshake', data: {
      'client_version': '2.0.0',
      'capabilities': [
        'voice_input',
        'live_agent_streams',
        'nested_events',
        'mission_snapshots',
        'qr_pairing'
      ]
    });
    return response.data;
  }
}
