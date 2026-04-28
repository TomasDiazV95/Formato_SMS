import { useEffect, useRef, useState } from 'react'

const DEFAULT_DURATIONS = {
  success: 8000,
  info: 8000,
  warning: 12000,
  danger: 0,
}

function useStatusMessage(initialState = { type: 'info', message: '' }, durations = DEFAULT_DURATIONS) {
  const [status, setStatus] = useState(initialState)
  const timeoutRef = useRef(null)

  const clearTimer = () => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }

  const clearStatus = () => {
    clearTimer()
    setStatus({ type: 'info', message: '' })
  }

  const updateStatus = (type, message) => {
    clearTimer()
    setStatus({ type, message })

    if (!message) return

    const duration = durations[type] ?? durations.info ?? 0
    if (duration > 0) {
      timeoutRef.current = window.setTimeout(() => {
        setStatus({ type: 'info', message: '' })
        timeoutRef.current = null
      }, duration)
    }
  }

  useEffect(() => clearTimer, [])

  return {
    status,
    setStatus,
    updateStatus,
    clearStatus,
  }
}

export default useStatusMessage
