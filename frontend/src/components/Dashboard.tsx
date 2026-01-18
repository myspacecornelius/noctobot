import { useEffect, useState } from 'react'
import { 
  Play, 
  Pause, 
  Zap, 
  TrendingUp, 
  ShoppingBag, 
  AlertTriangle,
  Activity,
  DollarSign,
  Target,
  Loader2
} from 'lucide-react'
import { useStore } from '../store/useStore'
import { api } from '../api/client'
import { cn, formatPrice, formatRelativeTime } from '../lib/utils'
import { toast } from './ui/Toast'

function StatCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend,
  color = 'purple',
  loading = false
}: { 
  title: string
  value: string | number
  subtitle?: string
  icon: any
  trend?: number
  color?: 'purple' | 'green' | 'yellow' | 'red' | 'cyan'
  loading?: boolean
}) {
  const colorClasses = {
    purple: 'group-hover:shadow-purple-500/20',
    green: 'group-hover:shadow-emerald-500/20',
    yellow: 'group-hover:shadow-amber-500/20',
    red: 'group-hover:shadow-rose-500/20',
    cyan: 'group-hover:shadow-cyan-500/20',
  }
  
  const iconBgColors = {
    purple: 'bg-purple-500/10 text-purple-400 group-hover:bg-purple-500/20',
    green: 'bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20',
    yellow: 'bg-amber-500/10 text-amber-400 group-hover:bg-amber-500/20',
    red: 'bg-rose-500/10 text-rose-400 group-hover:bg-rose-500/20',
    cyan: 'bg-cyan-500/10 text-cyan-400 group-hover:bg-cyan-500/20',
  }

  const accentColors = {
    purple: 'bg-purple-500',
    green: 'bg-emerald-500',
    yellow: 'bg-amber-500',
    red: 'bg-rose-500',
    cyan: 'bg-cyan-500',
  }
  
  return (
    <div className={cn(
      "group relative p-5 rounded-xl bg-zinc-900/50 border border-zinc-800 overflow-hidden",
      "transition-all duration-300 hover:border-zinc-700 hover:shadow-xl",
      colorClasses[color]
    )}>
      <div className={cn("absolute top-0 left-0 w-full h-0.5", accentColors[color], "opacity-50")} />
      
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-zinc-400">{title}</p>
          {loading ? (
            <div className="h-9 w-20 skeleton" />
          ) : (
            <p className="text-3xl font-bold text-white tracking-tight">{value.toLocaleString()}</p>
          )}
          {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
        </div>
        <div className={cn(
          "p-3 rounded-xl transition-colors duration-300",
          iconBgColors[color]
        )}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      
      {trend !== undefined && (
        <div className={cn(
          "flex items-center gap-1.5 mt-4 text-xs font-medium",
          trend >= 0 ? "text-emerald-400" : "text-rose-400"
        )}>
          <TrendingUp className={cn("w-3.5 h-3.5", trend < 0 && "rotate-180")} />
          <span>{trend >= 0 ? '+' : ''}{trend}% from last hour</span>
        </div>
      )}
    </div>
  )
}

function LiveFeed() {
  const { events } = useStore()
  const recentEvents = events.slice(0, 6)
  
  return (
    <div className="bg-zinc-900/50 rounded-xl border border-zinc-800 overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          Live Product Feed
        </h3>
        <div className="flex items-center gap-2 px-2 py-1 bg-emerald-500/10 rounded-full">
          <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
          <span className="text-xs font-medium text-emerald-400">Live</span>
        </div>
      </div>
      
      <div className="p-4 space-y-2 max-h-[400px] overflow-y-auto">
        {recentEvents.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-zinc-800 flex items-center justify-center">
              <Zap className="w-6 h-6 text-zinc-600" />
            </div>
            <p className="text-sm font-medium text-zinc-400">No products detected yet</p>
            <p className="text-xs text-zinc-600 mt-1">Start monitors to see live updates</p>
          </div>
        ) : (
          recentEvents.map((event, i) => (
            <div 
              key={event.id || i}
              className={cn(
                "p-3 rounded-lg border transition-all duration-200 animate-fade-in-up hover:bg-zinc-800/50",
                event.priority === 'high' 
                  ? "bg-emerald-500/5 border-emerald-500/20" 
                  : "bg-zinc-800/30 border-zinc-800"
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={cn(
                      "badge",
                      event.priority === 'high' ? "badge-green" : "badge-purple"
                    )}>
                      {event.store}
                    </span>
                    {event.matched && (
                      <span className="badge badge-yellow">Matched</span>
                    )}
                  </div>
                  <p className="text-sm text-white font-medium truncate">{event.product}</p>
                  <div className="flex items-center gap-2 mt-1.5 text-xs text-zinc-500">
                    <span className="font-medium text-zinc-400">{formatPrice(event.price)}</span>
                    <span className="text-zinc-700">•</span>
                    <span>{event.sizes?.slice(0, 3).join(', ')}{event.sizes?.length > 3 ? '...' : ''}</span>
                    <span className="text-zinc-700">•</span>
                    <span>{formatRelativeTime(event.timestamp)}</span>
                  </div>
                </div>
                {event.profit && (
                  <div className="text-right shrink-0">
                    <p className={cn(
                      "text-sm font-bold",
                      event.profit >= 100 ? "text-emerald-400" : event.profit >= 30 ? "text-amber-400" : "text-zinc-400"
                    )}>
                      +{formatPrice(event.profit)}
                    </p>
                    <p className="text-xs text-zinc-600">profit</p>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function StoreHealth() {
  const { shopifyStores } = useStore()
  const stores = Object.entries(shopifyStores).slice(0, 8)
  
  return (
    <div className="bg-zinc-900/50 rounded-xl border border-zinc-800 overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-zinc-800">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Target className="w-4 h-4 text-purple-400" />
          Store Health
        </h3>
        <span className="text-xs text-zinc-500">{stores.length} stores</span>
      </div>
      
      <div className="p-4 space-y-2 max-h-[400px] overflow-y-auto">
        {stores.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-zinc-800 flex items-center justify-center">
              <Target className="w-6 h-6 text-zinc-600" />
            </div>
            <p className="text-sm font-medium text-zinc-400">No stores configured</p>
            <p className="text-xs text-zinc-600 mt-1">Add stores in the Monitors tab</p>
          </div>
        ) : (
          stores.map(([id, store]) => (
            <div 
              key={id} 
              className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/30 border border-zinc-800 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={cn(
                  "status-dot",
                  store.errorCount === 0 ? "online" : store.errorCount < 3 ? "warning" : "offline"
                )} />
                <div>
                  <span className="text-sm font-medium text-white">{store.name}</span>
                  <p className="text-xs text-zinc-500">
                    {store.lastCheck ? formatRelativeTime(store.lastCheck) : 'Not checked'}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold text-white">{store.productsFound.toLocaleString()}</p>
                <p className="text-xs text-zinc-500">products</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export function Dashboard() {
  const { 
    isRunning, 
    setRunning, 
    monitorsRunning, 
    setMonitorsRunning,
    stats,
    setStats,
    setShopifyStores,
    addEvent
  } = useStore()
  
  const [loading, setLoading] = useState(false)
  
  const toggleEngine = async () => {
    setLoading(true)
    try {
      if (isRunning) {
        await api.stopEngine()
        setRunning(false)
        toast.info('Engine Stopped', 'Bot engine has been stopped')
      } else {
        await api.startEngine()
        setRunning(true)
        toast.success('Engine Started', 'Bot engine is now running')
      }
    } catch (e) {
      console.error(e)
      toast.error('Error', 'Failed to toggle engine')
    }
    setLoading(false)
  }
  
  const toggleMonitors = async () => {
    setLoading(true)
    try {
      if (monitorsRunning) {
        await api.stopMonitors()
        setMonitorsRunning(false)
        toast.info('Monitors Stopped', 'Product monitoring has been stopped')
      } else {
        await api.setupShopify()
        await api.startMonitors()
        setMonitorsRunning(true)
        toast.success('Monitors Started', 'Now monitoring for products')
      }
    } catch (e) {
      console.error(e)
      toast.error('Error', 'Failed to toggle monitors')
    }
    setLoading(false)
  }
  
  // Poll for updates
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const status = await api.getMonitorStatus()
        if (status.running !== undefined) {
          setMonitorsRunning(status.running)
        }
        if (status.total_products_found !== undefined) {
          setStats({ totalProductsFound: status.total_products_found })
        }
        if (status.high_priority_found !== undefined) {
          setStats({ highPriorityFound: status.high_priority_found })
        }
        if (status.shopify?.stores) {
          setShopifyStores(status.shopify.stores)
        }
      } catch {}
    }
    
    pollStatus()
    const interval = setInterval(pollStatus, 5000)
    return () => clearInterval(interval)
  }, [])
  
  // Poll for events
  useEffect(() => {
    const pollEvents = async () => {
      try {
        const data = await api.getMonitorEvents(10)
        if (data.events) {
          data.events.forEach((e: any, i: number) => {
            addEvent({ ...e, id: `${e.timestamp}-${i}` })
          })
        }
      } catch {}
    }
    
    const interval = setInterval(pollEvents, 3000)
    return () => clearInterval(interval)
  }, [])
  
  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Command Center</h1>
          <p className="text-zinc-500 text-sm mt-1">Real-time monitoring and control</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={toggleMonitors}
            disabled={loading}
            aria-label={monitorsRunning ? 'Stop Monitors' : 'Start Monitors'}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all duration-200",
              monitorsRunning
                ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20"
                : "bg-zinc-800 text-zinc-300 border border-zinc-700 hover:border-cyan-500/50 hover:text-cyan-400"
            )}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : monitorsRunning ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            {monitorsRunning ? 'Stop Monitors' : 'Start Monitors'}
          </button>
          
          <button
            onClick={toggleEngine}
            disabled={loading}
            aria-label={isRunning ? 'Stop Engine' : 'Start Engine'}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-all duration-200",
              isRunning
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                : "btn-primary"
            )}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : isRunning ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Zap className="w-4 h-4" />
            )}
            {isRunning ? 'Stop Engine' : 'Start Engine'}
          </button>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Products Found"
          value={stats.totalProductsFound}
          subtitle="Total detections"
          icon={ShoppingBag}
          color="purple"
        />
        <StatCard
          title="High Priority"
          value={stats.highPriorityFound}
          subtitle="Profitable items"
          icon={TrendingUp}
          color="green"
        />
        <StatCard
          title="Checkouts"
          value={stats.checkouts}
          subtitle="Successful orders"
          icon={DollarSign}
          color="cyan"
        />
        <StatCard
          title="Declines"
          value={stats.declines}
          subtitle="Failed attempts"
          icon={AlertTriangle}
          color="red"
        />
      </div>
      
      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiveFeed />
        <StoreHealth />
      </div>
    </div>
  )
}
