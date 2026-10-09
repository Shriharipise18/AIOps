/**
 * useHealth.js — Custom React hook for polling the /health endpoint.
 *
 * Returns { data, loading, error, refetch } and automatically refreshes
 * every POLL_INTERVAL milliseconds.
 */
import { useState, useEffect, useCallback } from 'react'
import { fetchHealth } from '../api/api'

const POLL_INTERVAL = 15_000 // 15 s

export function useHealth() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchHealth()
      setData(res.data)
    } catch {
      // Keep transport details internal; the dashboard renders a calm
      // disconnected state and offers a retry action.
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial fetch + polling
  useEffect(() => {
    refetch()
    const interval = setInterval(refetch, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [refetch])

  return { data, loading, error, refetch }
}
