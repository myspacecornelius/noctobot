import { 
  LayoutDashboard, 
  Radio, 
  ShoppingCart, 
  Users, 
  Globe, 
  BarChart3, 
  Settings,
  Zap,
  TrendingUp,
  Sparkles
} from 'lucide-react'
import { useStore } from '../store/useStore'
import { cn } from '../lib/utils'

const navItems = [
  { id: 'dashboard', label: 'Command Center', icon: LayoutDashboard },
  { id: 'monitors', label: 'Monitors', icon: Radio },
  { id: 'feed', label: 'Product Feed', icon: Zap },
  { id: 'tasks', label: 'Tasks', icon: ShoppingCart },
  { id: 'profiles', label: 'Profiles', icon: Users },
  { id: 'proxies', label: 'Proxies', icon: Globe },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'intelligence', label: 'Intelligence', icon: TrendingUp },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const { selectedTab, setSelectedTab, isRunning, monitorsRunning, events, stats } = useStore()
  
  const highPriorityCount = events.filter(e => e.priority === 'high').length
  
  return (
    <aside className="w-[260px] h-screen bg-zinc-950 border-r border-zinc-800/50 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-zinc-800/50">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-zinc-950" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gradient tracking-tight">
              PHANTOM
            </h1>
            <p className="text-[10px] text-zinc-600 uppercase tracking-widest">Bot Suite v1.0</p>
          </div>
        </div>
      </div>
      
      {/* Status Cards */}
      <div className="p-3 space-y-2">
        <div className={cn(
          "p-3 rounded-lg border transition-all duration-300",
          isRunning 
            ? "bg-emerald-500/5 border-emerald-500/20" 
            : "bg-zinc-900/50 border-zinc-800"
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn(
                "status-dot",
                isRunning ? "online pulsing" : "offline"
              )} />
              <span className="text-xs font-medium text-zinc-400">Engine</span>
            </div>
            <span className={cn(
              "text-xs font-semibold",
              isRunning ? "text-emerald-400" : "text-zinc-600"
            )}>
              {isRunning ? "Running" : "Stopped"}
            </span>
          </div>
        </div>
        
        <div className={cn(
          "p-3 rounded-lg border transition-all duration-300",
          monitorsRunning 
            ? "bg-cyan-500/5 border-cyan-500/20" 
            : "bg-zinc-900/50 border-zinc-800"
        )}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={cn(
                "status-dot",
                monitorsRunning ? "online pulsing" : "offline"
              )} style={{ background: monitorsRunning ? '#22d3ee' : undefined }} />
              <span className="text-xs font-medium text-zinc-400">Monitors</span>
            </div>
            <span className={cn(
              "text-xs font-semibold",
              monitorsRunning ? "text-cyan-400" : "text-zinc-600"
            )}>
              {monitorsRunning ? "Active" : "Idle"}
            </span>
          </div>
          {monitorsRunning && stats.totalProductsFound > 0 && (
            <div className="mt-2 pt-2 border-t border-cyan-500/10">
              <p className="text-[10px] text-zinc-500">
                <span className="text-cyan-400 font-semibold">{stats.totalProductsFound.toLocaleString()}</span> products found
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
        <p className="px-3 py-2 text-[10px] font-semibold text-zinc-600 uppercase tracking-wider">Navigation</p>
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = selectedTab === item.id
          const showBadge = item.id === 'feed' && highPriorityCount > 0
          
          return (
            <button
              key={item.id}
              onClick={() => setSelectedTab(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
                isActive 
                  ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" 
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 border border-transparent"
              )}
            >
              <Icon className={cn("w-4 h-4", isActive && "text-purple-400")} />
              <span className="flex-1 text-left">{item.label}</span>
              {showBadge && (
                <span className="px-1.5 py-0.5 text-[10px] font-bold bg-rose-500 text-white rounded-md animate-pulse">
                  {highPriorityCount}
                </span>
              )}
            </button>
          )
        })}
      </nav>
      
      {/* Pro Badge */}
      <div className="p-3 border-t border-zinc-800/50">
        <div className="p-3 rounded-xl bg-gradient-to-r from-purple-500/10 to-cyan-500/10 border border-purple-500/20">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-xs font-semibold text-zinc-300">Phantom Pro</span>
          </div>
          <p className="text-[10px] text-zinc-500 mt-1">Advanced automation suite</p>
        </div>
      </div>
    </aside>
  )
}
