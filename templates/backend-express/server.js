const express = require('express')
const cors = require('cors')

const app = express()
app.use(cors())
app.use(express.json())

// In-memory store — replace with a real database as needed.
const store = new Map()
let nextId = 1

app.get('/health', (req, res) => res.json({ status: 'ok', service: 'bigbro-api' }))

app.get('/api/items', (req, res) => res.json([...store.values()]))

app.post('/api/items', (req, res) => {
  const { name, value } = req.body || {}
  if (!name) return res.status(400).json({ error: 'name is required' })
  const item = { id: nextId++, name, value: value ?? null }
  store.set(item.id, item)
  res.status(201).json(item)
})

app.get('/api/items/:id', (req, res) => {
  const item = store.get(Number(req.params.id))
  if (!item) return res.status(404).json({ error: 'item not found' })
  res.json(item)
})

app.delete('/api/items/:id', (req, res) => {
  if (!store.delete(Number(req.params.id))) return res.status(404).json({ error: 'item not found' })
  res.status(204).end()
})

const port = process.env.PORT || 3000
app.listen(port, () => console.log(`BigBro API listening on :${port}`))
