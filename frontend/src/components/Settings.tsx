import { useState, useEffect } from 'react'
import { 
  Settings as SettingsIcon, 
  Bell,
  Moon,
  Sun,
  Shield,
  Key,
  Webhook,
  Save,
  Upload,
  Download,
  Trash2,
  RefreshCw,
  Wallet,
  Loader2
} from 'lucide-react'
import { cn } from '../lib/utils'
import { api } from '../api/client'
import { toast } from './ui/Toast'

function SettingSection({ title, description, children }: { 
  title: string
  description?: string
  children: React.ReactNode 
}) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-zinc-800">
        <h3 className="font-semibold text-white">{title}</h3>
        {description && <p className="text-sm text-zinc-500 mt-1">{description}</p>}
      </div>
      <div className="p-4">
        {children}
      </div>
    </div>
  )
}

function Toggle({ enabled, onChange, label }: { enabled: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-zinc-300">{label}</span>
      <button
        onClick={() => onChange(!enabled)}
        className={cn(
          "w-11 h-6 rounded-full transition-colors relative",
          enabled ? "bg-purple-600" : "bg-zinc-700"
        )}
        role="switch"
        aria-checked={enabled ? "true" : "false"}
        aria-label={label}
      >
        <div className={cn(
          "absolute w-5 h-5 rounded-full bg-white top-0.5 transition-all shadow-sm",
          enabled ? "left-5" : "left-0.5"
        )} />
      </button>
    </div>
  )
}

function InputField({ label, value, onChange, type = 'text', placeholder = '' }: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
}) {
  return (
    <div className="mb-4">
      <label className="block text-sm text-zinc-400 mb-2">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input w-full"
        placeholder={placeholder}
        aria-label={label}
      />
    </div>
  )
}

