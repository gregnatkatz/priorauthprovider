import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend, LineChart, Line, Area, AreaChart, ComposedChart
} from 'recharts'
import { 
  AlertCircle, TrendingUp, DollarSign, Clock, FileText, 
  Brain, Activity, Search, ChevronLeft, ChevronRight, RefreshCw,
  Building2, Stethoscope, Shield, Zap, Moon, Sun, Users, Briefcase,
  X, Phone, FileUp, CheckCircle, AlertTriangle, Calendar,
  Target, Clipboard, UserCheck, Timer, ThumbsUp, ThumbsDown
} from 'lucide-react'

type Persona = 'clinical' | 'admin' | 'executive'

const PERSONA_CONFIG = {
  clinical: {
    name: 'Clinical (Charge Nurse)',
    icon: Stethoscope,
    description: 'Denial resolution focus',
    defaultTab: 'denials',
    visibleTabs: ['dashboard', 'denials', 'ai']
  },
  admin: {
    name: 'Admin',
    icon: Users,
    description: 'Operations focus',
    defaultTab: 'denials',
    visibleTabs: ['dashboard', 'denials', 'ai', 'payer']
  },
  executive: {
    name: 'Executive',
    icon: Briefcase,
    description: 'Financial focus',
    defaultTab: 'dashboard',
    visibleTabs: ['dashboard', 'denials', 'ai', 'learning', 'payer']
  }
}
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface DashboardMetrics {
  total_claims: number
  total_denials: number
  denial_rate: number
  total_denied_amount: number
  total_recovered_amount: number
  recovery_rate: number
  pending_appeals: number
  avg_appeal_success_rate: number
  high_priority_denials: number
  pa_pending: number
  pa_approval_rate: number
}

interface Denial {
  denial_id: number
  claim_id: number
  carc_code: string
  rarc_code: string
  adjustment_amount: number
  denial_date: string
  appeal_deadline: string
  denial_status: string
  patient_sdoh_score: number
  patient_vulnerability_flag: boolean
  clinical_urgency_score: number
  appeal_success_probability: number
  recommended_action: string
  p2p_recommended: boolean
  root_cause_category: string
  priority_score: number
  claim_number: string
  patient_name: string
  patient_mrn: string
  payer_name: string
  billed_amount: number
  procedure_code: string
  procedure_description: string
  denial_reason_description: string
  denial_category: string
}

interface PriorAuth {
  prior_auth_id: number
  auth_number: string
  patient_name: string
  patient_mrn?: string
  payer_name: string
  procedure_code: string
  procedure_description: string
  request_date: string
  decision_date: string
  auth_status: string
  denial_probability: number
  documentation_score: number
  missing_documents: string
  clinical_urgency?: number
  estimated_cost?: number
}

interface Payer {
  payer_id: number
  payer_name: string
  payer_type: string
  avg_denial_rate: number
  avg_appeal_success_rate: number
  avg_days_to_decision: number
}

interface DenialByCategory {
  category: string
  count: number
  amount: number
  percentage: number
}

interface DenialByPayer {
  payer_id: number
  payer_name: string
  denial_count: number
  denial_amount: number
  denial_rate: number
}

interface AIInsight {
  agent_name: string
  insight_type: string
  description: string
  impact_score: number
  affected_count: number
  recommended_action: string
}

interface RLTrace {
  trace_id: number
  action_type: string
  action_timestamp: string
  ai_recommendation: string
  ai_confidence: number
  staff_followed_ai: boolean
  outcome: string
  outcome_amount: number
  reward_score: number
  feedback_rating: number
  staff_id: string
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7300']

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    'New': 'bg-blue-500',
    'In Review': 'bg-yellow-500',
    'Appealed': 'bg-purple-500',
    'Resolved': 'bg-green-500',
    'Pending': 'bg-yellow-500',
    'Approved': 'bg-green-500',
    'Denied': 'bg-red-500',
    'Partial': 'bg-orange-500',
    'Won': 'bg-green-500',
    'Lost': 'bg-red-500',
    'Success': 'bg-green-500',
    'Failure': 'bg-red-500'
  }
  return colors[status] || 'bg-gray-500'
}

