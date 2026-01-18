import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'
import { cn } from '../../lib/utils'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

interface ToastStore {
  toasts: Toast[]
  add: (toast: Omit<Toast, 'id'>) => void
  remove: (id: string) => void
}

const toastStore: ToastStore = {
  toasts: [],
  add: () => {},
  remove: () => {},
}

let listeners: Array<() => void> = []

function emitChange() {
  listeners.forEach((listener) => listener())
}

export const toast = {
  success: (title: string, message?: string) => {
    const id = Math.random().toString(36).slice(2)
    toastStore.toasts = [...toastStore.toasts, { id, type: 'success', title, message, duration: 4000 }]
    emitChange()
  },
  error: (title: string, message?: string) => {
    const id = Math.random().toString(36).slice(2)
    toastStore.toasts = [...toastStore.toasts, { id, type: 'error', title, message, duration: 5000 }]
    emitChange()
  },
  warning: (title: string, message?: string) => {
    const id = Math.random().toString(36).slice(2)
    toastStore.toasts = [...toastStore.toasts, { id, type: 'warning', title, message, duration: 4000 }]
    emitChange()
  },
  info: (title: string, message?: string) => {
    const id = Math.random().toString(36).slice(2)
    toastStore.toasts = [...toastStore.toasts, { id, type: 'info', title, message, duration: 4000 }]
    emitChange()
  },
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: () => void }) {
  const [isLeaving, setIsLeaving] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLeaving(true)
      setTimeout(onRemove, 200)
    }, toast.duration || 4000)
    return () => clearTimeout(timer)
  }, [toast.duration, onRemove])

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
  }

  const colors = {
    success: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
    error: 'bg-red-500/10 border-red-500/30 text-red-400',
    warning: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
    info: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  }

  const Icon = icons[toast.type]

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-xl border backdrop-blur-xl shadow-2xl min-w-[320px] max-w-[420px]',
        colors[toast.type],
        isLeaving ? 'animate-slide-out-right' : 'animate-slide-in-right'
      )}
    >
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm text-white">{toast.title}</p>
        {toast.message && (
          <p className="text-sm text-zinc-400 mt-0.5">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => {
          setIsLeaving(true)
          setTimeout(onRemove, 200)
        }}
        className="p-1 hover:bg-white/10 rounded-lg transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="w-4 h-4 text-zinc-400" />
      </button>
    </div>
  )
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    const listener = () => setToasts([...toastStore.toasts])
    listeners.push(listener)
    return () => {
      listeners = listeners.filter((l) => l !== listener)
    }
  }, [])

  const removeToast = (id: string) => {
    toastStore.toasts = toastStore.toasts.filter((t) => t.id !== id)
    setToasts([...toastStore.toasts])
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} onRemove={() => removeToast(t.id)} />
      ))}
    </div>
  )
}
