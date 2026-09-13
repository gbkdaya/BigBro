import 'package:flutter/material.dart'

void main() => runApp(const BigBroApp())

class BigBroApp extends StatelessWidget {
  const BigBroApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BigBro App',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFFF5B942),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _count = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('BigBro starter')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('Scaffolded with the mobile-flutter template.'),
            const SizedBox(height: 16),
            FilledButton.tonalIcon(
              onPressed: () => setState(() => _count++),
              icon: const Icon(Icons.add),
              label: Text('Count: $_count'),
            ),
          ],
        ),
      ),
    );
  }
}
