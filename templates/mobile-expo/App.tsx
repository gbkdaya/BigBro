import { StatusBar } from 'expo-status-bar'
import { Pressable, SafeAreaView, StyleSheet, Text } from 'react-native'
import { useState } from 'react'

export default function App() {
  const [count, setCount] = useState(0)
  return (
    <SafeAreaView style={styles.root}>
      <StatusBar style="auto" />
      <Text style={styles.title}>BigBro starter</Text>
      <Text style={styles.sub}>Scaffolded with the mobile-expo template.</Text>
      <Pressable style={styles.btn} onPress={() => setCount((c) => c + 1)}>
        <Text style={styles.btnText}>Count: {count}</Text>
      </Pressable>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#0b0e14', alignItems: 'center', justifyContent: 'center' },
  title: { color: '#f5b942', fontSize: 28, fontWeight: '800' },
  sub: { color: '#8b93a7', marginTop: 8 },
  btn: { marginTop: 24, backgroundColor: '#f5b942', borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12 },
  btnText: { color: '#1a1205', fontWeight: '700' },
})
