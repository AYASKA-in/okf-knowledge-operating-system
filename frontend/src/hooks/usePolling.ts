import { useEffect, useRef } from "react"

export function usePolling(
  callback: () => void,
  intervalMs: number,
  stopWhen: () => boolean = () => false
) {
  const savedCallback = useRef(callback)
  savedCallback.current = callback

  useEffect(() => {
    if (stopWhen()) return

    savedCallback.current()

    const id = setInterval(() => {
      if (stopWhen()) {
        clearInterval(id)
        return
      }
      savedCallback.current()
    }, intervalMs)

    return () => clearInterval(id)
  }, [intervalMs, stopWhen])
}
