import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { createToastStore } from './toastStore.js'

describe('toastStore', () => {
  let store

  beforeEach(() => {
    vi.useFakeTimers()
    store = createToastStore()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('shows a toast with the provided message', () => {
    let currentToast

    const unsubscribe = store.subscribe((toast) => {
      currentToast = toast
    })

    store.showToast('Test message')

    expect(currentToast).toEqual({ message: 'Test message' })
    unsubscribe()
  })

  it('auto-dismisses after 3 seconds', () => {
    let currentToast

    const unsubscribe = store.subscribe((toast) => {
      currentToast = toast
    })

    store.showToast('Test message')
    expect(currentToast).toEqual({ message: 'Test message' })

    vi.advanceTimersByTime(3000)
    expect(currentToast).toBeNull()
    unsubscribe()
  })

  it('clears previous timeout when showToast is called again', () => {
    let currentToast

    const unsubscribe = store.subscribe((toast) => {
      currentToast = toast
    })

    store.showToast('Message 1')
    expect(currentToast).toEqual({ message: 'Message 1' })

    vi.advanceTimersByTime(500)

    store.showToast('Message 2')
    expect(currentToast).toEqual({ message: 'Message 2' })

    // Advance by 2500ms more (total 3000ms from first message)
    // If the first timeout wasn't cleared, it would fire and dismiss the toast here
    vi.advanceTimersByTime(2500)
    expect(currentToast).toEqual({ message: 'Message 2' })

    // Advance by 500ms more (total 3000ms from second message)
    vi.advanceTimersByTime(500)
    expect(currentToast).toBeNull()
    unsubscribe()
  })

  it('dismiss() clears any pending timeout', () => {
    let currentToast

    const unsubscribe = store.subscribe((toast) => {
      currentToast = toast
    })

    store.showToast('Test message')
    expect(currentToast).toEqual({ message: 'Test message' })

    store.dismiss()
    expect(currentToast).toBeNull()

    // Advance timer - nothing should happen since timeout was cleared
    vi.advanceTimersByTime(3000)
    expect(currentToast).toBeNull()
    unsubscribe()
  })

  it('returns a cleanup function that cancels the timeout', () => {
    let currentToast

    const unsubscribe = store.subscribe((toast) => {
      currentToast = toast
    })

    const cleanup = store.showToast('Test message')
    expect(currentToast).toEqual({ message: 'Test message' })

    cleanup()
    expect(currentToast).toEqual({ message: 'Test message' })

    vi.advanceTimersByTime(3000)
    // Toast should still be there since cleanup cancelled the timeout
    expect(currentToast).toEqual({ message: 'Test message' })
    unsubscribe()
  })
})