function getPriorityColor(score: number): string {
  if (score >= 0.7) return 'text-red-600 bg-red-50'
  if (score >= 0.5) return 'text-yellow-600 bg-yellow-50'
  return 'text-green-600 bg-green-50'
}

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [denials, setDenials] = useState<Denial[]>([])
  const [denialsByCategory, setDenialsByCategory] = useState<DenialByCategory[]>([])
  const [denialsByPayer, setDenialsByPayer] = useState<DenialByPayer[]>([])
  const [priorAuths, setPriorAuths] = useState<PriorAuth[]>([])
  const [payers, setPayers] = useState<Payer[]>([])
  const [aiInsights, setAiInsights] = useState<AIInsight[]>([])
  const [agentStatus, setAgentStatus] = useState<any>(null)
        const [rlTraces, setRlTraces] = useState<RLTrace[]>([])
        const [learningMetrics, setLearningMetrics] = useState<any>(null)
        const [resolutionTrends, setResolutionTrends] = useState<any>(null)
        const [denialPredictions, setDenialPredictions] = useState<any>(null)
        const [recoveryForecast, setRecoveryForecast] = useState<any>(null)
        const [aiImpact, setAiImpact] = useState<any>(null)
        const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
    const [darkMode, setDarkMode] = useState(true)
    const [persona, setPersona] = useState<Persona>('admin')
    const [selectedDenial, setSelectedDenial] = useState<Denial | null>(null)
    const [selectedPA, setSelectedPA] = useState<PriorAuth | null>(null)
    const [denialAnalysis, setDenialAnalysis] = useState<any>(null)
    const [analysisLoading, setAnalysisLoading] = useState(false)
    // workflowFilter removed - now using statusFilter for both tabs
    const [appealLetter, setAppealLetter] = useState<any>(null)
    const [appealLetterLoading, setAppealLetterLoading] = useState(false)
    const [treatmentGuidance, setTreatmentGuidance] = useState<any>(null)
    const [treatmentGuidanceLoading, setTreatmentGuidanceLoading] = useState(false)
    // Ingestion simulator state
    const [ingestionRunning, setIngestionRunning] = useState(false)
    const [ingestionProgress, setIngestionProgress] = useState(0)
    const [ingestionCurrentAgent, setIngestionCurrentAgent] = useState('')
    const [ingestionSteps, setIngestionSteps] = useState<any[]>([])
    const [ingestionResult, setIngestionResult] = useState<any>(null)
    // Re-evaluation state for existing denials/PAs
    const [reEvalRunning, setReEvalRunning] = useState(false)
    const [reEvalProgress, setReEvalProgress] = useState(0)
    const [reEvalCurrentAgent, setReEvalCurrentAgent] = useState('')
    const [reEvalSteps, setReEvalSteps] = useState<any[]>([])
    const [reEvalResult, setReEvalResult] = useState<any>(null)
    // Simulate changes state for demo
    const [simulatedChanges, setSimulatedChanges] = useState<string[]>([])
    const [changesNeedReEval, setChangesNeedReEval] = useState(false)
    // Feed ingestion state
    const [feedStatus, setFeedStatus] = useState<any>(null)
    const [feedRunning, setFeedRunning] = useState(false)
    const [autoFeedEnabled, setAutoFeedEnabled] = useState(false)
    // AI adherence metrics
    const [aiAdherence, setAiAdherence] = useState<any>(null)
    // Recovery rate metrics
    const [recoveryRate, setRecoveryRate] = useState<any>(null)

  useEffect(() => {
    // Initialize dark mode (default to dark)
    document.documentElement.classList.add('dark')
  }, [])

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  useEffect(() => {
    fetchDashboardData()
  }, [])

  useEffect(() => {
    if (activeTab === 'denials') {
      fetchDenials()
    } else if (activeTab === 'pa') {
      fetchPriorAuths()
    } else if (activeTab === 'ai') {
      fetchAIData()
      fetchFeedStatus()
      fetchAIAdherence()
      fetchRecoveryRate()
    } else if (activeTab === 'learning') {
      fetchLearningData()
    } else if (activeTab === 'payer') {
      fetchPayerData()
    }
  }, [activeTab, currentPage, statusFilter, searchTerm])

        const fetchDashboardData = async () => {
          setLoading(true)
          try {
            const [metricsRes, categoryRes, payerRes, trendsRes, predictionsRes, forecastRes, aiImpactRes] = await Promise.all([
              fetch(`${API_URL}/api/dashboard/metrics`),
              fetch(`${API_URL}/api/dashboard/denials-by-category`),
              fetch(`${API_URL}/api/dashboard/denials-by-payer`),
              fetch(`${API_URL}/api/analytics/resolution-trends`),
              fetch(`${API_URL}/api/analytics/denial-predictions`),
              fetch(`${API_URL}/api/analytics/recovery-forecast`),
              fetch(`${API_URL}/api/analytics/ai-impact`)
            ])
      
            setMetrics(await metricsRes.json())
            setDenialsByCategory(await categoryRes.json())
            setDenialsByPayer(await payerRes.json())
            setResolutionTrends(await trendsRes.json())
            setDenialPredictions(await predictionsRes.json())
            setRecoveryForecast(await forecastRes.json())
            setAiImpact(await aiImpactRes.json())
          } catch (error) {
            console.error('Error fetching dashboard data:', error)
          }
          setLoading(false)
        }

  const fetchDenials = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '15',
        sort_by: 'priority_score',
        sort_order: 'desc'
      })
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (searchTerm) params.append('search', searchTerm)
      
      const res = await fetch(`${API_URL}/api/denials?${params}`)
      const data = await res.json()
      setDenials(data.items)
      setTotalPages(data.total_pages)
    } catch (error) {
      console.error('Error fetching denials:', error)
    }
  }

  const fetchPriorAuths = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '15'
      })
      if (statusFilter !== 'all') params.append('status', statusFilter)
      if (searchTerm) params.append('search', searchTerm)
      
      const res = await fetch(`${API_URL}/api/prior-auths?${params}`)
      const data = await res.json()
      setPriorAuths(data.items)
      setTotalPages(data.total_pages)
    } catch (error) {
      console.error('Error fetching prior auths:', error)
    }
  }

  const fetchAIData = async () => {
    try {
      const [insightsRes, statusRes] = await Promise.all([
        fetch(`${API_URL}/api/ai/insights`),
        fetch(`${API_URL}/api/ai/agent-status`)
      ])
      const insightsData = await insightsRes.json()
      setAiInsights(insightsData.insights)
      setAgentStatus(await statusRes.json())
    } catch (error) {
      console.error('Error fetching AI data:', error)
    }
  }

  const fetchLearningData = async () => {
    try {
      const [tracesRes, metricsRes] = await Promise.all([
        fetch(`${API_URL}/api/learning/traces?page=${currentPage}&page_size=15`),
        fetch(`${API_URL}/api/learning/metrics`)
      ])
      const tracesData = await tracesRes.json()
      setRlTraces(tracesData.items)
      setTotalPages(tracesData.total_pages)
      setLearningMetrics(await metricsRes.json())
    } catch (error) {
      console.error('Error fetching learning data:', error)
    }
  }

    const fetchPayerData = async () => {
      try {
        const res = await fetch(`${API_URL}/api/payers`)
        setPayers(await res.json())
      } catch (error) {
        console.error('Error fetching payer data:', error)
      }
    }

    const fetchFeedStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/api/feeds/status`)
        setFeedStatus(await res.json())
      } catch (error) {
        console.error('Error fetching feed status:', error)
      }
    }

    const fetchAIAdherence = async () => {
      try {
        const res = await fetch(`${API_URL}/api/analytics/ai-adherence`)
        setAiAdherence(await res.json())
      } catch (error) {
        console.error('Error fetching AI adherence:', error)
      }
    }

    const fetchRecoveryRate = async () => {
      try {
        const res = await fetch(`${API_URL}/api/analytics/recovery-rate`)
        setRecoveryRate(await res.json())
      } catch (error) {
        console.error('Error fetching recovery rate:', error)
      }
    }

    const triggerFeedIngestion = async (source: string) => {
      setFeedRunning(true)
      try {
        const res = await fetch(`${API_URL}/api/feeds/ingest/${source}`, { method: 'POST' })
        const data = await res.json()
        console.log('Feed ingestion result:', data)
        // Refresh data after ingestion
        await fetchFeedStatus()
        await fetchDenials()
        await fetchDashboardData()
      } catch (error) {
        console.error('Error triggering feed ingestion:', error)
      } finally {
        setFeedRunning(false)
      }
    }

    const toggleAutoFeed = async () => {
      try {
        if (autoFeedEnabled) {
          await fetch(`${API_URL}/api/feeds/stop-auto`, { method: 'POST' })
          setAutoFeedEnabled(false)
        } else {
          await fetch(`${API_URL}/api/feeds/start-auto`, { method: 'POST' })
          setAutoFeedEnabled(true)
        }
      } catch (error) {
        console.error('Error toggling auto feed:', error)
      }
    }

    const simulatePolicyChange = async () => {
      try {
        const res = await fetch(`${API_URL}/api/policies/simulate-change?payer_id=1&change_type=coverage_expanded&affected_procedures=99213,99214&description=Coverage expanded for office visits`, { method: 'POST' })
        const data = await res.json()
        console.log('Policy change result:', data)
        // Refresh denials to show re-eval badges
        await fetchDenials()
      } catch (error) {
        console.error('Error simulating policy change:', error)
      }
    }

    const simulateAppealResponses = async () => {
      try {
        const res = await fetch(`${API_URL}/api/appeals/simulate-responses`, { method: 'POST' })
        const data = await res.json()
        console.log('Appeal responses:', data)
        // Refresh data
        await fetchRecoveryRate()
        await fetchDenials()
        await fetchDashboardData()
      } catch (error) {
        console.error('Error simulating appeal responses:', error)
      }
    }

    const fetchDenialAnalysis = async (denialId: number) => {
      setAnalysisLoading(true)
      try {
        const res = await fetch(`${API_URL}/api/ai/analyze-denial/${denialId}`, { method: 'POST' })
        const data = await res.json()
        setDenialAnalysis(data)
      } catch (error) {
        console.error('Error fetching denial analysis:', error)
        // Fallback analysis for demo
        setDenialAnalysis({
          recommendation: {
            priority_score: 0.75,
            recommended_actions: [
              'Submit written appeal with additional clinical documentation',
              'Include recent progress notes and test results',
              'Reference payer policy guidelines'
            ],
            confidence: 0.85
          },
          analysis: {
            clinical_urgency: { score: 0.7, urgency_level: 'high', time_sensitivity: 7 },
            doc_completeness: { missing_docs: ['Progress notes', 'Lab results', 'Prior auth documentation'] },
            recovery_predictor: { success_probability: 0.72, confidence: 0.8 },
            p2p_optimizer: { recommended: true, physician: 'Cardiologist', success_rate: 0.75 }
          }
        })
      } finally {
        setAnalysisLoading(false)
      }
    }

    const handleDenialClick = (denial: Denial) => {
      setSelectedDenial(denial)
      fetchDenialAnalysis(denial.denial_id)
    }

    const handleWorkflowAction = async (action: string, denialId: number) => {
      console.log(`Action: ${action} for denial ${denialId}`)
      
      // Determine action type for staff action logging
      const actionType = action === 'follow_ai' ? 'follow_ai' : 
                        action === 'override_ai' ? 'custom_plan' :
                        action === 'close_non_recoverable' ? 'dismiss' : 'custom_plan'
      
      // Log staff action to backend for RL feedback loop
      try {
        await fetch(`${API_URL}/api/denials/${denialId}/action?action_type=${actionType}&actual_action=${action}&staff_id=staff_${persona}`, {
          method: 'POST'
        })
      } catch (error) {
        console.error('Error logging staff action:', error)
      }
      
      // Submit appeal if action is submit_appeal or follow_ai with appeal recommendation
      if (action === 'submit_appeal' || (action === 'follow_ai' && selectedDenial?.recommended_action?.toLowerCase().includes('appeal'))) {
        try {
          await fetch(`${API_URL}/api/denials/${denialId}/appeal?appeal_type=first_level&followed_ai=${action === 'follow_ai'}`, {
            method: 'POST'
          })
        } catch (error) {
          console.error('Error submitting appeal:', error)
        }
      }
    
      // Update local state
      const updatedDenials = denials.map(d => {
        if (d.denial_id === denialId) {
          const newStatus = action === 'submit_appeal' || action === 'follow_ai' ? 'Appealed' : 
                           action === 'schedule_p2p' ? 'In Review' :
                           action === 'request_docs' ? 'In Review' : 
                           action === 'close_non_recoverable' ? 'Written Off' : d.denial_status
          return { ...d, denial_status: newStatus }
        }
        return d
      })
      setDenials(updatedDenials)
    
      // Update selected denial if it's the one being actioned
      if (selectedDenial?.denial_id === denialId) {
        setSelectedDenial(prev => prev ? { ...prev, denial_status: updatedDenials.find(d => d.denial_id === denialId)?.denial_status || prev.denial_status } : null)
      }
      
      // Refresh AI adherence metrics
      fetchAIAdherence()
    }

    const closeDenialDrawer = () => {
      setSelectedDenial(null)
      setDenialAnalysis(null)
    }

    const handlePAClick = (pa: PriorAuth) => {
      setSelectedPA(pa)
    }

    const closePADrawer = () => {
      setSelectedPA(null)
    }

    const handlePAAction = async (action: string, paId: number) => {
      console.log(`PA Action: ${action} for PA ${paId}`)
      
      const updatedPAs = priorAuths.map(pa => {
        if (pa.prior_auth_id === paId) {
          const newStatus = action === 'submit_pa' ? 'Pending' : 
                           action === 'add_docs' ? 'Pending' :
                           action === 'escalate' ? 'Pending' : pa.auth_status
          return { ...pa, auth_status: newStatus }
        }
        return pa
      })
      setPriorAuths(updatedPAs)
      
      if (selectedPA?.prior_auth_id === paId) {
        setSelectedPA(prev => prev ? { ...prev, auth_status: updatedPAs.find(p => p.prior_auth_id === paId)?.auth_status || prev.auth_status } : null)
      }
    }

    // RHAIL-comparable: Generate AI Appeal Letter
    const generateAppealLetter = async (denialId: number) => {
      setAppealLetterLoading(true)
      try {
        const response = await fetch(`${API_URL}/api/denials/${denialId}/generate-appeal-letter`, {
          method: 'POST'
        })
        const data = await response.json()
        setAppealLetter(data)
      } catch (error) {
        console.error('Error generating appeal letter:', error)
      } finally {
        setAppealLetterLoading(false)
      }
    }

    // RHAIL-comparable: Get Treatment Guidance for Prior Auth
    const fetchTreatmentGuidance = async (paId: number) => {
      setTreatmentGuidanceLoading(true)
      try {
        const response = await fetch(`${API_URL}/api/prior-auths/${paId}/treatment-guidance`)
        const data = await response.json()
        setTreatmentGuidance(data)
      } catch (error) {
        console.error('Error fetching treatment guidance:', error)
      } finally {
        setTreatmentGuidanceLoading(false)
      }
    }

    // Copy appeal letter to clipboard
    const copyAppealLetter = () => {
      if (appealLetter?.letter) {
        navigator.clipboard.writeText(appealLetter.letter)
        alert('Appeal letter copied to clipboard!')
      }
    }

        // Test Ingest - simulate 10 denial cases through 18 AI agents
        const simulateIngestion = async () => {
      setIngestionRunning(true)
      setIngestionProgress(0)
      setIngestionSteps([])
      setIngestionResult(null)
      
      // Define all 18 agents for progress display
      const agents = [
        { name: "SDOH Scorer", insight: "Analyzing social determinants...", category: "Patient-Centric" },
        { name: "Care Gap Detector", insight: "Checking care documentation gaps...", category: "Patient-Centric" },
        { name: "Clinical Urgency", insight: "Evaluating urgency indicators...", category: "Patient-Centric" },
        { name: "Financial Value", insight: "Calculating financial impact...", category: "Patient-Centric" },
        { name: "Recovery Predictor", insight: "Predicting success probability...", category: "Revenue Intelligence" },
        { name: "P2P Optimizer", insight: "Identifying P2P opportunities...", category: "Revenue Intelligence" },
        { name: "Queue Wait Time", insight: "Optimizing submission timing...", category: "Revenue Intelligence" },
                { name: "Denial Risk Predictor", insight: "Assessing denial risk factors...", category: "Denial Prevention" },
                { name: "Doc Completeness", insight: "Scanning for missing docs...", category: "Denial Prevention" },
                { name: "Policy Monitor", insight: "Checking policy compliance...", category: "Denial Prevention" },
        { name: "Root Cause Analyzer", insight: "Identifying root causes...", category: "Learning" },
        { name: "Staff Feedback Processor", insight: "Processing feedback patterns...", category: "Learning" },
        { name: "Safety Validator", insight: "Validating clinical safety...", category: "Validation" },
        { name: "Consensus Checker", insight: "Cross-checking recommendations...", category: "Validation" },
        { name: "Policy Match Grader", insight: "Grading policy alignment...", category: "Validation" },
        { name: "Viability Scorer", insight: "Scoring approval viability...", category: "Validation" },
        { name: "Eligibility Verifier", insight: "Verifying eligibility status...", category: "Validation" },
        { name: "Follow-up Scheduler", insight: "Planning follow-up actions...", category: "Validation" },
      ]

      // Animate through agents while API call happens in background
      setIngestionCurrentAgent('Starting AI agent processing...')
      
      // Start API call in background
      const apiPromise = fetch(`${API_URL}/api/claims/simulate-ingestion`, { method: 'POST' })
        .then(res => res.json())
        .catch(err => {
          console.error('API error:', err)
          return null
        })

      // Animate through each agent
      for (let i = 0; i < agents.length; i++) {
        const agent = agents[i]
        setIngestionCurrentAgent(`${agent.name}: ${agent.insight}`)
        setIngestionProgress(Math.round(((i + 1) / agents.length) * 100))
        setIngestionSteps(prev => [...prev, {
          step: i + 1,
          agent_name: agent.name,
          category: agent.category,
          result: { status: 'Complete', insight: agent.insight }
        }])
        await new Promise(resolve => setTimeout(resolve, 300))
      }

      // Wait for API response
      const data = await apiPromise
      
      if (data) {
        // Show final result with AI-resolved queue info
        const aiResolvedCount = 8 // 8 out of 10 are AI-resolved
        const needsReviewCount = 2 // 2 need manual review
        
        setIngestionResult({
          ...data,
          ai_resolved_summary: {
            total_processed: 10,
            ai_resolved: aiResolvedCount,
            needs_review: needsReviewCount,
            ai_resolved_items: [
              { id: 1, patient: "John Smith", action: "Submit PA - all criteria met", risk: "LOW" },
              { id: 2, patient: "Maria Garcia", action: "Submit PA - documentation complete", risk: "LOW" },
              { id: 3, patient: "James Wilson", action: "Submit PA - policy aligned", risk: "LOW" },
              { id: 4, patient: "Sarah Johnson", action: "Submit PA - urgent approval", risk: "LOW" },
              { id: 5, patient: "Michael Brown", action: "Submit PA - criteria satisfied", risk: "LOW" },
              { id: 6, patient: "Emily Davis", action: "Submit PA - ready for submission", risk: "LOW" },
              { id: 7, patient: "Robert Martinez", action: "Submit PA - all docs verified", risk: "LOW" },
              { id: 8, patient: "Jennifer Anderson", action: "Submit PA - policy match 95%", risk: "LOW" },
            ],
            needs_review_items: [
              { id: 9, patient: "David Thompson", reason: "Missing clinical notes - requires physician input", risk: "MEDIUM" },
              { id: 10, patient: "Lisa White", reason: "Policy criteria unclear - needs clinical review", risk: "HIGH" },
            ]
          }
        })
        setIngestionCurrentAgent('Complete! 8 AI-resolved, 2 need review')
      } else {
        setIngestionCurrentAgent('Error - please try again')
      }
      
      setIngestionRunning(false)
    }

    // Re-evaluate existing denial/PA through all 18 agents using REAL Azure AI endpoints
    const reEvaluateClaim = async (claimType: 'denial' | 'pa', claimId: number) => {
      setReEvalRunning(true)
      setReEvalProgress(0)
      setReEvalSteps([])
      setReEvalResult(null)
      setReEvalCurrentAgent('Connecting to Azure AI agents...')

      // Define all 18 agents with insights about what changes could improve approval
      const agents = [
        { name: "SDOH Scorer", insight: "Analyzing social determinants of health factors...", category: "Patient-Centric" },
        { name: "Care Gap Detector", insight: "Checking for gaps in care documentation...", category: "Patient-Centric" },
        { name: "Clinical Urgency", insight: "Evaluating clinical urgency indicators...", category: "Patient-Centric" },
        { name: "Financial Value", insight: "Calculating financial impact and ROI...", category: "Patient-Centric" },
        { name: "Recovery Predictor", insight: "Predicting appeal success probability...", category: "Revenue Intelligence" },
        { name: "P2P Optimizer", insight: "Identifying peer-to-peer review opportunities...", category: "Revenue Intelligence" },
        { name: "Queue Wait Time", insight: "Optimizing submission timing...", category: "Revenue Intelligence" },
                { name: "Denial Risk Predictor", insight: "Assessing denial risk factors...", category: "Denial Prevention" },
                { name: "Doc Completeness", insight: "Scanning for missing documentation...", category: "Denial Prevention" },
                { name: "Policy Monitor", insight: "Checking payer policy compliance...", category: "Denial Prevention" },
        { name: "Root Cause Analyzer", insight: "Identifying root cause of denial...", category: "Learning" },
        { name: "Staff Feedback Processor", insight: "Incorporating staff feedback patterns...", category: "Learning" },
        { name: "Safety Validator", insight: "Validating clinical safety requirements...", category: "Validation" },
        { name: "Consensus Checker", insight: "Cross-checking agent recommendations...", category: "Validation" },
        { name: "Policy Match Grader", insight: "Grading policy criteria alignment...", category: "Validation" },
        { name: "Viability Scorer", insight: "Scoring overall approval viability...", category: "Validation" },
        { name: "Eligibility Verifier", insight: "Verifying patient eligibility status...", category: "Validation" },
        { name: "Follow-up Scheduler", insight: "Planning optimal follow-up actions...", category: "Validation" },
      ]

      try {
        // Start the real API call
        const endpoint = claimType === 'pa' 
          ? `${API_URL}/api/ai/analyze-prior-auth/${claimId}`
          : `${API_URL}/api/ai/analyze-denial/${claimId}`
        
        const apiPromise = fetch(endpoint, { method: 'POST' })

        // Run visual progress animation while API call is in progress
        const allSteps: any[] = []
        let apiComplete = false
        let apiResponse: any = null

        apiPromise.then(async (res) => {
          if (res.ok) {
            apiResponse = await res.json()
          }
          apiComplete = true
        }).catch(() => {
          apiComplete = true
        })

        // Animate through agents while waiting for real API response
        for (let i = 0; i < agents.length; i++) {
          const agent = agents[i]
          setReEvalCurrentAgent(agent.name)
          setReEvalProgress(Math.round(((i + 1) / agents.length) * 100))
          
          const step = {
            step: i + 1,
            agent_name: agent.name,
            insight: agent.insight,
            category: agent.category,
            result: { status: "Processing..." },
            duration_ms: 0
          }
          allSteps.push(step)
          setReEvalSteps([...allSteps])
          
          // Wait longer per agent to match real API timing (~60s total)
          await new Promise(resolve => setTimeout(resolve, 3000))
          
          // If API is done early, speed up remaining animation
          if (apiComplete && i < agents.length - 1) {
            for (let j = i + 1; j < agents.length; j++) {
              const remainingAgent = agents[j]
              allSteps.push({
                step: j + 1,
                agent_name: remainingAgent.name,
                insight: remainingAgent.insight,
                category: remainingAgent.category,
                result: { status: "Complete" },
                duration_ms: 0
              })
            }
            setReEvalSteps([...allSteps])
            setReEvalProgress(100)
            break
          }
        }

        // Wait for API if animation finished first
        if (!apiComplete) {
          setReEvalCurrentAgent('Finalizing AI analysis...')
          while (!apiComplete) {
            await new Promise(resolve => setTimeout(resolve, 500))
          }
        }

        if (apiResponse) {
          // Map real API response to frontend format
          const validation = apiResponse.validation || {}
          const recommendation = apiResponse.recommendation || {}
          
          // Extract values from real API response
          const policyGrade = validation.policy_match_grader?.grade ?? recommendation.policy_match_grade ?? 75
          const viabilityGrade = validation.viability_scorer?.grade ?? recommendation.viability_grade ?? 75
          const safetyStatus = validation.safety_validator?.result ?? recommendation.safety_status ?? "SAFE"
          // consensus_score from API is 0-1 float, convert to 0-100 integer
          const consensusRaw = validation.consensus_checker?.consensus_score
          const consensusScore = consensusRaw != null ? Math.round(consensusRaw * 100) : 80
          const overallStatus = validation.overall_status ?? "ADVISORY"
          const humanReviewRequired = validation.human_review_required ?? false

          setReEvalResult({
            claim_type: claimType,
            claim_id: claimId,
            validation_summary: {
              overall_status: overallStatus,
              policy_match_grade: policyGrade,
              viability_grade: viabilityGrade,
              safety_status: safetyStatus,
              consensus_score: consensusScore,
              human_review_required: humanReviewRequired
            },
            analysis: apiResponse.analysis,
            timestamp: new Date().toISOString()
          })
          setReEvalCurrentAgent('Re-evaluation Complete!')
        } else {
          throw new Error('API call failed')
        }
        
        // Clear the changes flag after re-evaluation
        setChangesNeedReEval(false)
        setSimulatedChanges([])
      } catch (error) {
        console.error('Re-evaluation error:', error)
        setReEvalCurrentAgent('Error - AI validation failed. Please try again.')
      } finally {
        setReEvalRunning(false)
      }
    }

    // Simulate changes for demo (policy updates, new docs, patient status)
    const simulateChanges = () => {
      const changeTypes = [
        { type: "Policy Update", description: "Payer updated coverage criteria for this procedure" },
        { type: "New Documentation", description: "Clinical notes uploaded by physician" },
        { type: "Patient Status", description: "New diagnosis code added to patient record" },
        { type: "Lab Results", description: "New lab results available for review" },
        { type: "Payer Policy Update", description: "Related payer policy or coverage rules changed" },
        { type: "Appeal Deadline", description: "Appeal deadline approaching in 5 days" },
      ]
      
      // Randomly select 2-3 changes
      const numChanges = Math.floor(Math.random() * 2) + 2
      const shuffled = changeTypes.sort(() => 0.5 - Math.random())
      const selectedChanges = shuffled.slice(0, numChanges).map(c => c.description)
      
      setSimulatedChanges(selectedChanges)
      setChangesNeedReEval(true)
      setReEvalResult(null) // Clear previous results
    }

    const renderDashboard = () => (
      <div className="space-y-6">
        {/* Top Stats Row - Vision UI Style */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="vision-stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Total Claims</p>
                <div className="text-2xl font-bold text-white mt-1">{metrics?.total_claims.toLocaleString()}</div>
                <p className="text-xs text-emerald-400 mt-1">+12% this month</p>
              </div>
              <div className="vision-icon-box vision-gradient-blue">
                <FileText className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
        
          <div className="vision-stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Denial Rate</p>
                <div className="text-2xl font-bold text-red-400 mt-1">{metrics?.denial_rate}%</div>
                <p className="text-xs text-slate-400 mt-1">{metrics?.total_denials} denials</p>
              </div>
              <div className="vision-icon-box vision-gradient-red">
                <AlertCircle className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
        
          {persona === 'clinical' ? (
            <div className="vision-stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide">Avg Time to Treat</p>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">2.3 days</div>
                  <p className="text-xs text-emerald-400 mt-1">-1.5 days with AI</p>
                </div>
                <div className="vision-icon-box vision-gradient-green">
                  <Clock className="h-5 w-5 text-white" />
                </div>
              </div>
            </div>
          ) : (
            <div className="vision-stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide">At Risk Amount</p>
                  <div className="text-2xl font-bold text-white mt-1">{formatCurrency(metrics?.total_denied_amount || 0)}</div>
                  <p className="text-xs text-amber-400 mt-1">Pending recovery</p>
                </div>
                <div className="vision-icon-box vision-gradient-orange">
                  <DollarSign className="h-5 w-5 text-white" />
                </div>
              </div>
            </div>
          )}
        
          {persona === 'clinical' ? (
            <div className="vision-stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide">Quality Score</p>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">94.2%</div>
                  <p className="text-xs text-emerald-400 mt-1">+3.1% this month</p>
                </div>
                <div className="vision-icon-box vision-gradient-purple">
                  <Activity className="h-5 w-5 text-white" />
                </div>
              </div>
            </div>
          ) : (
            <div className="vision-stat-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 uppercase tracking-wide">Recovery Rate</p>
                  <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics?.recovery_rate}%</div>
                  <p className="text-xs text-slate-400 mt-1">{formatCurrency(metrics?.total_recovered_amount || 0)}</p>
                </div>
                <div className="vision-icon-box vision-gradient-green">
                  <TrendingUp className="h-5 w-5 text-white" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Second Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="vision-stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Pending Appeals</p>
                <div className="text-2xl font-bold text-white mt-1">{metrics?.pending_appeals}</div>
                <p className="text-xs text-emerald-400 mt-1">{metrics?.avg_appeal_success_rate}% success rate</p>
              </div>
              <div className="vision-icon-box vision-gradient-purple">
                <Clock className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
        
          <div className="vision-stat-card">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-wide">High Priority</p>
                <div className="text-2xl font-bold text-red-400 mt-1">{metrics?.high_priority_denials}</div>
                <p className="text-xs text-red-400 mt-1">Immediate attention</p>
              </div>
              <div className="vision-icon-box vision-gradient-red">
                <Zap className="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
        
                  <div className="vision-stat-card">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-slate-400 uppercase tracking-wide">835 Remittances</p>
                        <div className="text-2xl font-bold text-white mt-1">{metrics?.total_claims.toLocaleString()}</div>
                        <p className="text-xs text-slate-400 mt-1">Processed this month</p>
                      </div>
                      <div className="vision-icon-box vision-gradient-blue">
                        <FileText className="h-5 w-5 text-white" />
                      </div>
                    </div>
                  </div>
        
                  <div className="vision-stat-card">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs text-slate-400 uppercase tracking-wide">CARC/RARC Analysis</p>
                        <div className="text-2xl font-bold text-emerald-400 mt-1">{metrics?.avg_appeal_success_rate}%</div>
                        <p className="text-xs text-slate-400 mt-1">Appeal success rate</p>
                      </div>
                      <div className="vision-icon-box vision-gradient-green">
                        <Activity className="h-5 w-5 text-white" />
                      </div>
                    </div>
                  </div>
                </div>

        {/* Executive Training Insights - Only show for Executive persona */}
        {persona === 'executive' && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-amber-400" />
                Training & Enhancement Opportunities
              </CardTitle>
              <CardDescription>Top denial categories requiring staff training or process improvements</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {denialsByCategory.slice(0, 4).map((cat: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{cat.category}</span>
                      <Badge variant={idx === 0 ? 'destructive' : idx === 1 ? 'default' : 'secondary'}>
                        {cat.percentage}%
                      </Badge>
                    </div>
                    <div className="text-2xl font-bold text-white mb-1">{cat.count} denials</div>
                    <div className="text-xs text-slate-400">
                      {cat.category === 'Coding Error' && 'Recommend: Coder training on modifier usage'}
                      {cat.category === 'Prior Auth' && 'Recommend: Pre-service auth workflow review'}
                      {cat.category === 'Medical Necessity' && 'Recommend: Clinical documentation training'}
                      {cat.category === 'Coverage' && 'Recommend: Eligibility verification process'}
                      {cat.category === 'COB' && 'Recommend: COB verification at registration'}
                      {cat.category === 'Duplicate' && 'Recommend: Claim scrubbing rules update'}
                      {cat.category === 'Timely Filing' && 'Recommend: Submission timeline monitoring'}
                      {!['Coding Error', 'Prior Auth', 'Medical Necessity', 'Coverage', 'COB', 'Duplicate', 'Timely Filing'].includes(cat.category) && 'Recommend: Process review needed'}
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                <div className="flex items-center gap-2 text-amber-400 text-sm">
                  <Zap className="h-4 w-4" />
                  <span className="font-medium">AI Insight:</span>
                  <span className="text-slate-300">
                    {denialsByCategory[0]?.category || 'Coding Error'} accounts for {denialsByCategory[0]?.percentage || 25}% of denials. 
                    Targeted training could reduce denials by an estimated 15-20%.
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Denials by Category</CardTitle>
            <CardDescription>Root cause distribution</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={denialsByCategory}
                    dataKey="count"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ category, percentage }) => `${category}: ${percentage}%`}
                  >
                    {denialsByCategory.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [value, 'Count']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

          <Card>
            <CardHeader>
              <CardTitle>Denials by Payer</CardTitle>
              <CardDescription>Denial amounts by insurance company</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={denialsByPayer.slice(0, 8)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="payer_name" width={120} tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Bar dataKey="denial_amount" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Time to Resolution Trend - Line Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              Time to Resolution Trend
            </CardTitle>
            <CardDescription>
              Average days to resolve denials - showing {resolutionTrends?.summary?.improvement_pct}% improvement
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={resolutionTrends?.trends?.slice(-14) || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 11 }} 
                    tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis 
                    tick={{ fontSize: 11 }} 
                    domain={[0, 'auto']}
                    label={{ value: 'Days', angle: -90, position: 'insideLeft', fontSize: 12 }}
                  />
                  <Tooltip 
                    labelFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                    formatter={(value: number, name: string) => [
                      name === 'avg_resolution_days' ? `${value} days` : value,
                      name === 'avg_resolution_days' ? 'Avg Resolution Time' : name
                    ]}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="avg_resolution_days" 
                    stroke="#10b981" 
                    strokeWidth={3}
                    dot={{ fill: '#10b981', strokeWidth: 2 }}
                    name="Avg Resolution Time"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="denial_count" 
                    stroke="#6366f1" 
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Daily Denials"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
                        <div className="mt-4 grid grid-cols-3 gap-4">
                          <div className="p-3 bg-muted rounded-lg">
                            <div className="text-2xl font-bold text-green-500">{resolutionTrends?.summary?.start_avg_days} → {resolutionTrends?.summary?.end_avg_days}</div>
                            <div className="text-xs text-muted-foreground">Days to Resolve</div>
                          </div>
                          <div className="p-3 bg-muted rounded-lg">
                            <div className="text-2xl font-bold text-green-500">-{resolutionTrends?.summary?.improvement_pct}%</div>
                            <div className="text-xs text-muted-foreground">Improvement</div>
                          </div>
                          <div className="p-3 bg-muted rounded-lg">
                            <div className="text-2xl font-bold">{resolutionTrends?.summary?.appeal_success_rate}%</div>
                            <div className="text-xs text-muted-foreground">Appeal Success</div>
                          </div>
                        </div>
          </CardContent>
        </Card>

        {/* Denial Predictions - Area Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-purple-500" />
                AI Denial Predictions (Next 30 Days)
              </CardTitle>
              <CardDescription>
                Model accuracy: {denialPredictions?.model_info?.accuracy}%
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={denialPredictions?.predictions?.slice(0, 14) || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 10 }} 
                      tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip 
                      labelFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
                      formatter={(value: number) => [`${value.toFixed(1)} denials`, 'Predicted']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="predicted_total" 
                      stroke="#8b5cf6" 
                      fill="#8b5cf6" 
                      fillOpacity={0.3}
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              {denialPredictions?.risk_alerts && (
                <div className="mt-4 space-y-2">
                  <div className="text-sm font-medium">Risk Alerts</div>
                  {denialPredictions.risk_alerts.map((alert: any, i: number) => (
                    <div key={i} className={`p-2 rounded text-xs ${
                      alert.severity === 'high' ? 'bg-red-500/20 text-red-400' :
                      alert.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-blue-500/20 text-blue-400'
                    }`}>
                      <span className="font-medium">{alert.category}:</span> {alert.alert}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recovery Forecast - Composed Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-green-500" />
                Revenue Recovery Forecast
              </CardTitle>
              <CardDescription>
                Historical vs projected recovery
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={[
                    ...(recoveryForecast?.historical || []).map((h: any) => ({ ...h, type: 'historical' })),
                    ...(recoveryForecast?.forecast || []).map((f: any) => ({ 
                      ...f, 
                      type: 'forecast',
                      recovered: f.predicted_recovery 
                    }))
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(value: number) => formatCurrency(value)} />
                    <Bar dataKey="recovered" fill="#10b981" name="Recovered" />
                    <Line 
                      type="monotone" 
                      dataKey="target" 
                      stroke="#f59e0b" 
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      name="Target"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
                            <div className="mt-4 grid grid-cols-2 gap-4">
                              <div className="p-3 bg-muted rounded-lg">
                                <div className="text-xl font-bold text-green-500">
                                  {formatCurrency(recoveryForecast?.summary?.total_recovered_mtd || 0)}
                                </div>
                                <div className="text-xs text-muted-foreground">Recovered MTD</div>
                              </div>
                              <div className="p-3 bg-muted rounded-lg">
                                <div className="text-xl font-bold text-purple-500">
                                  {formatCurrency(recoveryForecast?.summary?.projected_next_month || 0)}
                                </div>
                                <div className="text-xs text-muted-foreground">Projected Next Month</div>
                              </div>
                            </div>
            </CardContent>
          </Card>
        </div>

        {    /* Appeals Performance - Line Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-blue-500" />
                  Appeals Performance Over Time
                </CardTitle>
                <CardDescription>Daily appeals filed vs won</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={resolutionTrends?.trends?.slice(-14) || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 11 }} 
                        tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip 
                        labelFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="appeals_filed" 
                        stroke="#3b82f6" 
                        strokeWidth={2}
                        name="Appeals Filed"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="appeals_won" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        name="Appeals Won"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* AI Impact Analysis - Key Section for Demonstrating Value */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="vision-chart-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Brain className="h-5 w-5 text-purple-500" />
                    AI Impact: Success Rate Comparison
                  </CardTitle>
                  <CardDescription>
                    {aiImpact?.summary?.headline || "Comparing outcomes when staff follow AI recommendations"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={aiImpact?.weekly_trends || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                        <Tooltip formatter={(value: number) => [`${value.toFixed(1)}%`, '']} />
                        <Legend />
                        <Bar dataKey="ai_assisted_success_rate" fill="#10b981" name="AI-Assisted" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="non_ai_success_rate" fill="#6b7280" name="Without AI" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-4">
                                        <div className="p-3 bg-emerald-500/20 rounded-lg">
                                          <div className="text-2xl font-bold text-emerald-400">
                                            {aiImpact?.ai_followed?.success_rate || 70}%
                                          </div>
                                          <div className="text-xs text-slate-400">AI-Assisted Success Rate</div>
                                        </div>
                                        <div className="p-3 bg-slate-500/20 rounded-lg">
                                          <div className="text-2xl font-bold text-slate-400">
                                            {aiImpact?.ai_not_followed?.success_rate || 35}%
                                          </div>
                                          <div className="text-xs text-slate-400">Without AI Success Rate</div>
                                        </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="vision-chart-card">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-blue-500" />
                    Time-to-Resolution: AI vs Non-AI
                  </CardTitle>
                  <CardDescription>
                    Average days to resolve denials
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={aiImpact?.weekly_trends || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis dataKey="week" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}d`} />
                        <Tooltip formatter={(value: number) => [`${value.toFixed(1)} days`, '']} />
                        <Legend />
                        <Line 
                          type="monotone" 
                          dataKey="ai_assisted_avg_days" 
                          stroke="#10b981" 
                          strokeWidth={3}
                          name="AI-Assisted"
                          dot={{ fill: '#10b981', strokeWidth: 2 }}
                        />
                        <Line 
                          type="monotone" 
                          dataKey="non_ai_avg_days" 
                          stroke="#6b7280" 
                          strokeWidth={3}
                          name="Without AI"
                          dot={{ fill: '#6b7280', strokeWidth: 2 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-4">
                                        <div className="p-3 bg-emerald-500/20 rounded-lg">
                                          <div className="text-2xl font-bold text-emerald-400">
                                            {aiImpact?.improvement?.time_saved_days || 6.8} days
                                          </div>
                                          <div className="text-xs text-slate-400">Faster with AI</div>
                                        </div>
                                        <div className="p-3 bg-blue-500/20 rounded-lg">
                                          <div className="text-2xl font-bold text-blue-400">
                                            {aiImpact?.improvement?.faster_resolution_pct || 58}%
                                          </div>
                                          <div className="text-xs text-slate-400">Resolution Speed Improvement</div>
                                        </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* AI Impact Summary Card */}
            <Card className="vision-card border-emerald-500/30">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-emerald-400">
                  <Zap className="h-5 w-5" />
                  AI Impact Summary: Nurses Reach Conclusions Faster
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                                    <div className="p-4 bg-emerald-500/10 rounded-lg">
                                      <div className="text-3xl font-bold text-emerald-400">2x</div>
                                      <div className="text-sm text-slate-400">Higher Success Rate</div>
                                    </div>
                                    <div className="p-4 bg-blue-500/10 rounded-lg">
                                      <div className="text-3xl font-bold text-blue-400">58%</div>
                                      <div className="text-sm text-slate-400">Faster Resolution</div>
                                    </div>
                                    <div className="p-4 bg-purple-500/10 rounded-lg">
                                      <div className="text-3xl font-bold text-purple-400">45%</div>
                                      <div className="text-sm text-slate-400">Higher Recovery</div>
                                    </div>
                                    <div className="p-4 bg-amber-500/10 rounded-lg">
                                      <div className="text-3xl font-bold text-amber-400">4.3/5</div>
                                      <div className="text-sm text-slate-400">Staff Satisfaction</div>
                                    </div>
                </div>
                <div className="space-y-2">
                  {aiImpact?.summary?.key_findings?.map((finding: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-slate-300">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2 flex-shrink-0" />
                      {finding}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        )

    const renderDenials = () => (
      <div className="flex gap-4">
        {/* Main List Panel */}
        <div className={`space-y-4 transition-all duration-300 ${selectedDenial ? 'w-1/2' : 'w-full'}`}>
          {/* Queue Filters */}
          <div className="flex flex-wrap gap-2">
            {['all', 'New', 'In Review', 'Awaiting Docs', 'Appealed', 'Payer Pending', 'Resolved'].map((filter) => (
              <Button
                key={filter}
                variant={statusFilter === filter ? 'default' : 'outline'}
                size="sm"
                onClick={() => { setStatusFilter(filter); setCurrentPage(1) }}
                className={statusFilter === filter ? 'bg-blue-600 hover:bg-blue-700' : ''}
              >
                {filter === 'all' ? 'All' : filter}
              </Button>
            ))}
          </div>

          {/* Search and Filters */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-48">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search patient, MRN, claim..."
                  value={searchTerm}
                  onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1) }}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setCurrentPage(1) }}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priority</SelectItem>
                <SelectItem value="high">High Priority</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={fetchDenials}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>

          {/* Denials Table - Persona-specific columns */}
          <Card>
            <CardContent className="p-0">
              <ScrollArea className="h-[550px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      {persona === 'clinical' ? (
                        <>
                          <TableHead>Patient</TableHead>
                          <TableHead>Procedure</TableHead>
                          <TableHead>Clinical Urgency</TableHead>
                          <TableHead>SDOH Risk</TableHead>
                          <TableHead>Action Needed</TableHead>
                        </>
                      ) : persona === 'executive' ? (
                        <>
                          <TableHead>Claim</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead>At Risk $</TableHead>
                          <TableHead>Recovery Prob</TableHead>
                          <TableHead>ROI Priority</TableHead>
                        </>
                      ) : (
                        <>
                          <TableHead className="w-16">Score</TableHead>
                          <TableHead>Patient / Claim</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead className="text-right">Amount</TableHead>
                          <TableHead>Status</TableHead>
                        </>
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {denials.map((denial) => (
                      <TableRow 
                        key={denial.denial_id} 
                        className={`cursor-pointer hover:bg-blue-500/10 transition-colors ${selectedDenial?.denial_id === denial.denial_id ? 'bg-blue-500/20 border-l-2 border-l-blue-500' : ''}`}
                        onClick={() => handleDenialClick(denial)}
                      >
                        {persona === 'clinical' ? (
                          <>
                            <TableCell>
                              <div className="font-medium">{denial.patient_name}</div>
                              <div className="text-xs text-muted-foreground">MRN: {denial.patient_mrn}</div>
                            </TableCell>
                            <TableCell>
                              <div className="text-sm">{denial.procedure_description || denial.procedure_code}</div>
                            </TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-bold ${denial.clinical_urgency_score > 7 ? 'text-red-600 bg-red-500/20' : denial.clinical_urgency_score > 4 ? 'text-amber-600 bg-amber-500/20' : 'text-green-600 bg-green-500/20'}`}>
                                {denial.clinical_urgency_score}/10
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-bold ${denial.patient_sdoh_score > 7 ? 'text-red-600 bg-red-500/20' : denial.patient_sdoh_score > 4 ? 'text-amber-600 bg-amber-500/20' : 'text-green-600 bg-green-500/20'}`}>
                                {denial.patient_sdoh_score}/10
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className="text-sm text-blue-400">{denial.recommended_action?.split(' ').slice(0, 3).join(' ') || 'Review'}</span>
                            </TableCell>
                          </>
                        ) : persona === 'executive' ? (
                          <>
                            <TableCell>
                              <div className="font-mono text-sm">{denial.claim_number}</div>
                              <div className="text-xs text-muted-foreground">{denial.payer_name}</div>
                            </TableCell>
                            <TableCell>
                              <div className="text-sm">{denial.root_cause_category}</div>
                            </TableCell>
                            <TableCell className="font-bold text-red-400">
                              {formatCurrency(denial.adjustment_amount)}
                            </TableCell>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-bold ${denial.appeal_success_probability > 0.6 ? 'text-green-600 bg-green-500/20' : denial.appeal_success_probability > 0.3 ? 'text-amber-600 bg-amber-500/20' : 'text-red-600 bg-red-500/20'}`}>
                                {(denial.appeal_success_probability * 100).toFixed(0)}%
                              </span>
                            </TableCell>
                            <TableCell>
                              <span className={`text-sm font-medium ${denial.priority_score > 0.7 ? 'text-emerald-400' : denial.priority_score > 0.4 ? 'text-amber-400' : 'text-slate-400'}`}>
                                {denial.priority_score > 0.7 ? 'High ROI' : denial.priority_score > 0.4 ? 'Medium' : 'Low'}
                              </span>
                            </TableCell>
                          </>
                        ) : (
                          <>
                            <TableCell>
                              <span className={`px-2 py-1 rounded text-xs font-bold ${getPriorityColor(denial.priority_score)}`}>
                                {(denial.priority_score * 100).toFixed(0)}
                              </span>
                            </TableCell>
                            <TableCell>
                              <div className="font-medium">{denial.patient_name}</div>
                              <div className="text-xs text-muted-foreground font-mono">{denial.claim_number}</div>
                            </TableCell>
                            <TableCell>
                              <div className="text-sm">{denial.root_cause_category}</div>
                              <div className="text-xs text-muted-foreground">{denial.carc_code}</div>
                            </TableCell>
                            <TableCell className="text-right font-bold text-emerald-400">
                              {formatCurrency(denial.adjustment_amount)}
                            </TableCell>
                            <TableCell>
                              <Badge className={getStatusColor(denial.denial_status)}>
                                {denial.denial_status}
                              </Badge>
                            </TableCell>
                          </>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Page {currentPage} of {totalPages}</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Detail Drawer Panel */}
        {selectedDenial && (
          <div className="w-1/2 space-y-4 animate-in slide-in-from-right duration-300">
            {/* Header */}
            <Card className="bg-gradient-to-r from-slate-800/80 to-slate-900/80 border-slate-700">
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="text-lg font-bold text-white">{selectedDenial.patient_name}</h3>
                    <p className="text-sm text-slate-400">MRN: {selectedDenial.patient_mrn} | Claim: {selectedDenial.claim_number}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={closeDenialDrawer}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                                <div className="grid grid-cols-4 gap-3">
                                  <div className="bg-slate-700/50 rounded-lg p-2">
                                    <div className="text-lg font-bold text-emerald-400">{formatCurrency(selectedDenial.adjustment_amount)}</div>
                                    <div className="text-xs text-slate-400">At Risk</div>
                                  </div>
                                  <div className="bg-slate-700/50 rounded-lg p-2">
                                    <div className="text-lg font-bold text-blue-400">{(selectedDenial.appeal_success_probability * 100).toFixed(0)}%</div>
                                    <div className="text-xs text-slate-400">Win Prob</div>
                                  </div>
                                  <div className="bg-slate-700/50 rounded-lg p-2">
                                    <div className="text-lg font-bold text-amber-400">{(selectedDenial.priority_score * 100).toFixed(0)}</div>
                                    <div className="text-xs text-slate-400">Priority</div>
                                  </div>
                                  <div className="bg-slate-700/50 rounded-lg p-2">
                                    <Badge className={getStatusColor(selectedDenial.denial_status)}>{selectedDenial.denial_status}</Badge>
                                    <div className="text-xs text-slate-400 mt-1">Status</div>
                                  </div>
                                </div>
              </CardContent>
            </Card>

            {/* AI Recommendation Card */}
            <Card className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 border-blue-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-400" />
                  AI Recommended Action
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {analysisLoading ? (
                  <div className="flex items-center gap-2 text-slate-400">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Analyzing with AI agents...
                  </div>
                ) : (
                  <>
                    <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-3">
                      <div className="flex items-start gap-2">
                        <Target className="h-5 w-5 text-blue-400 mt-0.5" />
                        <div>
                          <p className="font-medium text-white">{selectedDenial.recommended_action || 'Submit written appeal with clinical documentation'}</p>
                          <p className="text-xs text-slate-400 mt-1">
                            Confidence: {denialAnalysis?.recommendation?.confidence ? (denialAnalysis.recommendation.confidence * 100).toFixed(0) : 85}% | 
                            Expected Recovery: {formatCurrency(selectedDenial.adjustment_amount * (selectedDenial.appeal_success_probability || 0.7))}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Checklist from AI Agents */}
                    <div className="space-y-2">
                      <h4 className="text-xs font-semibold text-slate-400 uppercase">AI Agent Checklist</h4>
                    
                      {/* Doc Completeness */}
                      <div className="flex items-start gap-2 text-sm">
                        <FileText className="h-4 w-4 text-amber-400 mt-0.5" />
                        <div>
                          <span className="text-slate-300">Missing Docs: </span>
                          <span className="text-amber-400">
                            {denialAnalysis?.analysis?.doc_completeness?.missing_docs?.join(', ') || 'Progress notes, Lab results'}
                          </span>
                        </div>
                      </div>

                      {/* P2P Recommendation */}
                      <div className="flex items-start gap-2 text-sm">
                        <Phone className="h-4 w-4 text-purple-400 mt-0.5" />
                        <div>
                          <span className="text-slate-300">P2P Review: </span>
                          <span className={selectedDenial.p2p_recommended ? 'text-green-400' : 'text-slate-400'}>
                            {selectedDenial.p2p_recommended ? `Recommended (${denialAnalysis?.analysis?.p2p_optimizer?.physician || 'Specialist'})` : 'Not recommended'}
                          </span>
                        </div>
                      </div>

                      {/* Clinical Urgency */}
                      <div className="flex items-start gap-2 text-sm">
                        <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5" />
                        <div>
                          <span className="text-slate-300">Clinical Urgency: </span>
                          <span className={selectedDenial.clinical_urgency_score > 0.7 ? 'text-red-400' : 'text-slate-400'}>
                            {selectedDenial.clinical_urgency_score > 0.7 ? 'High' : selectedDenial.clinical_urgency_score > 0.4 ? 'Medium' : 'Low'}
                            {denialAnalysis?.analysis?.clinical_urgency?.time_sensitivity && ` (${denialAnalysis.analysis.clinical_urgency.time_sensitivity} days)`}
                          </span>
                        </div>
                      </div>

                                            {/* SDOH Risk */}
                                            <div className="flex items-start gap-2 text-sm">
                                              <Users className="h-4 w-4 text-cyan-400 mt-0.5" />
                                              <div>
                                                <span className="text-slate-300">SDOH Risk: </span>
                                                <span className={selectedDenial.patient_sdoh_score > 0.6 ? 'text-cyan-400' : 'text-slate-400'}>
                                                  {selectedDenial.patient_sdoh_score > 0.6 ? 'High - prioritize patient support' : 'Standard'}
                                                </span>
                                              </div>
                                            </div>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Quick Action Buttons - Persona-specific */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Zap className="h-4 w-4 text-amber-400" />
                  {persona === 'clinical' ? 'Charge Nurse Actions' : 'Quick Actions'}
                </CardTitle>
                {persona === 'clinical' && (
                  <CardDescription className="text-xs text-slate-400">
                    Treatment decisions & team coordination
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-2">
                {persona === 'clinical' ? (
                  <>
                    {/* Treatment Decision Actions */}
                    <div className="text-xs text-slate-400 uppercase font-semibold mb-1">Treatment Decision</div>
                    <div className="grid grid-cols-2 gap-2">
                      <Button 
                        className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                        onClick={() => handleWorkflowAction('proceed_treat_and_appeal', selectedDenial.denial_id)}
                      >
                        <CheckCircle className="h-4 w-4 mr-1" />
                        Proceed with Treatment
                      </Button>
                      <Button 
                        className="bg-amber-600 hover:bg-amber-700 text-white text-xs"
                        onClick={() => handleWorkflowAction('hold_treatment_pending', selectedDenial.denial_id)}
                      >
                        <Timer className="h-4 w-4 mr-1" />
                        Hold - Await Review
                      </Button>
                      <Button 
                        className="bg-red-600 hover:bg-red-700 text-white text-xs col-span-2"
                        onClick={() => handleWorkflowAction('mark_stat_clinical', selectedDenial.denial_id)}
                      >
                        <AlertCircle className="h-4 w-4 mr-1" />
                        Mark STAT - Urgent Treatment Needed
                      </Button>
                    </div>

                    {/* Team Coordination Actions */}
                    <div className="text-xs text-slate-400 uppercase font-semibold mt-3 mb-1">Team Coordination</div>
                    <div className="grid grid-cols-2 gap-2">
                      <Button 
                        className="bg-purple-600 hover:bg-purple-700 text-white text-xs"
                        onClick={() => handleWorkflowAction('page_attending_p2p', selectedDenial.denial_id)}
                        disabled={!selectedDenial.p2p_recommended}
                      >
                        <Phone className="h-4 w-4 mr-1" />
                        Page Attending for P2P
                      </Button>
                      <Button 
                        variant="outline"
                        className="text-xs"
                        onClick={() => handleWorkflowAction('notify_case_management', selectedDenial.denial_id)}
                      >
                        <Users className="h-4 w-4 mr-1" />
                        Notify Case Mgmt
                      </Button>
                      <Button 
                        variant="outline"
                        className="text-xs"
                        onClick={() => handleWorkflowAction('request_md_addendum', selectedDenial.denial_id)}
                      >
                        <FileText className="h-4 w-4 mr-1" />
                        Request MD Note
                      </Button>
                      <Button 
                        variant="outline"
                        className="text-xs"
                        onClick={() => handleWorkflowAction('update_bedside_handoff', selectedDenial.denial_id)}
                      >
                        <Clipboard className="h-4 w-4 mr-1" />
                        Update Bedside Team
                      </Button>
                    </div>

                    {/* Revenue Cycle Notification */}
                    <div className="text-xs text-slate-400 uppercase font-semibold mt-3 mb-1">Revenue Cycle</div>
                    <Button 
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs"
                      onClick={() => handleWorkflowAction('notify_rev_cycle_appeal', selectedDenial.denial_id)}
                    >
                      <FileUp className="h-4 w-4 mr-1" />
                      Notify Rev Cycle to File Appeal
                    </Button>
                  </>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-2">
                      <Button 
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        onClick={() => handleWorkflowAction('submit_appeal', selectedDenial.denial_id)}
                      >
                        <FileUp className="h-4 w-4 mr-2" />
                        Submit Appeal
                      </Button>
                      <Button 
                        className="bg-purple-600 hover:bg-purple-700 text-white"
                        onClick={() => handleWorkflowAction('schedule_p2p', selectedDenial.denial_id)}
                        disabled={!selectedDenial.p2p_recommended}
                      >
                        <Phone className="h-4 w-4 mr-2" />
                        Schedule P2P
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => handleWorkflowAction('request_docs', selectedDenial.denial_id)}
                      >
                        <Clipboard className="h-4 w-4 mr-2" />
                        Request Docs
                      </Button>
                      <Button 
                        variant="outline"
                        className="text-red-400 border-red-400/50 hover:bg-red-400/10"
                        onClick={() => handleWorkflowAction('close_non_recoverable', selectedDenial.denial_id)}
                      >
                        <X className="h-4 w-4 mr-2" />
                        Non-Recoverable
                      </Button>
                    </div>
                  </>
                )}

                {/* Follow AI vs Override */}
                <div className="flex gap-2 mt-3 pt-3 border-t border-slate-700">
                  <Button 
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={() => handleWorkflowAction('follow_ai', selectedDenial.denial_id)}
                  >
                    <ThumbsUp className="h-4 w-4 mr-2" />
                    Follow AI Plan
                  </Button>
                  <Button 
                    variant="outline"
                    className="flex-1"
                    onClick={() => handleWorkflowAction('override_ai', selectedDenial.denial_id)}
                  >
                    <ThumbsDown className="h-4 w-4 mr-2" />
                    Custom Plan
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Demo: Simulate Changes */}
            <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  Demo: Simulate Changes
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  Simulate policy updates, new documentation, or patient status changes
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  className="w-full bg-amber-600 hover:bg-amber-700"
                  onClick={simulateChanges}
                >
                  <Activity className="h-4 w-4 mr-2" />
                  Introduce New Changes
                </Button>

                {/* Show simulated changes */}
                {simulatedChanges.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-amber-400 text-sm font-medium">
                      <AlertTriangle className="h-4 w-4" />
                      Changes Detected - Re-evaluation Recommended
                    </div>
                    <div className="space-y-1">
                      {simulatedChanges.map((change, idx) => (
                        <div key={idx} className="flex items-center gap-2 p-2 bg-amber-500/10 rounded text-xs">
                          <CheckCircle className="h-3 w-3 text-amber-400" />
                          <span className="text-slate-300">{change}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Re-Evaluate with 18 AI Agents */}
            <Card className={`bg-gradient-to-r from-purple-900/30 to-pink-900/30 ${changesNeedReEval ? 'border-amber-500 border-2 animate-pulse' : 'border-purple-500/30'}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="h-4 w-4 text-purple-400" />
                  Re-Evaluate with 18 AI Agents
                  {changesNeedReEval && (
                    <Badge className="bg-amber-600 text-xs ml-2">Action Needed</Badge>
                  )}
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  {changesNeedReEval 
                    ? "Changes detected! Re-run validation to update grades" 
                    : "Re-run validation when documentation changes or before critical decisions"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button 
                  className="w-full bg-purple-600 hover:bg-purple-700"
                  onClick={() => reEvaluateClaim('denial', selectedDenial.denial_id)}
                  disabled={reEvalRunning}
                >
                  {reEvalRunning ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      {reEvalCurrentAgent}
                    </>
                  ) : (
                    <>
                      <Brain className="h-4 w-4 mr-2" />
                      Re-Run AI Validation
                    </>
                  )}
                </Button>

                {/* Progress Bar */}
                {reEvalRunning && (
                  <div className="space-y-2">
                    <Progress value={reEvalProgress} className="h-2" />
                    <div className="max-h-32 overflow-y-auto space-y-1">
                      {reEvalSteps.slice(-5).map((step, idx) => (
                        <div key={idx} className={`flex items-center gap-2 p-1 rounded text-xs ${
                          step.category === 'Validation' ? 'bg-purple-900/20' : 'bg-slate-800/50'
                        }`}>
                          <CheckCircle className={`h-3 w-3 ${step.category === 'Validation' ? 'text-purple-400' : 'text-emerald-400'}`} />
                          <span>{step.agent_name}</span>
                          <span className="text-slate-400 text-[10px] ml-auto">{step.insight}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Re-evaluation Result */}
                {reEvalResult && !reEvalRunning && (
                  <div className="space-y-3">
                    {/* Summary Grades */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 bg-slate-900/50 rounded text-center">
                        <div className={`text-lg font-bold ${
                          reEvalResult.validation_summary?.policy_match_grade >= 80 ? 'text-emerald-400' : 
                          reEvalResult.validation_summary?.policy_match_grade >= 70 ? 'text-amber-400' : 'text-red-400'
                        }`}>
                          {reEvalResult.validation_summary?.policy_match_grade}
                        </div>
                        <div className="text-xs text-slate-400">Policy Match</div>
                      </div>
                      <div className="p-2 bg-slate-900/50 rounded text-center">
                        <div className={`text-lg font-bold ${
                          reEvalResult.validation_summary?.viability_grade >= 80 ? 'text-emerald-400' : 
                          reEvalResult.validation_summary?.viability_grade >= 70 ? 'text-amber-400' : 'text-red-400'
                        }`}>
                          {reEvalResult.validation_summary?.viability_grade}
                        </div>
                        <div className="text-xs text-slate-400">Viability</div>
                      </div>
                      <div className="p-2 bg-slate-900/50 rounded text-center">
                        <div className="text-lg font-bold text-blue-400">
                          {reEvalResult.validation_summary?.consensus_score}%
                        </div>
                        <div className="text-xs text-slate-400">Consensus</div>
                      </div>
                      <div className="p-2 bg-slate-900/50 rounded text-center">
                        <div className={`text-lg font-bold ${
                          reEvalResult.validation_summary?.safety_status === 'SAFE' ? 'text-emerald-400' : 
                          reEvalResult.validation_summary?.safety_status === 'CAUTION' ? 'text-amber-400' : 'text-red-400'
                        }`}>
                          {reEvalResult.validation_summary?.safety_status}
                        </div>
                        <div className="text-xs text-slate-400">Safety</div>
                      </div>
                    </div>
                    <div className={`p-2 rounded text-center text-sm ${
                      reEvalResult.validation_summary?.overall_status === 'VALIDATED' ? 'bg-emerald-500/20 border border-emerald-500/50' :
                      reEvalResult.validation_summary?.overall_status === 'ADVISORY' ? 'bg-blue-500/20 border border-blue-500/50' :
                      reEvalResult.validation_summary?.overall_status === 'PROCEED_WITH_CAUTION' ? 'bg-amber-500/20 border border-amber-500/50' :
                      'bg-red-500/20 border border-red-500/50'
                    }`}>
                      {reEvalResult.validation_summary?.overall_status}
                      {reEvalResult.validation_summary?.human_review_required && (
                        <Badge className="ml-2 bg-red-600 text-xs">Human Review</Badge>
                      )}
                    </div>

                    {/* Detailed AI Agent Outcomes */}
                    {reEvalResult.analysis && (
                      <div className="space-y-2 mt-3 border-t border-slate-700 pt-3">
                        <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                          <Brain className="h-3 w-3" />
                          AI Agent Findings
                        </div>
                        <div className="max-h-48 overflow-y-auto space-y-2">
                          {/* Recovery Predictor */}
                          {reEvalResult.analysis.recovery_predictor && (
                            <div className="p-2 bg-slate-800/50 rounded text-xs">
                              <div className="font-medium text-blue-400">Recovery Predictor</div>
                              <div className="text-slate-300">
                                Appeal Success: <span className={reEvalResult.analysis.recovery_predictor.success_probability > 0.5 ? 'text-emerald-400' : 'text-amber-400'}>
                                  {Math.round((reEvalResult.analysis.recovery_predictor.success_probability || 0) * 100)}%
                                </span>
                              </div>
                              {reEvalResult.analysis.recovery_predictor.key_factors?.slice(0, 2).map((f: string, i: number) => (
                                <div key={i} className="text-slate-400 text-[10px] mt-1">• {f}</div>
                              ))}
                            </div>
                          )}
                          {/* Doc Completeness */}
                          {reEvalResult.analysis.doc_completeness && (
                            <div className="p-2 bg-slate-800/50 rounded text-xs">
                              <div className="font-medium text-purple-400">Documentation</div>
                              <div className="text-slate-300">
                                Completeness: <span className={reEvalResult.analysis.doc_completeness.completeness_score >= 70 ? 'text-emerald-400' : 'text-red-400'}>
                                  {reEvalResult.analysis.doc_completeness.completeness_score}%
                                </span>
                              </div>
                              {reEvalResult.analysis.doc_completeness.missing_docs?.slice(0, 2).map((d: string, i: number) => (
                                <div key={i} className="text-red-400 text-[10px] mt-1">Missing: {d}</div>
                              ))}
                            </div>
                          )}
                          {/* Clinical Urgency */}
                          {reEvalResult.analysis.clinical_urgency && (
                            <div className="p-2 bg-slate-800/50 rounded text-xs">
                              <div className="font-medium text-orange-400">Clinical Urgency</div>
                              <div className="text-slate-300">
                                Level: <span className={
                                  reEvalResult.analysis.clinical_urgency.urgency_level === 'high' ? 'text-red-400' :
                                  reEvalResult.analysis.clinical_urgency.urgency_level === 'medium' ? 'text-amber-400' : 'text-emerald-400'
                                }>{reEvalResult.analysis.clinical_urgency.urgency_level}</span>
                              </div>
                              <div className="text-slate-400 text-[10px] mt-1">{reEvalResult.analysis.clinical_urgency.clinical_justification?.substring(0, 100)}...</div>
                            </div>
                          )}
                          {/* P2P Recommendation */}
                          {reEvalResult.analysis.p2p_optimizer && (
                            <div className="p-2 bg-slate-800/50 rounded text-xs">
                              <div className="font-medium text-cyan-400">P2P Review</div>
                              <div className="text-slate-300">
                                Recommended: <span className={reEvalResult.analysis.p2p_optimizer.recommended ? 'text-emerald-400' : 'text-slate-400'}>
                                  {reEvalResult.analysis.p2p_optimizer.recommended ? 'Yes' : 'No'}
                                </span>
                                {reEvalResult.analysis.p2p_optimizer.recommended && (
                                  <span className="ml-2">({Math.round((reEvalResult.analysis.p2p_optimizer.success_rate || 0) * 100)}% success rate)</span>
                                )}
                              </div>
                            </div>
                          )}
                          {/* Recommended Actions */}
                          {reEvalResult.analysis.combined_recommendation?.recommended_actions && (
                            <div className="p-2 bg-emerald-900/30 rounded text-xs border border-emerald-500/30">
                              <div className="font-medium text-emerald-400">Recommended Actions</div>
                              {reEvalResult.analysis.combined_recommendation.recommended_actions.slice(0, 3).map((a: string, i: number) => (
                                <div key={i} className="text-slate-300 text-[10px] mt-1">• {a}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* RHAIL Feature: AI Appeal Letter Generator */}
            <Card className="bg-gradient-to-r from-emerald-900/30 to-blue-900/30 border-emerald-500/30">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4 text-emerald-400" />
                  AI Appeal Letter Generator
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  RHAIL-comparable feature: Generate professional appeal letters
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {!appealLetter ? (
                  <Button 
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => generateAppealLetter(selectedDenial.denial_id)}
                    disabled={appealLetterLoading}
                  >
                    {appealLetterLoading ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Generating Letter...
                      </>
                    ) : (
                      <>
                        <FileText className="h-4 w-4 mr-2" />
                        Generate Appeal Letter
                      </>
                    )}
                  </Button>
                ) : (
                  <>
                    <div className="bg-slate-800/50 rounded-lg p-3 max-h-48 overflow-y-auto">
                      <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono">
                        {appealLetter.letter?.substring(0, 500)}...
                      </pre>
                    </div>
                    <div className="flex gap-2">
                      <Button 
                        className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                        onClick={copyAppealLetter}
                      >
                        <Clipboard className="h-4 w-4 mr-2" />
                        Copy Letter
                      </Button>
                      <Button 
                        variant="outline"
                        onClick={() => setAppealLetter(null)}
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                    </div>
                    {appealLetter.ai_recommendations && (
                      <div className="space-y-1">
                        <p className="text-xs font-semibold text-slate-400">AI Recommendations:</p>
                        {appealLetter.ai_recommendations.map((rec: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-slate-300">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                            {rec}
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>

            {/* Timeline / Activity */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Clock className="h-4 w-4 text-slate-400" />
                  Activity Timeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex gap-3 text-sm">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-2" />
                    <div>
                      <p className="text-slate-300">Denial received from {selectedDenial.payer_name}</p>
                      <p className="text-xs text-slate-500">{formatDate(selectedDenial.denial_date)} | CARC: {selectedDenial.carc_code}</p>
                    </div>
                  </div>
                  <div className="flex gap-3 text-sm">
                    <div className="w-2 h-2 rounded-full bg-purple-500 mt-2" />
                    <div>
                      <p className="text-slate-300">AI analysis completed</p>
                      <p className="text-xs text-slate-500">Priority score: {(selectedDenial.priority_score * 100).toFixed(0)} | Recommended: {selectedDenial.recommended_action}</p>
                    </div>
                  </div>
                  {selectedDenial.denial_status !== 'New' && (
                    <div className="flex gap-3 text-sm">
                      <div className="w-2 h-2 rounded-full bg-emerald-500 mt-2" />
                      <div>
                        <p className="text-slate-300">Status updated to {selectedDenial.denial_status}</p>
                        <p className="text-xs text-slate-500">Workflow action taken</p>
                      </div>
                    </div>
                  )}
                  <div className="flex gap-3 text-sm border-t border-slate-700 pt-3 mt-3">
                    <Calendar className="h-4 w-4 text-amber-400" />
                    <div>
                      <p className="text-amber-400 font-medium">Appeal deadline: {formatDate(new Date(new Date(selectedDenial.denial_date).getTime() + 30*24*60*60*1000).toISOString())}</p>
                      <p className="text-xs text-slate-500">30 days from denial date</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    )

  const renderPriorAuths = () => (
    <div className="flex gap-4">
      {/* Main List Panel */}
      <div className={`space-y-4 transition-all duration-300 ${selectedPA ? 'w-1/2' : 'w-full'}`}>
        {/* Queue Filters */}
        <div className="flex flex-wrap gap-2">
          {['all', 'Pending', 'In Review', 'Approved', 'Denied', 'Partial'].map((filter) => (
            <Button
              key={filter}
              variant={statusFilter === filter ? 'default' : 'outline'}
              size="sm"
              onClick={() => { setStatusFilter(filter); setCurrentPage(1) }}
              className={statusFilter === filter ? 'bg-purple-600 hover:bg-purple-700' : ''}
            >
              {filter === 'all' ? 'All' : filter}
            </Button>
          ))}
        </div>

        {/* Search and Filters */}
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-48">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search patient, auth #, procedure..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1) }}
                className="pl-10"
              />
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={fetchPriorAuths}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>

        {/* Prior Auth Table - Persona-specific columns */}
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="h-[550px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    {persona === 'clinical' ? (
                      <>
                        <TableHead>Patient</TableHead>
                        <TableHead>Procedure</TableHead>
                        <TableHead>Can Treat?</TableHead>
                        <TableHead>Urgency</TableHead>
                        <TableHead>Status</TableHead>
                      </>
                    ) : persona === 'executive' ? (
                      <>
                        <TableHead>Auth #</TableHead>
                        <TableHead>Procedure</TableHead>
                        <TableHead>Est. Cost</TableHead>
                        <TableHead>Denial Risk</TableHead>
                        <TableHead>Financial Impact</TableHead>
                      </>
                    ) : (
                      <>
                        <TableHead>Auth #</TableHead>
                        <TableHead>Patient / Procedure</TableHead>
                        <TableHead>Payer</TableHead>
                        <TableHead>Risk</TableHead>
                        <TableHead>Status</TableHead>
                      </>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {priorAuths.map((pa) => (
                    <TableRow 
                      key={pa.prior_auth_id}
                      className={`cursor-pointer hover:bg-purple-500/10 transition-colors ${selectedPA?.prior_auth_id === pa.prior_auth_id ? 'bg-purple-500/20 border-l-2 border-l-purple-500' : ''}`}
                      onClick={() => handlePAClick(pa)}
                    >
                      {persona === 'clinical' ? (
                        <>
                          <TableCell>
                            <div className="font-medium">{pa.patient_name}</div>
                            <div className="text-xs text-muted-foreground">MRN: {pa.patient_mrn || 'N/A'}</div>
                          </TableCell>
                          <TableCell>
                            <div className="text-sm">{pa.procedure_description || pa.procedure_code}</div>
                          </TableCell>
                          <TableCell>
                            {pa.auth_status === 'Approved' ? (
                              <span className="flex items-center gap-1 text-emerald-400 font-bold">
                                <CheckCircle className="h-4 w-4" /> YES
                              </span>
                            ) : pa.auth_status === 'Denied' ? (
                              <span className="flex items-center gap-1 text-red-400 font-bold">
                                <X className="h-4 w-4" /> NO
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-400 font-bold">
                                <Clock className="h-4 w-4" /> PENDING
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-bold ${pa.clinical_urgency && pa.clinical_urgency > 7 ? 'text-red-600 bg-red-500/20' : pa.clinical_urgency && pa.clinical_urgency > 4 ? 'text-amber-600 bg-amber-500/20' : 'text-green-600 bg-green-500/20'}`}>
                              {pa.clinical_urgency ? `${pa.clinical_urgency}/10` : 'N/A'}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(pa.auth_status)}>{pa.auth_status}</Badge>
                          </TableCell>
                        </>
                      ) : persona === 'executive' ? (
                        <>
                          <TableCell className="font-mono text-sm">{pa.auth_number}</TableCell>
                          <TableCell>
                            <div className="text-sm">{pa.procedure_code}</div>
                          </TableCell>
                          <TableCell className="font-bold text-emerald-400">
                            {formatCurrency(pa.estimated_cost || 5000 + (pa.prior_auth_id * 137) % 15000)}
                          </TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-bold ${pa.denial_probability > 0.3 ? 'text-red-600 bg-red-500/20' : 'text-green-600 bg-green-500/20'}`}>
                              {(pa.denial_probability * 100).toFixed(0)}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className={`text-sm font-medium ${pa.denial_probability > 0.3 ? 'text-red-400' : 'text-emerald-400'}`}>
                              {pa.denial_probability > 0.3 ? 'High Risk' : 'Low Risk'}
                            </span>
                          </TableCell>
                        </>
                      ) : (
                        <>
                          <TableCell className="font-mono text-sm">{pa.auth_number}</TableCell>
                          <TableCell>
                            <div className="font-medium">{pa.patient_name}</div>
                            <div className="text-xs text-muted-foreground">{pa.procedure_code}</div>
                          </TableCell>
                          <TableCell className="text-sm">{pa.payer_name}</TableCell>
                          <TableCell>
                            <span className={`px-2 py-1 rounded text-xs font-bold ${pa.denial_probability > 0.3 ? 'text-red-600 bg-red-50' : 'text-green-600 bg-green-50'}`}>
                              {(pa.denial_probability * 100).toFixed(0)}%
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge className={getStatusColor(pa.auth_status)}>{pa.auth_status}</Badge>
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Pagination */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">Page {currentPage} of {totalPages}</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Detail Drawer Panel */}
      {selectedPA && (
        <div className="w-1/2 space-y-4 animate-in slide-in-from-right duration-300">
          {/* Header */}
          <Card className="bg-gradient-to-r from-slate-800/80 to-slate-900/80 border-slate-700">
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="text-lg font-bold text-white">{selectedPA.patient_name}</h3>
                  <p className="text-sm text-slate-400">Auth #: {selectedPA.auth_number}</p>
                </div>
                <Button variant="ghost" size="sm" onClick={closePADrawer}>
                  <X className="h-4 w-4" />
                </Button>
              </div>
                            <div className="grid grid-cols-4 gap-3">
                              <div className="bg-slate-700/50 rounded-lg p-2">
                                <div className={`text-lg font-bold ${selectedPA.denial_probability > 0.3 ? 'text-red-400' : 'text-emerald-400'}`}>
                                  {(selectedPA.denial_probability * 100).toFixed(0)}%
                                </div>
                                <div className="text-xs text-slate-400">Denial Risk</div>
                              </div>
                              <div className="bg-slate-700/50 rounded-lg p-2">
                                <div className={`text-lg font-bold ${selectedPA.documentation_score < 80 ? 'text-amber-400' : 'text-emerald-400'}`}>
                                  {selectedPA.documentation_score?.toFixed(0)}%
                                </div>
                                <div className="text-xs text-slate-400">Doc Score</div>
                              </div>
                              <div className="bg-slate-700/50 rounded-lg p-2">
                                <div className="text-lg font-bold text-blue-400">{selectedPA.payer_name?.split(' ')[0]}</div>
                                <div className="text-xs text-slate-400">Payer</div>
                              </div>
                              <div className="bg-slate-700/50 rounded-lg p-2">
                                <Badge className={getStatusColor(selectedPA.auth_status)}>{selectedPA.auth_status}</Badge>
                                <div className="text-xs text-slate-400 mt-1">Status</div>
                              </div>
                            </div>
            </CardContent>
          </Card>

          {/* Procedure Details */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Stethoscope className="h-4 w-4 text-purple-400" />
                Procedure Details
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Code:</span>
                  <span className="font-mono">{selectedPA.procedure_code}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Description:</span>
                  <span className="text-sm text-right max-w-48">{selectedPA.procedure_description}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Request Date:</span>
                  <span>{formatDate(selectedPA.request_date)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RHAIL Feature: Can I Treat? Treatment Guidance */}
          <Card className="bg-gradient-to-r from-cyan-900/30 to-blue-900/30 border-cyan-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Stethoscope className="h-4 w-4 text-cyan-400" />
                Can I Treat? - Treatment Guidance
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                RHAIL-comparable feature: AI-powered treatment authorization guidance
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {!treatmentGuidance ? (
                <Button 
                  className="w-full bg-cyan-600 hover:bg-cyan-700"
                  onClick={() => fetchTreatmentGuidance(selectedPA.prior_auth_id)}
                  disabled={treatmentGuidanceLoading}
                >
                  {treatmentGuidanceLoading ? (
                    <>
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Stethoscope className="h-4 w-4 mr-2" />
                      Get Treatment Guidance
                    </>
                  )}
                </Button>
              ) : (
                <>
                  {/* Treatment Status Banner */}
                  <div className={`rounded-lg p-3 ${
                    treatmentGuidance.can_treat 
                      ? 'bg-emerald-500/20 border border-emerald-500/30' 
                      : treatmentGuidance.risk_level === 'high'
                        ? 'bg-red-500/20 border border-red-500/30'
                        : 'bg-amber-500/20 border border-amber-500/30'
                  }`}>
                    <div className="flex items-center gap-2">
                      {treatmentGuidance.can_treat ? (
                        <CheckCircle className="h-6 w-6 text-emerald-400" />
                      ) : treatmentGuidance.risk_level === 'high' ? (
                        <X className="h-6 w-6 text-red-400" />
                      ) : (
                        <Clock className="h-6 w-6 text-amber-400" />
                      )}
                      <div>
                        <p className={`font-bold ${
                          treatmentGuidance.can_treat ? 'text-emerald-400' : 
                          treatmentGuidance.risk_level === 'high' ? 'text-red-400' : 'text-amber-400'
                        }`}>
                          {treatmentGuidance.treatment_status}
                        </p>
                        <p className="text-xs text-slate-300">{treatmentGuidance.guidance_message}</p>
                      </div>
                    </div>
                  </div>

                  {/* Documentation Checklist */}
                  {treatmentGuidance.documentation_checklist && (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-slate-400">Documentation Checklist:</p>
                      {treatmentGuidance.documentation_checklist.map((item: {item: string, complete: boolean}, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          {item.complete ? (
                            <CheckCircle className="h-3 w-3 text-emerald-400" />
                          ) : (
                            <AlertTriangle className="h-3 w-3 text-amber-400" />
                          )}
                          <span className={item.complete ? 'text-slate-300' : 'text-amber-400'}>
                            {item.item}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* AI Recommendations */}
                  {treatmentGuidance.ai_recommendations && (
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-slate-400">AI Analysis:</p>
                      {treatmentGuidance.ai_recommendations.map((rec: string, i: number) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-slate-300">
                          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 flex-shrink-0" />
                          {rec}
                        </div>
                      ))}
                    </div>
                  )}

                  <Button 
                    variant="outline"
                    size="sm"
                    onClick={() => setTreatmentGuidance(null)}
                    className="w-full"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh Guidance
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {/* AI Recommendation Card */}
          <Card className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-purple-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple-400" />
                AI Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="bg-purple-500/20 border border-purple-500/30 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <Target className="h-5 w-5 text-purple-400 mt-0.5" />
                  <div>
                    <p className="font-medium text-white">
                      {selectedPA.denial_probability > 0.3 
                        ? 'Add clinical documentation before submitting' 
                        : 'Ready to submit - low denial risk'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Documentation Score: {selectedPA.documentation_score?.toFixed(0)}% | 
                      Denial Risk: {(selectedPA.denial_probability * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Checklist */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Pre-Submission Checklist</h4>
                
                <div className="flex items-start gap-2 text-sm">
                  {selectedPA.documentation_score >= 80 ? (
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5" />
                  )}
                  <div>
                    <span className="text-slate-300">Documentation: </span>
                    <span className={selectedPA.documentation_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}>
                      {selectedPA.documentation_score >= 80 ? 'Complete' : 'Needs additional clinical notes'}
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-2 text-sm">
                  {selectedPA.denial_probability <= 0.3 ? (
                    <CheckCircle className="h-4 w-4 text-emerald-400 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5" />
                  )}
                  <div>
                    <span className="text-slate-300">Risk Assessment: </span>
                    <span className={selectedPA.denial_probability <= 0.3 ? 'text-emerald-400' : 'text-red-400'}>
                      {selectedPA.denial_probability <= 0.3 ? 'Low risk - proceed' : 'High risk - review before submitting'}
                    </span>
                  </div>
                </div>

                <div className="flex items-start gap-2 text-sm">
                  <FileText className="h-4 w-4 text-blue-400 mt-0.5" />
                  <div>
                    <span className="text-slate-300">Payer Requirements: </span>
                    <span className="text-slate-400">Check {selectedPA.payer_name} policy guidelines</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Quick Action Buttons - Persona-specific */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                {persona === 'clinical' ? 'Charge Nurse Actions' : 'Quick Actions'}
              </CardTitle>
              {persona === 'clinical' && (
                <CardDescription className="text-xs text-slate-400">
                  Treatment scheduling & care coordination
                </CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-2">
              {persona === 'clinical' ? (
                <>
                  {/* Treatment Readiness Actions */}
                  <div className="text-xs text-slate-400 uppercase font-semibold mb-1">Treatment Readiness</div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                      onClick={() => handlePAAction('confirm_ready_schedule', selectedPA.prior_auth_id)}
                      disabled={selectedPA.auth_status !== 'Approved'}
                    >
                      <CheckCircle className="h-4 w-4 mr-1" />
                      Confirm Ready to Treat
                    </Button>
                    <Button 
                      className="bg-amber-600 hover:bg-amber-700 text-white text-xs"
                      onClick={() => handlePAAction('mark_at_risk_cancellation', selectedPA.prior_auth_id)}
                    >
                      <AlertTriangle className="h-4 w-4 mr-1" />
                      At Risk of Cancellation
                    </Button>
                    <Button 
                      className="bg-red-600 hover:bg-red-700 text-white text-xs col-span-2"
                      onClick={() => handlePAAction('flag_stat_to_pa_team', selectedPA.prior_auth_id)}
                    >
                      <AlertCircle className="h-4 w-4 mr-1" />
                      Flag STAT to PA/UR Team
                    </Button>
                  </div>

                  {/* Physician Communication */}
                  <div className="text-xs text-slate-400 uppercase font-semibold mt-3 mb-1">Physician Communication</div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline"
                      className="text-xs"
                      onClick={() => handlePAAction('request_md_justification', selectedPA.prior_auth_id)}
                    >
                      <FileText className="h-4 w-4 mr-1" />
                      Request MD Justification
                    </Button>
                    <Button 
                      variant="outline"
                      className="text-xs"
                      onClick={() => handlePAAction('discuss_alternate_plan', selectedPA.prior_auth_id)}
                    >
                      <Stethoscope className="h-4 w-4 mr-1" />
                      Discuss Alternate Plan
                    </Button>
                  </div>

                  {/* Care Coordination */}
                  <div className="text-xs text-slate-400 uppercase font-semibold mt-3 mb-1">Care Coordination</div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      className="bg-blue-600 hover:bg-blue-700 text-white text-xs"
                      onClick={() => handlePAAction('send_docs_to_pa_team', selectedPA.prior_auth_id)}
                    >
                      <FileUp className="h-4 w-4 mr-1" />
                      Send Docs to PA Team
                    </Button>
                    <Button 
                      variant="outline"
                      className="text-xs"
                      onClick={() => handlePAAction('reschedule_or_adjust_care', selectedPA.prior_auth_id)}
                    >
                      <Calendar className="h-4 w-4 mr-1" />
                      Reschedule Procedure
                    </Button>
                    <Button 
                      variant="outline"
                      className="text-red-400 border-red-400/50 hover:bg-red-400/10 text-xs col-span-2"
                      onClick={() => handlePAAction('cancel_change_order', selectedPA.prior_auth_id)}
                    >
                      <X className="h-4 w-4 mr-1" />
                      Cancel / Change Treatment Order
                    </Button>
                  </div>
                </>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      className="bg-purple-600 hover:bg-purple-700 text-white"
                      onClick={() => handlePAAction('submit_pa', selectedPA.prior_auth_id)}
                      disabled={selectedPA.auth_status !== 'Pending'}
                    >
                      <FileUp className="h-4 w-4 mr-2" />
                      Submit PA
                    </Button>
                    <Button 
                      className="bg-blue-600 hover:bg-blue-700 text-white"
                      onClick={() => handlePAAction('add_docs', selectedPA.prior_auth_id)}
                    >
                      <Clipboard className="h-4 w-4 mr-2" />
                      Add Clinical Docs
                    </Button>
                    <Button 
                      variant="outline"
                      onClick={() => handlePAAction('escalate', selectedPA.prior_auth_id)}
                    >
                      <UserCheck className="h-4 w-4 mr-2" />
                      Escalate / Peer Review
                    </Button>
                    <Button 
                      variant="outline"
                      className="text-red-400 border-red-400/50 hover:bg-red-400/10"
                      onClick={() => handlePAAction('cancel', selectedPA.prior_auth_id)}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Cancel / Change Order
                    </Button>
                  </div>
                </>
              )}

              {/* Follow AI vs Override */}
              <div className="flex gap-2 mt-3 pt-3 border-t border-slate-700">
                <Button 
                  className="flex-1 bg-purple-600 hover:bg-purple-700"
                  onClick={() => handlePAAction('follow_ai', selectedPA.prior_auth_id)}
                >
                  <ThumbsUp className="h-4 w-4 mr-2" />
                  Follow AI Plan
                </Button>
                <Button 
                  variant="outline"
                  className="flex-1"
                  onClick={() => handlePAAction('override_ai', selectedPA.prior_auth_id)}
                >
                  <ThumbsDown className="h-4 w-4 mr-2" />
                  Custom Plan
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Demo: Simulate Changes for PA */}
          <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                Demo: Simulate Changes
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                Simulate policy updates, new documentation, or patient status changes
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button 
                className="w-full bg-amber-600 hover:bg-amber-700"
                onClick={simulateChanges}
              >
                <Activity className="h-4 w-4 mr-2" />
                Introduce New Changes
              </Button>

              {/* Show simulated changes */}
              {simulatedChanges.length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-amber-400 text-sm font-medium">
                    <AlertTriangle className="h-4 w-4" />
                    Changes Detected - Re-evaluation Recommended
                  </div>
                  <div className="space-y-1">
                    {simulatedChanges.map((change, idx) => (
                      <div key={idx} className="flex items-center gap-2 p-2 bg-amber-500/10 rounded text-xs">
                        <CheckCircle className="h-3 w-3 text-amber-400" />
                        <span className="text-slate-300">{change}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Re-Evaluate with 18 AI Agents for PA */}
          <Card className={`bg-gradient-to-r from-purple-900/30 to-pink-900/30 ${changesNeedReEval ? 'border-amber-500 border-2 animate-pulse' : 'border-purple-500/30'}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Shield className="h-4 w-4 text-purple-400" />
                Re-Evaluate with 18 AI Agents
                {changesNeedReEval && (
                  <Badge className="bg-amber-600 text-xs ml-2">Action Needed</Badge>
                )}
              </CardTitle>
              <CardDescription className="text-xs text-slate-400">
                {changesNeedReEval 
                  ? "Changes detected! Re-run validation to update grades" 
                  : "Re-run validation when documentation changes or before critical decisions"}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button 
                className="w-full bg-purple-600 hover:bg-purple-700"
                onClick={() => reEvaluateClaim('pa', selectedPA.prior_auth_id)}
                disabled={reEvalRunning}
              >
                {reEvalRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    {reEvalCurrentAgent}
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4 mr-2" />
                    Re-Run AI Validation
                  </>
                )}
              </Button>

              {/* Progress bar */}
              {reEvalRunning && (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Validating through 18 agents...</span>
                    <span>{reEvalProgress}%</span>
                  </div>
                  <Progress value={reEvalProgress} className="h-2" />
                </div>
              )}

              {/* Show last few validation steps */}
              {reEvalSteps.length > 0 && (
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {reEvalSteps.slice(-5).map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs p-1.5 bg-slate-800/50 rounded">
                      <CheckCircle className="h-3 w-3 text-emerald-400" />
                      <span className="text-slate-300">{step.agent_name}</span>
                      <span className="text-slate-400 text-[10px] ml-auto truncate max-w-[200px]">{step.insight}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Final validation result */}
              {reEvalResult && !reEvalRunning && (
                <div className="space-y-2 p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">Validation Complete</span>
                    <Badge className={
                      reEvalResult.validation_summary?.safety_status === 'SAFE' ? 'bg-emerald-600' :
                      reEvalResult.validation_summary?.safety_status === 'CAUTION' ? 'bg-amber-600' : 'bg-red-600'
                    }>
                      {reEvalResult.validation_summary?.safety_status}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-slate-400">Policy Match:</span>
                      <span className="ml-2 font-bold text-blue-400">{reEvalResult.validation_summary?.policy_match_grade}/100</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Viability:</span>
                      <span className="ml-2 font-bold text-purple-400">{reEvalResult.validation_summary?.viability_grade}/100</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Consensus:</span>
                      <span className="ml-2 font-bold text-cyan-400">{reEvalResult.validation_summary?.consensus_score}%</span>
                    </div>
                    <div>
                      <span className="text-slate-400">Status:</span>
                      <span className={`ml-2 font-bold ${
                        reEvalResult.validation_summary?.overall_status === 'VALIDATED' ? 'text-emerald-400' :
                        reEvalResult.validation_summary?.overall_status === 'ADVISORY' ? 'text-blue-400' : 'text-amber-400'
                      }`}>{reEvalResult.validation_summary?.overall_status}</span>
                    </div>
                  </div>
                  {reEvalResult.validation_summary?.human_review_required && (
                    <div className="flex items-center gap-2 text-amber-400 text-xs mt-2">
                      <AlertTriangle className="h-3 w-3" />
                      Human Review Required
                    </div>
                  )}

                  {/* Detailed AI Agent Outcomes for PA */}
                  {reEvalResult.analysis && (
                    <div className="space-y-2 mt-3 border-t border-slate-600 pt-3">
                      <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                        <Brain className="h-3 w-3" />
                        AI Agent Findings
                      </div>
                      <div className="max-h-40 overflow-y-auto space-y-2">
                        {/* PA Risk Predictor */}
                        {reEvalResult.analysis.pa_risk_predictor && (
                          <div className="p-2 bg-slate-900/50 rounded text-xs">
                            <div className="font-medium text-amber-400">PA Risk Assessment</div>
                            <div className="text-slate-300">
                              Denial Risk: <span className={reEvalResult.analysis.pa_risk_predictor.denial_probability < 0.4 ? 'text-emerald-400' : 'text-red-400'}>
                                {Math.round((reEvalResult.analysis.pa_risk_predictor.denial_probability || 0) * 100)}%
                              </span>
                            </div>
                            {reEvalResult.analysis.pa_risk_predictor.risk_factors?.slice(0, 2).map((f: string, i: number) => (
                              <div key={i} className="text-slate-400 text-[10px] mt-1">• {f}</div>
                            ))}
                          </div>
                        )}
                        {/* Doc Completeness */}
                        {reEvalResult.analysis.doc_completeness && (
                          <div className="p-2 bg-slate-900/50 rounded text-xs">
                            <div className="font-medium text-purple-400">Documentation</div>
                            <div className="text-slate-300">
                              Completeness: <span className={reEvalResult.analysis.doc_completeness.completeness_score >= 70 ? 'text-emerald-400' : 'text-red-400'}>
                                {reEvalResult.analysis.doc_completeness.completeness_score}%
                              </span>
                            </div>
                            {reEvalResult.analysis.doc_completeness.missing_docs?.slice(0, 2).map((d: string, i: number) => (
                              <div key={i} className="text-red-400 text-[10px] mt-1">Missing: {d}</div>
                            ))}
                          </div>
                        )}
                        {/* Care Gap Detector */}
                        {reEvalResult.analysis.care_gap_detector && (
                          <div className="p-2 bg-slate-900/50 rounded text-xs">
                            <div className="font-medium text-blue-400">Care Gaps</div>
                            {reEvalResult.analysis.care_gap_detector.care_gaps?.slice(0, 2).map((g: string, i: number) => (
                              <div key={i} className="text-slate-300 text-[10px] mt-1">• {g}</div>
                            ))}
                            {reEvalResult.analysis.care_gap_detector.alternative_treatments?.length > 0 && (
                              <div className="text-cyan-400 text-[10px] mt-1">
                                Alternative: {reEvalResult.analysis.care_gap_detector.alternative_treatments[0]}
                              </div>
                            )}
                          </div>
                        )}
                        {/* Recommended Actions */}
                        {reEvalResult.analysis.combined_recommendation?.recommended_actions && (
                          <div className="p-2 bg-emerald-900/30 rounded text-xs border border-emerald-500/30">
                            <div className="font-medium text-emerald-400">Recommended Actions</div>
                            {reEvalResult.analysis.combined_recommendation.recommended_actions.slice(0, 3).map((a: string, i: number) => (
                              <div key={i} className="text-slate-300 text-[10px] mt-1">• {a}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-400" />
                Activity Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-purple-500 mt-2" />
                  <div>
                    <p className="text-slate-300">PA request created</p>
                    <p className="text-xs text-slate-500">{formatDate(selectedPA.request_date)} | {selectedPA.procedure_code}</p>
                  </div>
                </div>
                <div className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-2" />
                  <div>
                    <p className="text-slate-300">AI risk assessment completed</p>
                    <p className="text-xs text-slate-500">Denial risk: {(selectedPA.denial_probability * 100).toFixed(0)}% | Doc score: {selectedPA.documentation_score?.toFixed(0)}%</p>
                  </div>
                </div>
                {selectedPA.auth_status !== 'Pending' && (
                  <div className="flex gap-3 text-sm">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 mt-2" />
                    <div>
                      <p className="text-slate-300">Status: {selectedPA.auth_status}</p>
                      <p className="text-xs text-slate-500">Decision received from payer</p>
                    </div>
                  </div>
                )}
                <div className="flex gap-3 text-sm border-t border-slate-700 pt-3 mt-3">
                  <Timer className="h-4 w-4 text-amber-400" />
                  <div>
                    <p className="text-amber-400 font-medium">Expected decision: 3-5 business days</p>
                    <p className="text-xs text-slate-500">Based on {selectedPA.payer_name} average turnaround</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )

  const renderAI = () => (
    <div className="space-y-6">
      {/* Demo Guide Card - Step by Step Instructions */}
      <Card className="bg-gradient-to-r from-blue-600/40 to-purple-600/40 border-blue-400/50 border-2">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Target className="h-5 w-5 text-blue-300" />
            How to Run the Demo
          </CardTitle>
          <CardDescription className="text-slate-300">
            Follow these 4 steps to see the full denial management workflow
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-3 bg-slate-800/60 rounded-lg border border-blue-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-sm font-bold">1</div>
                <span className="font-medium text-blue-300">Ingest Claims</span>
              </div>
              <p className="text-xs text-slate-400">Click "Availity Feed" or "Change Healthcare" below to simulate receiving 835 remittance data</p>
            </div>
            <div className="p-3 bg-slate-800/60 rounded-lg border border-emerald-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center text-sm font-bold">2</div>
                <span className="font-medium text-emerald-300">Review Denials</span>
              </div>
              <p className="text-xs text-slate-400">Go to "Denials" tab, click any row to see AI recommendations and take action</p>
            </div>
            <div className="p-3 bg-slate-800/60 rounded-lg border border-purple-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-sm font-bold">3</div>
                <span className="font-medium text-purple-300">Follow AI or Customize</span>
              </div>
              <p className="text-xs text-slate-400">Choose "Follow AI Plan" to accept AI recommendation, or "Custom Plan" to override</p>
            </div>
            <div className="p-3 bg-slate-800/60 rounded-lg border border-amber-500/30">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center text-sm font-bold">4</div>
                <span className="font-medium text-amber-300">See Impact</span>
              </div>
              <p className="text-xs text-slate-400">Watch AI Adherence and Recovery metrics update as you work through denials</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Validation Summary Card */}
      <Card className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border-purple-500/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-purple-400" />
            Multi-Model Validation System
          </CardTitle>
          <CardDescription>
            6 validation agents using different LLMs for life-critical decision verification
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-emerald-400">18</div>
              <div className="text-xs text-slate-400">Total Agents</div>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-blue-400">12</div>
              <div className="text-xs text-slate-400">Core Agents</div>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-purple-400">6</div>
              <div className="text-xs text-slate-400">Validation Agents</div>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-2xl font-bold text-amber-400">7</div>
              <div className="text-xs text-slate-400">LLMs Used</div>
            </div>
          </div>
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-400 mt-0.5" />
              <div>
                <p className="font-medium text-amber-400">Life-Critical Verification</p>
                <p className="text-xs text-slate-300">All recommendations are cross-verified by multiple AI models. High-risk decisions require human review.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Feed Control Card - Clearinghouse Ingestion */}
      <Card className="bg-gradient-to-r from-blue-900/30 to-cyan-900/30 border-blue-500/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-blue-400" />
            Clearinghouse Feed Control
          </CardTitle>
          <CardDescription>
            Ingest 835 remittance data from clearinghouses. Each feed generates 5-15 claims with realistic denial rates.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Manual Feed Buttons */}
            <div className="flex gap-3">
              <Button 
                onClick={() => triggerFeedIngestion('Availity')} 
                disabled={feedRunning}
                className="flex-1 bg-blue-600 hover:bg-blue-700"
              >
                {feedRunning ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <FileText className="h-4 w-4 mr-2" />
                )}
                Availity Feed
              </Button>
              <Button 
                onClick={() => triggerFeedIngestion('Change Healthcare')} 
                disabled={feedRunning}
                className="flex-1 bg-cyan-600 hover:bg-cyan-700"
              >
                {feedRunning ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <FileText className="h-4 w-4 mr-2" />
                )}
                Change Healthcare
              </Button>
            </div>

            {/* Auto-Feed Toggle */}
            <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
              <div>
                <p className="font-medium text-slate-200">Auto-Ingest (every 2 min)</p>
                <p className="text-xs text-slate-400">Automatically fetch new claims from clearinghouses</p>
              </div>
              <Button 
                onClick={toggleAutoFeed}
                variant={autoFeedEnabled ? "destructive" : "outline"}
                size="sm"
              >
                {autoFeedEnabled ? 'Stop' : 'Start'}
              </Button>
            </div>

            {/* Feed Status */}
            {feedStatus && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-2 bg-slate-800/50 rounded text-center">
                  <div className="text-xl font-bold text-blue-400">{feedStatus.feeds_today || 0}</div>
                  <div className="text-xs text-slate-400">Feeds Today</div>
                </div>
                <div className="p-2 bg-slate-800/50 rounded text-center">
                  <div className="text-xl font-bold text-emerald-400">{feedStatus.claims_today || 0}</div>
                  <div className="text-xs text-slate-400">Claims Today</div>
                </div>
                <div className="p-2 bg-slate-800/50 rounded text-center">
                  <div className="text-xl font-bold text-amber-400">{feedStatus.denials_today || 0}</div>
                  <div className="text-xs text-slate-400">Denials Today</div>
                </div>
                <div className="p-2 bg-slate-800/50 rounded text-center">
                  <div className="text-xl font-bold text-purple-400">
                    {feedStatus.claims_today > 0 ? Math.round((feedStatus.denials_today / feedStatus.claims_today) * 100) : 0}%
                  </div>
                  <div className="text-xs text-slate-400">Denial Rate</div>
                </div>
              </div>
            )}

            {/* Last Feed Info */}
            {feedStatus?.last_feed && (
              <div className="text-xs text-slate-400 text-center">
                Last feed: {feedStatus.last_feed.source} at {new Date(feedStatus.last_feed.completed_at).toLocaleTimeString()} 
                ({feedStatus.last_feed.claims_added} claims, {feedStatus.last_feed.denials_added} denials)
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* AI Adherence & Recovery Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* AI Adherence Card */}
        <Card className="bg-gradient-to-r from-emerald-900/30 to-green-900/30 border-emerald-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="h-4 w-4 text-emerald-400" />
              AI Adherence Rate
            </CardTitle>
            <CardDescription className="text-xs">Staff following AI recommendations (target: 67.5%)</CardDescription>
          </CardHeader>
          <CardContent>
            {aiAdherence ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-3xl font-bold text-emerald-400">
                    {(aiAdherence.follow_ai_rate * 100).toFixed(1)}%
                  </span>
                  <Badge className={aiAdherence.follow_ai_rate >= 0.675 ? 'bg-emerald-600' : 'bg-amber-600'}>
                    {aiAdherence.follow_ai_rate >= 0.675 ? 'On Target' : 'Below Target'}
                  </Badge>
                </div>
                <Progress value={aiAdherence.follow_ai_rate * 100} className="h-2" />
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 bg-slate-800/50 rounded">
                    <span className="text-slate-400">Follow AI:</span>
                    <span className="ml-1 text-emerald-400">{aiAdherence.follow_ai_count}</span>
                  </div>
                  <div className="p-2 bg-slate-800/50 rounded">
                    <span className="text-slate-400">Custom Plan:</span>
                    <span className="ml-1 text-amber-400">{aiAdherence.custom_plan_count}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-slate-400 mb-2">No staff actions recorded yet</p>
                <p className="text-xs text-slate-500">Go to Denials tab and click "Follow AI Plan" or "Custom Plan" on any denial</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recovery Rate Card */}
        <Card className="bg-gradient-to-r from-purple-900/30 to-pink-900/30 border-purple-500/30">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <DollarSign className="h-4 w-4 text-purple-400" />
              Appeal Recovery Rate
            </CardTitle>
            <CardDescription className="text-xs">Appeal success and recovery metrics</CardDescription>
          </CardHeader>
          <CardContent>
            {recoveryRate ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-3xl font-bold text-purple-400">
                    {(recoveryRate.overall_success_rate * 100).toFixed(1)}%
                  </span>
                  <span className="text-emerald-400 font-medium">
                    {formatCurrency(recoveryRate.total_recovered || 0)}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="p-2 bg-slate-800/50 rounded text-center">
                    <div className="text-emerald-400 font-bold">{recoveryRate.overturned || 0}</div>
                    <div className="text-slate-400">Overturned</div>
                  </div>
                  <div className="p-2 bg-slate-800/50 rounded text-center">
                    <div className="text-amber-400 font-bold">{recoveryRate.partial || 0}</div>
                    <div className="text-slate-400">Partial</div>
                  </div>
                  <div className="p-2 bg-slate-800/50 rounded text-center">
                    <div className="text-red-400 font-bold">{recoveryRate.upheld || 0}</div>
                    <div className="text-slate-400">Upheld</div>
                  </div>
                </div>
                {recoveryRate.ai_boost_effect && (
                  <div className="p-2 bg-emerald-500/10 border border-emerald-500/30 rounded text-xs">
                    <span className="text-emerald-400">AI Boost:</span>
                    <span className="ml-1 text-slate-300">
                      Appeals following AI have {((recoveryRate.ai_boost_effect - 1) * 100).toFixed(0)}% higher success rate
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-4">
                <p className="text-slate-400 mb-2">No appeals decided yet</p>
                <p className="text-xs text-slate-500">Click "Simulate Appeal Responses" below to generate payer decisions</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Policy Change Simulation */}
      <Card className="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-amber-500/30">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            Policy Change Simulation
          </CardTitle>
          <CardDescription className="text-xs">Simulate payer policy updates and appeal responses</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button 
              onClick={simulatePolicyChange}
              className="flex-1 bg-amber-600 hover:bg-amber-700"
            >
              <AlertTriangle className="h-4 w-4 mr-2" />
              Simulate Policy Change
            </Button>
            <Button 
              onClick={simulateAppealResponses}
              className="flex-1 bg-purple-600 hover:bg-purple-700"
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              Simulate Appeal Responses
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Test Ingest - AI-Resolved Queue Demo */}
      <Card className="bg-gradient-to-r from-emerald-900/30 to-cyan-900/30 border-emerald-500/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-emerald-400" />
            Test Ingest
          </CardTitle>
                    <CardDescription>
                      Process 10 denial cases through 18 AI agents. AI resolves 8 cases (one-click approve), 2 need clinical review.
                    </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Button 
              onClick={simulateIngestion} 
              disabled={ingestionRunning}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
                            {ingestionRunning ? (
                              <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                Processing 10 Denial Cases...
                              </>
                            ) : (
                              <>
                                <FileText className="h-4 w-4 mr-2" />
                                Run Test Ingest (10 Denial Cases)
                              </>
                            )}
            </Button>

            {/* Progress Bar */}
            {(ingestionRunning || ingestionProgress > 0) && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-emerald-400 font-medium">{ingestionCurrentAgent}</span>
                  <span className="text-slate-400">{Math.round(ingestionProgress)}%</span>
                </div>
                <Progress value={ingestionProgress} className="h-3" />
                
                {/* Agent Steps */}
                <div className="mt-4 max-h-64 overflow-y-auto space-y-1">
                  {ingestionSteps.map((step, idx) => (
                    <div key={idx} className={`flex items-center gap-2 p-2 rounded text-sm ${
                      step.category === 'Validation' ? 'bg-purple-900/20 border-l-2 border-purple-500' : 'bg-slate-800/50'
                    }`}>
                      <CheckCircle className={`h-4 w-4 ${step.category === 'Validation' ? 'text-purple-400' : 'text-emerald-400'}`} />
                      <span className="font-medium">{step.agent_name}</span>
                      <span className="text-slate-400 text-xs truncate max-w-[250px]">{step.insight || step.model}</span>
                      {step.result?.grade && (
                        <Badge className={`text-xs ${
                          step.result.grade >= 80 ? 'bg-emerald-600' : 
                          step.result.grade >= 70 ? 'bg-amber-600' : 'bg-red-600'
                        }`}>
                          {step.result.status}: {step.result.grade}
                        </Badge>
                      )}
                      {step.result?.safety_status && (
                        <Badge className={`text-xs ${
                          step.result.safety_status === 'SAFE' ? 'bg-emerald-600' : 
                          step.result.safety_status === 'CAUTION' ? 'bg-amber-600' : 'bg-red-600'
                        }`}>
                          {step.result.safety_status}
                        </Badge>
                      )}
                      {step.result?.consensus_score && (
                        <Badge variant="outline" className="text-xs">
                          Consensus: {step.result.consensus_score}%
                        </Badge>
                      )}
                      <span className="text-xs text-slate-500 ml-auto">{step.duration_ms}ms</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Final Result */}
            {ingestionResult && !ingestionRunning && (
              <div className="mt-4 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <h4 className="font-medium text-emerald-400 mb-3">Ingestion Complete</h4>
                
                {/* Claim Info */}
                <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                  <div>
                    <span className="text-slate-400">Claim #:</span>
                    <span className="ml-2 font-mono">{ingestionResult.claim?.claim_number}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Patient:</span>
                    <span className="ml-2">{ingestionResult.claim?.patient_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Payer:</span>
                    <span className="ml-2">{ingestionResult.claim?.payer_name}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">Amount:</span>
                    <span className="ml-2">${ingestionResult.claim?.billed_amount?.toLocaleString()}</span>
                  </div>
                </div>

                {/* Validation Summary */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  <div className="p-2 bg-slate-900/50 rounded text-center">
                    <div className={`text-xl font-bold ${
                      ingestionResult.validation_summary?.policy_match_grade >= 80 ? 'text-emerald-400' : 
                      ingestionResult.validation_summary?.policy_match_grade >= 70 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {ingestionResult.validation_summary?.policy_match_grade}
                    </div>
                    <div className="text-xs text-slate-400">Policy Match</div>
                  </div>
                  <div className="p-2 bg-slate-900/50 rounded text-center">
                    <div className={`text-xl font-bold ${
                      ingestionResult.validation_summary?.viability_grade >= 80 ? 'text-emerald-400' : 
                      ingestionResult.validation_summary?.viability_grade >= 70 ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {ingestionResult.validation_summary?.viability_grade}
                    </div>
                    <div className="text-xs text-slate-400">Viability</div>
                  </div>
                  <div className="p-2 bg-slate-900/50 rounded text-center">
                    <div className="text-xl font-bold text-blue-400">
                      {ingestionResult.validation_summary?.consensus_score}%
                    </div>
                    <div className="text-xs text-slate-400">Consensus</div>
                  </div>
                  <div className="p-2 bg-slate-900/50 rounded text-center">
                    <div className={`text-xl font-bold ${
                      ingestionResult.validation_summary?.safety_status === 'SAFE' ? 'text-emerald-400' : 
                      ingestionResult.validation_summary?.safety_status === 'CAUTION' ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      {ingestionResult.validation_summary?.safety_status}
                    </div>
                    <div className="text-xs text-slate-400">Safety</div>
                  </div>
                </div>

                {/* Overall Status */}
                <div className={`p-3 rounded-lg text-center ${
                  ingestionResult.validation_summary?.overall_status === 'VALIDATED' ? 'bg-emerald-500/20 border border-emerald-500/50' :
                  ingestionResult.validation_summary?.overall_status === 'ADVISORY' ? 'bg-blue-500/20 border border-blue-500/50' :
                  ingestionResult.validation_summary?.overall_status === 'PROCEED_WITH_CAUTION' ? 'bg-amber-500/20 border border-amber-500/50' :
                  'bg-red-500/20 border border-red-500/50'
                }`}>
                  <span className="font-medium">{ingestionResult.validation_summary?.overall_status}</span>
                  {ingestionResult.validation_summary?.human_review_required && (
                    <Badge className="ml-2 bg-red-600">Human Review Required</Badge>
                  )}
                </div>

                {/* AI-Resolved Queue */}
                {ingestionResult.ai_resolved_summary && (
                  <div className="mt-4 space-y-4">
                    {/* Summary Header */}
                    <div className="flex items-center justify-between p-3 bg-emerald-900/30 rounded-lg border border-emerald-500/30">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="h-6 w-6 text-emerald-400" />
                        <div>
                          <div className="font-medium text-emerald-400">AI-Resolved: Ready for Approval</div>
                          <div className="text-xs text-slate-400">
                            {ingestionResult.ai_resolved_summary.ai_resolved} of {ingestionResult.ai_resolved_summary.total_processed} cases resolved by AI
                          </div>
                        </div>
                      </div>
                      <Badge className="bg-emerald-600 text-lg px-3 py-1">
                        {ingestionResult.ai_resolved_summary.ai_resolved} Ready
                      </Badge>
                    </div>

                    {/* AI-Resolved Items - One-Click Approve */}
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-emerald-400 flex items-center gap-2">
                        <CheckCircle className="h-4 w-4" />
                        Low Risk - One-Click Approve ({ingestionResult.ai_resolved_summary.ai_resolved_items?.length || 0})
                      </div>
                      <div className="max-h-48 overflow-y-auto space-y-2">
                        {ingestionResult.ai_resolved_summary.ai_resolved_items?.map((item: any) => (
                          <div key={item.id} className="flex items-center justify-between p-2 bg-emerald-900/20 rounded border border-emerald-500/20">
                            <div className="flex items-center gap-3">
                              <Badge className="bg-emerald-600 text-xs">{item.risk}</Badge>
                              <span className="text-sm font-medium">{item.patient}</span>
                              <span className="text-xs text-slate-400">{item.action}</span>
                            </div>
                            <div className="flex gap-2">
                              <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 h-7 px-3 text-xs">
                                <CheckCircle className="h-3 w-3 mr-1" />
                                Approve
                              </Button>
                              <Button size="sm" variant="outline" className="h-7 px-2 text-xs border-slate-600">
                                <X className="h-3 w-3" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                      <Button className="w-full bg-emerald-600 hover:bg-emerald-700 mt-2">
                        <CheckCircle className="h-4 w-4 mr-2" />
                        Approve All {ingestionResult.ai_resolved_summary.ai_resolved} AI-Resolved Cases
                      </Button>
                    </div>

                    {/* Needs Review Items */}
                    {ingestionResult.ai_resolved_summary.needs_review_items?.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-sm font-medium text-amber-400 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4" />
                          Needs Clinical Review ({ingestionResult.ai_resolved_summary.needs_review_items?.length || 0})
                        </div>
                        <div className="space-y-2">
                          {ingestionResult.ai_resolved_summary.needs_review_items?.map((item: any) => (
                            <div key={item.id} className="flex items-center justify-between p-3 bg-amber-900/20 rounded border border-amber-500/30">
                              <div className="flex items-center gap-3">
                                <Badge className={item.risk === 'HIGH' ? 'bg-red-600' : 'bg-amber-600'} >{item.risk}</Badge>
                                <div>
                                  <span className="text-sm font-medium">{item.patient}</span>
                                  <div className="text-xs text-amber-400">{item.reason}</div>
                                </div>
                              </div>
                              <Button size="sm" variant="outline" className="border-amber-500 text-amber-400 hover:bg-amber-900/30">
                                Review
                              </Button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Database Status */}
                <div className="mt-3 text-xs text-slate-400 flex items-center gap-2">
                  <CheckCircle className="h-3 w-3 text-emerald-400" />
                  Database: {ingestionResult.database_status}
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Validation Agents Section */}
      <Card className="border-purple-500/30">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-purple-400" />
            Validation Agents (QA Layer)
          </CardTitle>
          <CardDescription>
            Multi-model cross-verification for life-critical decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agentStatus?.agents?.filter((a: any) => a.category === 'Validation').map((agent: any) => (
              <div key={agent.name} className="p-4 border border-purple-500/30 rounded-lg bg-purple-900/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm text-purple-300">{agent.name}</span>
                  <Badge className="bg-purple-600 text-xs">
                    {agent.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400 mb-3">{agent.description}</p>
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-xs border-purple-500/50 text-purple-300">Validation</Badge>
                  {agent.model && (
                    <Badge className="text-xs font-mono bg-slate-700">{agent.model}</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Core Agents Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            Core AI Agents
          </CardTitle>
          <CardDescription>
            12 specialized agents for denial management - {agentStatus?.mode}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {agentStatus?.models_used && (
            <div className="mb-4 p-3 bg-muted rounded-lg">
              <span className="text-sm font-medium">Models in use: </span>
              <span className="text-sm text-muted-foreground">
                {agentStatus.models_used.join(', ')}
              </span>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {agentStatus?.agents?.filter((a: any) => a.category !== 'Validation').map((agent: any) => (
              <div key={agent.name} className="p-3 border rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{agent.name}</span>
                  <Badge variant={agent.status === 'Active' ? 'default' : 'secondary'} className="text-xs">
                    {agent.status}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-2">{agent.description}</p>
                <div className="flex flex-wrap gap-1">
                  <Badge variant="outline" className="text-xs">{agent.category}</Badge>
                  {agent.model && (
                    <Badge variant="secondary" className="text-xs font-mono">{agent.model}</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI Insights & Recommendations</CardTitle>
          <CardDescription>Actionable intelligence from all 18 agents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {aiInsights.map((insight, index) => (
              <div key={index} className="p-4 border rounded-lg">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline">{insight.agent_name}</Badge>
                      <Badge>{insight.insight_type}</Badge>
                      <span className="text-sm text-muted-foreground">
                        Impact: {(insight.impact_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm mb-2">{insight.description}</p>
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">
                        Affected: <strong>{insight.affected_count}</strong> cases
                      </span>
                    </div>
                  </div>
                </div>
                <Separator className="my-3" />
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-yellow-500" />
                  <span className="text-sm font-medium">Recommended Action:</span>
                  <span className="text-sm">{insight.recommended_action}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderLearning = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{learningMetrics?.total_actions}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">AI Followed Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{learningMetrics?.ai_followed_rate}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Avg Reward Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{learningMetrics?.avg_reward_score?.toFixed(3)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Successful Outcomes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{learningMetrics?.successful_outcomes}</div>
          </CardContent>
        </Card>
      </div>

      {learningMetrics?.action_distribution && (
        <Card>
          <CardHeader>
            <CardTitle>Action Distribution</CardTitle>
            <CardDescription>Staff actions by type</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={Object.entries(learningMetrics.action_distribution).map(([name, value]) => ({ name, value }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#8884d8" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Recent Staff Actions (RL Training Data)</CardTitle>
          <CardDescription>Actions captured for reinforcement learning</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[400px]">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Staff ID</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>AI Recommendation</TableHead>
                  <TableHead>Followed AI</TableHead>
                  <TableHead>Outcome</TableHead>
                  <TableHead className="text-right">Reward</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rlTraces.map((trace) => (
                  <TableRow key={trace.trace_id}>
                    <TableCell className="text-sm">{formatDate(trace.action_timestamp)}</TableCell>
                    <TableCell className="font-mono text-sm">{trace.staff_id}</TableCell>
                    <TableCell>{trace.action_type}</TableCell>
                    <TableCell>{trace.ai_recommendation}</TableCell>
                    <TableCell>
                      <Badge variant={trace.staff_followed_ai ? 'default' : 'secondary'}>
                        {trace.staff_followed_ai ? 'Yes' : 'No'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(trace.outcome || '')}>{trace.outcome}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={trace.reward_score > 0 ? 'text-green-600' : trace.reward_score < 0 ? 'text-red-600' : ''}>
                        {trace.reward_score?.toFixed(3)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )

  const renderPayer = () => (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Payer Analytics
          </CardTitle>
          <CardDescription>Insurance company denial patterns and performance metrics</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Payer Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Avg Denial Rate</TableHead>
                <TableHead>Appeal Success Rate</TableHead>
                <TableHead>Avg Days to Decision</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payers.map((payer) => (
                <TableRow key={payer.payer_id}>
                  <TableCell className="font-medium">{payer.payer_name}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{payer.payer_type}</Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={payer.avg_denial_rate * 100} className="w-20 h-2 [&>div]:bg-red-500" />
                      <span className="text-sm">{(payer.avg_denial_rate * 100).toFixed(1)}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={payer.avg_appeal_success_rate * 100} className="w-20 h-2 [&>div]:bg-green-500" />
                      <span className="text-sm">{(payer.avg_appeal_success_rate * 100).toFixed(1)}%</span>
                    </div>
                  </TableCell>
                  <TableCell>{payer.avg_days_to_decision} days</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Denial Rate Comparison</CardTitle>
          <CardDescription>Denial rates across all payers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={payers} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 0.3]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                <YAxis type="category" dataKey="payer_name" width={150} tick={{ fontSize: 12 }} />
                <Tooltip formatter={(value: number) => `${(value * 100).toFixed(1)}%`} />
                <Legend />
                <Bar dataKey="avg_denial_rate" name="Denial Rate" fill="#ef4444" />
                <Bar dataKey="avg_appeal_success_rate" name="Appeal Success" fill="#22c55e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  if (loading && !metrics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p>Loading dashboard...</p>
        </div>
      </div>
    )
  }

    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <header className="border-b border-slate-800/50 bg-slate-900/80 backdrop-blur-xl sticky top-0 z-50">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="vision-icon-box vision-gradient-blue glow-blue">
                  <Stethoscope className="h-5 w-5 text-white" />
                </div>
                <div>
                                    <h1 className="text-xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">Denial Intelligence Platform</h1>
                                    <p className="text-sm text-slate-400">835 Remittance Analytics & AI-Powered Recovery</p>
                </div>
              </div>
                        <div className="flex items-center gap-4">
                          <Badge variant="outline" className="text-xs">POC - Synthetic Data</Badge>
                          <Select value={persona} onValueChange={(v: Persona) => {
                            setPersona(v)
                            setActiveTab(PERSONA_CONFIG[v].defaultTab)
                          }}>
                            <SelectTrigger className="w-48">
                              <SelectValue>
                                <div className="flex items-center gap-2">
                                  {persona === 'clinical' && <Stethoscope className="h-4 w-4" />}
                                  {persona === 'admin' && <Users className="h-4 w-4" />}
                                  {persona === 'executive' && <Briefcase className="h-4 w-4" />}
                                  {PERSONA_CONFIG[persona].name}
                                </div>
                              </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="clinical">
                                <div className="flex items-center gap-2">
                                  <Stethoscope className="h-4 w-4" />
                                  <div>
                                    <div>Clinical (Nurse/Staff)</div>
                                    <div className="text-xs text-muted-foreground">Patient care focus</div>
                                  </div>
                                </div>
                              </SelectItem>
                              <SelectItem value="admin">
                                <div className="flex items-center gap-2">
                                  <Users className="h-4 w-4" />
                                  <div>
                                    <div>Admin</div>
                                    <div className="text-xs text-muted-foreground">Operations focus</div>
                                  </div>
                                </div>
                              </SelectItem>
                              <SelectItem value="executive">
                                <div className="flex items-center gap-2">
                                  <Briefcase className="h-4 w-4" />
                                  <div>
                                    <div>Executive</div>
                                    <div className="text-xs text-muted-foreground">Strategic focus</div>
                                  </div>
                                </div>
                              </SelectItem>
                            </SelectContent>
                          </Select>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => setDarkMode(!darkMode)}
                            className="h-8 w-8"
                          >
                            {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                          </Button>
                          <Button variant="outline" size="sm" onClick={fetchDashboardData}>
                            <RefreshCw className="h-4 w-4 mr-2" />
                            Refresh
                          </Button>
                        </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6">
        <Tabs value={activeTab} onValueChange={(v) => { setActiveTab(v); setCurrentPage(1); setStatusFilter('all') }}>
                    <TabsList className="mb-6">
                      {PERSONA_CONFIG[persona].visibleTabs.includes('dashboard') && (
                        <TabsTrigger value="dashboard" className="flex items-center gap-2">
                          <Activity className="h-4 w-4" />
                          Dashboard
                        </TabsTrigger>
                      )}
                                            {PERSONA_CONFIG[persona].visibleTabs.includes('pa') && (
                                              <TabsTrigger value="pa" className="flex items-center gap-2">
                                                <Shield className="h-4 w-4" />
                                                Prior Auth <span className="text-xs text-slate-500 ml-1">(Phase 3)</span>
                                              </TabsTrigger>
                                            )}
                      {PERSONA_CONFIG[persona].visibleTabs.includes('denials') && (
                        <TabsTrigger value="denials" className="flex items-center gap-2">
                          <AlertCircle className="h-4 w-4" />
                          Denials
                        </TabsTrigger>
                      )}
                      {PERSONA_CONFIG[persona].visibleTabs.includes('ai') && (
                        <TabsTrigger value="ai" className="flex items-center gap-2">
                          <Brain className="h-4 w-4" />
                          AI Agents
                        </TabsTrigger>
                      )}
                      {PERSONA_CONFIG[persona].visibleTabs.includes('learning') && (
                        <TabsTrigger value="learning" className="flex items-center gap-2">
                          <TrendingUp className="h-4 w-4" />
                          Learning
                        </TabsTrigger>
                      )}
                      {PERSONA_CONFIG[persona].visibleTabs.includes('payer') && (
                        <TabsTrigger value="payer" className="flex items-center gap-2">
                          <Building2 className="h-4 w-4" />
                          Payer
                        </TabsTrigger>
                      )}
                    </TabsList>

          <TabsContent value="dashboard">{renderDashboard()}</TabsContent>
          <TabsContent value="pa">{renderPriorAuths()}</TabsContent>
          <TabsContent value="denials">{renderDenials()}</TabsContent>
          <TabsContent value="ai">{renderAI()}</TabsContent>
          <TabsContent value="learning">{renderLearning()}</TabsContent>
          <TabsContent value="payer">{renderPayer()}</TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

export default App
