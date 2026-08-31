import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

void main() {
  runApp(const WhatAreYouDoingApp());
}

class WhatAreYouDoingApp extends StatelessWidget {
  const WhatAreYouDoingApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '뭐해요?',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFFE8A87C),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String message = "아직 오늘의 안부 메시지를 받아오지 않았어요.";
  String analysis = "";
  bool isLoading = false;

  // Pass a different URL for an emulator or a physical device.
  static const String apiUrl = String.fromEnvironment(
    "API_URL", defaultValue: "http://127.0.0.1:8001/today-message",
  );

  Future<void> fetchMessage() async {
    setState(() {
      isLoading = true;
      message = "오늘 부모님의 하루를 정리하는 중이에요...";
      analysis = "";
    });

    try {
      final response = await http.get(Uri.parse(apiUrl));

      if (response.statusCode == 200) {
        final data = jsonDecode(utf8.decode(response.bodyBytes));

        setState(() {
          message = data["message"] ?? "메시지를 받아오지 못했어요.";
          analysis = data["analysis"] ?? "";
        });
      } else {
        setState(() {
          message = "서버에서 메시지를 받아오지 못했어요.";
        });
      }
    } catch (e) {
      setState(() {
        message = "서버와 연결되지 않았어요.\nFastAPI 서버가 켜져 있는지 확인해주세요.";
      });
    }

    setState(() {
      isLoading = false;
    });
  }

  Future<void> callParent() async {
    const parentPhone = String.fromEnvironment("PARENT_PHONE");
    if (parentPhone.isEmpty) return;
    final Uri phoneUri = Uri(scheme: "tel", path: parentPhone);

    if (await canLaunchUrl(phoneUri)) {
      await launchUrl(phoneUri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFFF8F2),
      appBar: AppBar(
        title: const Text("뭐해요?"),
        centerTitle: true,
        backgroundColor: Colors.transparent,
      ),
      body: SafeArea(
  child: SingleChildScrollView(
    padding: const EdgeInsets.all(24),
    child: Column(
      children: [
        const SizedBox(height: 24),

        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            "오늘 부모님은...",
            style: TextStyle(
              fontSize: 30,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),

        const SizedBox(height: 20),

        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(26),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.08),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Text(
            message,
            style: const TextStyle(
              fontSize: 18,
              height: 1.55,
            ),
          ),
        ),

        if (analysis.isNotEmpty) ...[
          const SizedBox(height: 16),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: const Color(0xFFFFEFE2),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              analysis,
              style: const TextStyle(
                fontSize: 14,
                height: 1.45,
                color: Colors.black87,
              ),
            ),
          ),
        ],

        const SizedBox(height: 24),

        SizedBox(
          width: double.infinity,
          height: 58,
          child: FilledButton(
            onPressed: isLoading ? null : fetchMessage,
            child: Text(
              isLoading ? "불러오는 중..." : "오늘의 안부 메시지 받기",
              style: const TextStyle(fontSize: 17),
            ),
          ),
        ),

        const SizedBox(height: 12),

        SizedBox(
          width: double.infinity,
          height: 58,
          child: OutlinedButton(
            onPressed: callParent,
            child: const Text(
              "뭐해요? 전화하기",
              style: TextStyle(fontSize: 17),
            ),
          ),
        ),
      ],
    ),
  ),
),  
    );
  }
}