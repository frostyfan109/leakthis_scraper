import React from 'react';

export default function useAbortController() {
  const abortControllerRef = React.useRef()
  const getAbortController = React.useCallback(() => {
    if (!abortControllerRef.current) {
      abortControllerRef.current = new AbortController()
    }
    return abortControllerRef.current
  }, [])

  React.useEffect(() => {
    return () => getAbortController().abort()
  }, [getAbortController])

  const getSignal = React.useCallback(() => getAbortController().signal, [
    getAbortController,
  ])

  return getSignal
}