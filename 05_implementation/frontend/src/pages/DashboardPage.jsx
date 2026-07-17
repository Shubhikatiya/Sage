import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getLifeDomains, getThoughts, getDeadlines, getDailyPlans } from '../services/api'

function DashboardPage({ activeDomain }) {
  const [domains, setDomains] = useState([])
  const [thoughts, setThoughts] = useState([])
  const [deadlines, setDeadlines] = useState([])
  const [plans, setPlans] = useState([])
  const [greeting, setGreeting] = useState('')

  useEffect(() => {
    fetchData()
    fetchGreeting()
  }, [activeDomain])

  const fetchGreeting = async () => {
    try {
      const response = await fetch('http://localhost:8009/api/greet')
      const data = await response.json()
      if (data.greeting) setGreeting(data.greeting)
    } catch (e) {}
  }

  const fetchData = async () => {
    try {
      const domainsRes = await getLifeDomains()
      setDomains(domainsRes.data)

      const allThoughts = []
      const allDeadlines = []

      for (const domain of domainsRes.data) {
        try {
          const tRes = await getThoughts(domain.id)
          allThoughts.push(...tRes.data)
        } catch (e) {}

        try {
          const dRes = await getDeadlines(domain.id)
          allDeadlines.push(...dRes.data)
        } catch (e) {}
      }

      setThoughts(allThoughts)
      setDeadlines(allDeadlines)
    } catch (error) {
      console.error('Dashboard fetch error:', error)
    }
  }

  const topLevelDomains = domains.filter(d => !d.parent_id)
  const activeDomains = domains.filter(d => d.status === 'active')
  const pendingDeadlines = deadlines.filter(d => d.status !== 'completed')

  return (
    <div className="p-6 overflow-y-auto h-full">
      {/* Personalized Greeting */}
      {greeting && (
        <div className="mb-6 bg-gradient-to-r from-sage-600 to-sage-500 text-white p-4 rounded-xl">
          <p className="text-lg font-medium">{greeting}</p>
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-sage-800 mb-2">Dashboard</h1>
        <p className="text-sage-500">Your command center. Everything at a glance.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded-xl border border-sage-200">
          <div className="text-2xl font-bold text-sage-800">{topLevelDomains.length}</div>
          <div className="text-sm text-sage-500">Life Domains</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-sage-200">
          <div className="text-2xl font-bold text-green-600">{activeDomains.length}</div>
          <div className="text-sm text-sage-500">Active</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-sage-200">
          <div className="text-2xl font-bold text-orange-600">{pendingDeadlines.length}</div>
          <div className="text-sm text-sage-500">Upcoming Deadlines</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-sage-200">
          <div className="text-2xl font-bold text-sage-600">{thoughts.length}</div>
          <div className="text-sm text-sage-500">Captured Thoughts</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Scrollable Recent Thoughts */}
        <div className="bg-white p-6 rounded-xl border border-sage-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-sage-800">Recent Thoughts</h2>
            <span className="text-xs text-sage-400">{thoughts.length} total</span>
          </div>
          {thoughts.length === 0 ? (
            <p className="text-sage-400 text-sm">No thoughts captured yet. Start chatting!</p>
          ) : (
            <div className="max-h-64 overflow-y-auto space-y-3 pr-1">
              {thoughts.slice(0, 20).map(thought => (
                <div key={thought.id} className="p-3 bg-sage-50 rounded-lg">
                  <p className="text-sm text-sage-800 line-clamp-2">{thought.content}</p>
                  <p className="text-xs text-sage-400 mt-1">{new Date(thought.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scrollable Upcoming Deadlines */}
        <div className="bg-white p-6 rounded-xl border border-sage-200">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-sage-800">Upcoming Deadlines</h2>
            <span className="text-xs text-sage-400">{deadlines.length} total</span>
          </div>
          {deadlines.length === 0 ? (
            <p className="text-sage-400 text-sm">No deadlines set. Add one from the chat!</p>
          ) : (
            <div className="max-h-64 overflow-y-auto space-y-3 pr-1">
              {deadlines.slice(0, 20).map(deadline => (
                <div key={deadline.id} className="flex items-center justify-between p-3 bg-sage-50 rounded-lg">
                  <div>
                    <p className="text-sm font-medium text-sage-800">{deadline.title}</p>
                    <p className="text-xs text-sage-500">{truncateText(deadline.description, 60)}</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${deadline.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                    {deadline.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/chat" className="bg-sage-600 text-white p-4 rounded-xl hover:bg-sage-700 transition-colors text-center">
          <div className="text-lg font-semibold">Open Chat</div>
          <div className="text-sm text-sage-200">Talk to Sage</div>
        </Link>

        <Link to="/chat" className="bg-white border border-sage-200 text-sage-700 p-4 rounded-xl hover:bg-sage-50 transition-colors text-center">
          <div className="text-lg font-semibold">Capture Idea</div>
          <div className="text-sm text-sage-500">Save a new thought</div>
        </Link>

        <button className="bg-white border border-sage-200 text-sage-700 p-4 rounded-xl hover:bg-sage-50 transition-colors text-center">
          <div className="text-lg font-semibold">Weekend Review</div>
          <div className="text-sm text-sage-500">Review captured ideas</div>
        </button>
      </div>
    </div>
  )
}

export default DashboardPage