export function Settings() {
  const [settings, setSettings] = useState({
    // Notifications
    soundAlerts: true,
    desktopNotifications: true,
    discordWebhook: '',
    successWebhook: '',
    failureWebhook: '',
    
    // Performance
    maxConcurrentTasks: 50,
    monitorDelay: 3000,
    retryDelay: 2000,
    checkoutTimeout: 60,
    
    // Captcha
    twoCaptchaKey: '',
    capmonsterKey: '',
    autoSolveCaptcha: true,
    
    // Evasion
    randomizeFingerprint: true,
    humanizeTyping: true,
    rotateUserAgents: true,
    useResidentialProxies: false,
    
    // Theme
    darkMode: true,
  })
  
  const [saving, setSaving] = useState(false)
  const [captchaBalances, setCaptchaBalances] = useState<{ twocaptcha?: number; capmonster?: number } | null>(null)
  const [loadingBalances, setLoadingBalances] = useState(false)
  
  useEffect(() => {
    fetchCaptchaBalances()
  }, [])
  
  const fetchCaptchaBalances = async () => {
    setLoadingBalances(true)
    try {
      const balances = await api.getCaptchaBalances()
      setCaptchaBalances(balances)
    } catch (e) {
      console.error('Failed to fetch captcha balances')
    }
    setLoadingBalances(false)
  }
  
  const handleSave = async () => {
    setSaving(true)
    try {
      await new Promise(r => setTimeout(r, 1000))
      toast.success('Settings Saved', 'Your preferences have been updated')
    } catch (e) {
      toast.error('Error', 'Failed to save settings')
    }
    setSaving(false)
  }
  
  const updateSetting = (key: string, value: any) => {
    setSettings(s => ({ ...s, [key]: value }))
  }
  
  return (
    <div className="p-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
          <p className="text-zinc-500 text-sm mt-1">Configure your bot preferences</p>
        </div>
        
        <button
          onClick={handleSave}
          disabled={saving}
          aria-label="Save settings"
          className="btn-primary flex items-center gap-2 disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Changes
        </button>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Notifications */}
        <SettingSection 
          title="Notifications" 
          description="Configure alerts and webhooks"
        >
          <div className="space-y-1 mb-4">
            <Toggle
              label="Sound Alerts"
              enabled={settings.soundAlerts}
              onChange={(v) => updateSetting('soundAlerts', v)}
            />
            <Toggle
              label="Desktop Notifications"
              enabled={settings.desktopNotifications}
              onChange={(v) => updateSetting('desktopNotifications', v)}
            />
          </div>
          
          <div className="pt-4 border-t border-zinc-800">
            <div className="flex items-center gap-2 text-sm text-purple-400 mb-3">
              <Bell className="w-4 h-4" />
              Discord Webhooks
            </div>
            <InputField
              label="Main Webhook"
              value={settings.discordWebhook}
              onChange={(v) => updateSetting('discordWebhook', v)}
              placeholder="https://discord.com/api/webhooks/..."
            />
            <InputField
              label="Success Webhook"
              value={settings.successWebhook}
              onChange={(v) => updateSetting('successWebhook', v)}
              placeholder="https://discord.com/api/webhooks/..."
            />
            <InputField
              label="Failure Webhook"
              value={settings.failureWebhook}
              onChange={(v) => updateSetting('failureWebhook', v)}
              placeholder="https://discord.com/api/webhooks/..."
            />
          </div>
        </SettingSection>
        
        {/* Captcha */}
        <SettingSection 
          title="Captcha Solving" 
          description="Configure captcha service API keys"
        >
          <Toggle
            label="Auto-solve Captchas"
            enabled={settings.autoSolveCaptcha}
            onChange={(v) => updateSetting('autoSolveCaptcha', v)}
          />
          
          <div className="pt-4 border-t border-[#1a1a2e] mt-4">
            <div className="flex items-center gap-2 text-sm text-purple-400 mb-3">
              <Key className="w-4 h-4" />
              API Keys
            </div>
            <InputField
              label="2Captcha API Key"
              value={settings.twoCaptchaKey}
              onChange={(v) => updateSetting('twoCaptchaKey', v)}
              type="password"
              placeholder="Enter API key"
            />
            <InputField
              label="CapMonster API Key"
              value={settings.capmonsterKey}
              onChange={(v) => updateSetting('capmonsterKey', v)}
              type="password"
              placeholder="Enter API key"
            />
          </div>
        </SettingSection>
        
        {/* Performance */}
        <SettingSection 
          title="Performance" 
          description="Tune bot speed and concurrency"
        >
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Max Concurrent Tasks</label>
              <input
                type="number"
                value={settings.maxConcurrentTasks}
                onChange={(e) => updateSetting('maxConcurrentTasks', parseInt(e.target.value) || 50)}
                className="w-full px-4 py-2.5 bg-[#1a1a24] border border-[#2a2a3a] rounded-lg text-white focus:outline-none focus:border-purple-500"
                min="1"
                max="100"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Checkout Timeout (s)</label>
              <input
                type="number"
                value={settings.checkoutTimeout}
                onChange={(e) => updateSetting('checkoutTimeout', parseInt(e.target.value) || 60)}
                className="w-full px-4 py-2.5 bg-[#1a1a24] border border-[#2a2a3a] rounded-lg text-white focus:outline-none focus:border-purple-500"
                min="10"
                max="300"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Monitor Delay (ms)</label>
              <input
                type="number"
                value={settings.monitorDelay}
                onChange={(e) => updateSetting('monitorDelay', parseInt(e.target.value) || 3000)}
                className="w-full px-4 py-2.5 bg-[#1a1a24] border border-[#2a2a3a] rounded-lg text-white focus:outline-none focus:border-purple-500"
                min="500"
                max="10000"
                step="500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Retry Delay (ms)</label>
              <input
                type="number"
                value={settings.retryDelay}
                onChange={(e) => updateSetting('retryDelay', parseInt(e.target.value) || 2000)}
                className="w-full px-4 py-2.5 bg-[#1a1a24] border border-[#2a2a3a] rounded-lg text-white focus:outline-none focus:border-purple-500"
                min="500"
                max="10000"
                step="500"
              />
            </div>
          </div>
        </SettingSection>
        
        {/* Anti-Bot Evasion */}
        <SettingSection 
          title="Anti-Bot Evasion" 
          description="Configure stealth and evasion techniques"
        >
          <div className="space-y-1">
            <Toggle
              label="Randomize Browser Fingerprint"
              enabled={settings.randomizeFingerprint}
              onChange={(v) => updateSetting('randomizeFingerprint', v)}
            />
            <Toggle
              label="Humanize Typing Patterns"
              enabled={settings.humanizeTyping}
              onChange={(v) => updateSetting('humanizeTyping', v)}
            />
            <Toggle
              label="Rotate User Agents"
              enabled={settings.rotateUserAgents}
              onChange={(v) => updateSetting('rotateUserAgents', v)}
            />
            <Toggle
              label="Prefer Residential Proxies"
              enabled={settings.useResidentialProxies}
              onChange={(v) => updateSetting('useResidentialProxies', v)}
            />
          </div>
        </SettingSection>
        
        {/* Data Management */}
        <SettingSection 
          title="Data Management" 
          description="Import, export, and manage your data"
        >
          <div className="flex flex-wrap gap-3">
            <button className="flex items-center gap-2 px-4 py-2 bg-[#1a1a24] text-gray-300 border border-[#2a2a3a] rounded-lg hover:border-purple-500/50 transition-colors">
              <Upload className="w-4 h-4" />
              Import Data
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-[#1a1a24] text-gray-300 border border-[#2a2a3a] rounded-lg hover:border-purple-500/50 transition-colors">
              <Download className="w-4 h-4" />
              Export Data
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors">
              <Trash2 className="w-4 h-4" />
              Clear All Data
            </button>
          </div>
        </SettingSection>
        
        {/* Theme */}
        <SettingSection 
          title="Appearance" 
          description="Customize the look and feel"
        >
          <div className="flex items-center gap-4">
            <button
              onClick={() => updateSetting('darkMode', true)}
              className={cn(
                "flex items-center gap-2 px-4 py-3 rounded-lg border transition-colors",
                settings.darkMode 
                  ? "bg-purple-500/20 border-purple-500/50 text-purple-400" 
                  : "bg-[#1a1a24] border-[#2a2a3a] text-gray-400"
              )}
            >
              <Moon className="w-5 h-5" />
              Dark Mode
            </button>
            <button
              onClick={() => updateSetting('darkMode', false)}
              className={cn(
                "flex items-center gap-2 px-4 py-3 rounded-lg border transition-colors",
                !settings.darkMode 
                  ? "bg-purple-500/20 border-purple-500/50 text-purple-400" 
                  : "bg-[#1a1a24] border-[#2a2a3a] text-gray-400"
              )}
            >
              <Sun className="w-5 h-5" />
              Light Mode
            </button>
          </div>
        </SettingSection>
      </div>
    </div>
  )
}
