import { useEffect } from 'react'
import { useStore } from './store/useStore'
import { api } from './api/client'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './components/Dashboard'
import { ProductFeed } from './components/ProductFeed'
import { Monitors } from './components/Monitors'
import { Tasks } from './components/Tasks'
import { Profiles } from './components/Profiles'
import { Proxies } from './components/Proxies'
import { Analytics } from './components/Analytics'
import { Intelligence } from './components/Intelligence'
import { Settings } from './components/Settings'
import { ToastContainer } from './components/ui/Toast'

function App() {
  const { selectedTab, setRunning, setMonitorsRunning, setStats } = useStore()
  
  // Initial status fetch
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const status = await api.getStatus()
        if (status.running !== undefined) {
          setRunning(status.running)
        }
        
        const monitorStatus = await api.getMonitorStatus()
        if (monitorStatus.running !== undefined) {
          setMonitorsRunning(monitorStatus.running)
        }
        if (monitorStatus.total_products_found !== undefined) {
          setStats({
            totalProductsFound: monitorStatus.total_products_found,
            highPriorityFound: monitorStatus.high_priority_found || 0,
          })
        }
      } catch (e) {
        console.log('API not available yet')
      }
    }
    
    fetchStatus()
  }, [])
  
  const renderContent = () => {
    switch (selectedTab) {
      case 'dashboard':
        return <Dashboard />
      case 'feed':
        return <ProductFeed />
      case 'monitors':
        return <Monitors />
      case 'tasks':
        return <Tasks />
      case 'profiles':
        return <Profiles />
      case 'proxies':
        return <Proxies />
      case 'analytics':
        return <Analytics />
      case 'intelligence':
        return <Intelligence />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard />
    }
  }
  
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {renderContent()}
      </main>
      <ToastContainer />
    </div>
  )
}

export default App
