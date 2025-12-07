import { useState, useEffect, useRef } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Progress } from '@/components/ui/progress'
// Separator removed - not currently used
import { ScrollArea } from '@/components/ui/scroll-area'
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend, LineChart, Line, Area, AreaChart, ComposedChart
} from 'recharts'
import { 
  AlertCircle, TrendingUp, TrendingDown, DollarSign, Clock, FileText, 
  Brain, Activity, Search, ChevronLeft, ChevronRight, RefreshCw,
  Building2, Stethoscope, Shield, Zap, Moon, Sun, Users, Briefcase,
  X, Phone, FileUp, CheckCircle, AlertTriangle, Calendar,
  Target, Clipboard, UserCheck, Timer, ThumbsUp, ThumbsDown, ArrowRight, Wallet
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
    visibleTabs: ['dashboard', 'denials', 'ai', 'lifecycle', 'payer', 'policy']
  },
  executive: {
    name: 'Executive',
    icon: Briefcase,
    description: 'Financial focus',
    defaultTab: 'cfo',
    visibleTabs: ['cfo', 'dashboard', 'denials', 'ai', 'lifecycle', 'learning', 'payer', 'policy']
  }
}
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || ''

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
  avg_queue_wait_time_seconds?: number
  avg_queue_wait_time_display?: string
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
  queue_wait_time_seconds?: number
  queue_wait_time_display?: string
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
  const [, setAiInsights] = useState<AIInsight[]>([])
  const [, setAgentStatus] = useState<any>(null)
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
    // Auto-feed timer state
    const [autoFeedCountdown, setAutoFeedCountdown] = useState(0)
    const [lastFeedResult, setLastFeedResult] = useState<{source: string, claims: number, denials: number, time: Date} | null>(null)
    const autoFeedIntervalRef = useRef<NodeJS.Timeout | null>(null)
    const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null)
    // AI agent processing animation during feed ingestion - Step-by-step workflow
    type AgentStatus = 'pending' | 'running' | 'auto_processed' | 'needs_review'
    type RiskLevel = 'low' | 'medium' | 'high'
    type AgentRunResult = {
      id: string
      name: string
      description: string
      status: AgentStatus
      risk: RiskLevel | null
      outcome: string | null
      needsHuman: boolean | null
    }
    
    const INITIAL_AGENT_PIPELINE: AgentRunResult[] = [
      { id: 'intake', name: 'Intake & Normalization', description: 'Parse 835 EDI and normalize claim records', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'eligibility', name: 'Eligibility & Coverage', description: 'Verify member eligibility and coverage', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'coding', name: 'Coding & Modifiers', description: 'Validate CPT/ICD codes and modifiers', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'medical_necessity', name: 'Medical Necessity', description: 'Check clinical criteria and medical necessity', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'timely_filing', name: 'Timely Filing Check', description: 'Verify submission within payer deadlines', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'documentation', name: 'Documentation Review', description: 'Check for missing clinical documentation', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'appeal_strategy', name: 'Appeal Strategy', description: 'Determine optimal appeal approach', status: 'pending', risk: null, outcome: null, needsHuman: null },
      { id: 'risk_triage', name: 'Risk Triage & Routing', description: 'Assign risk level and route for action', status: 'pending', risk: null, outcome: null, needsHuman: null },
    ]
    
    const [agentPipeline, setAgentPipeline] = useState<AgentRunResult[]>(INITIAL_AGENT_PIPELINE)
    const [, setAgentStepIndex] = useState<number>(-1)
    const [agentSummary, setAgentSummary] = useState<{ autoProcessed: number, needsReview: number, lowRisk: number, highRisk: number, claimsAnalyzed: number, denialsFound: number } | null>(null)
    const agentStepIndexRef = useRef<number>(-1)
    const feedAgentIntervalRef = useRef<NodeJS.Timeout | null>(null)
    
    // CFO Dashboard state (prefixed with _ to indicate intentionally unused - using static data for demo)
    const [_cfoKpis, setCfoKpis] = useState<any>(null)
    const [_churnWaterfall, setChurnWaterfall] = useState<any>(null)
    const [_cashForecast, setCashForecast] = useState<any>(null)
    const [_budgetVariance, setBudgetVariance] = useState<any>(null)
    const [_payerPerformance, setPayerPerformance] = useState<any>(null)
    const [_executiveSummary, setExecutiveSummary] = useState<any>(null)
    const [cfoLoading, setCfoLoading] = useState(false)
    // Suppress unused variable warnings
    void _cfoKpis; void _churnWaterfall; void _cashForecast; void _budgetVariance; void _payerPerformance; void _executiveSummary;
    // Scenario modeler state
    const [scenarioDenialRate, setScenarioDenialRate] = useState(18.5)
    const [scenarioAppealSuccess, setScenarioAppealSuccess] = useState(67)
    
    // 837/835 Lifecycle state
    const [lifecycleSources, setLifecycleSources] = useState<any[]>([])
    const [highRiskClaims, setHighRiskClaims] = useState<any[]>([])
    const [reconciliationData, setReconciliationData] = useState<any>(null)
    const [lifecycleLoading, setLifecycleLoading] = useState(false)
    
        // Clearinghouse state
        const [clearinghouseStatus, setClearinghouseStatus] = useState<any>(null)
        const [clearinghouseLogs, setClearinghouseLogs] = useState<any[]>([])
        const [pollingAvaility, setPollingAvaility] = useState(false)
        const [pollingChange, setPollingChange] = useState(false)
    
        // Early Warning state
        const [earlyWarning, setEarlyWarning] = useState<any>(null)

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
    } else if (activeTab === 'cfo') {
      fetchCFOData()
    } else if (activeTab === 'lifecycle') {
      fetchLifecycleData()
    }
  }, [activeTab, currentPage, statusFilter, searchTerm])

        const fetchDashboardData = async () => {
          setLoading(true)
          try {
                        const [metricsRes, categoryRes, payerRes, trendsRes, predictionsRes, forecastRes, aiImpactRes, earlyWarningRes] = await Promise.all([
                          fetch(`${API_URL}/api/dashboard/metrics`),
                          fetch(`${API_URL}/api/dashboard/denials-by-category`),
                          fetch(`${API_URL}/api/dashboard/denials-by-payer`),
                          fetch(`${API_URL}/api/analytics/resolution-trends`),
                          fetch(`${API_URL}/api/analytics/denial-predictions`),
                          fetch(`${API_URL}/api/analytics/recovery-forecast`),
                          fetch(`${API_URL}/api/analytics/ai-impact`),
                          fetch(`${API_URL}/api/analytics/early-warning`)
                        ])
      
                        setMetrics(await metricsRes.json())
                        setDenialsByCategory(await categoryRes.json())
                        setDenialsByPayer(await payerRes.json())
                        setResolutionTrends(await trendsRes.json())
                        setDenialPredictions(await predictionsRes.json())
                        setRecoveryForecast(await forecastRes.json())
                        setAiImpact(await aiImpactRes.json())
                        setEarlyWarning(await earlyWarningRes.json())
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

    const fetchCFOData = async () => {
      setCfoLoading(true)
      try {
        const [kpisRes, waterfallRes, cashRes, budgetRes, payerPerfRes, summaryRes] = await Promise.all([
          fetch(`${API_URL}/api/cfo/kpis`),
          fetch(`${API_URL}/api/cfo/churn-waterfall`),
          fetch(`${API_URL}/api/cfo/cash-forecast`),
          fetch(`${API_URL}/api/cfo/budget-variance`),
          fetch(`${API_URL}/api/cfo/payer-performance`),
          fetch(`${API_URL}/api/cfo/executive-summary`)
        ])
        setCfoKpis(await kpisRes.json())
        setChurnWaterfall(await waterfallRes.json())
        setCashForecast(await cashRes.json())
        setBudgetVariance(await budgetRes.json())
        setPayerPerformance(await payerPerfRes.json())
        setExecutiveSummary(await summaryRes.json())
      } catch (error) {
        console.error('Error fetching CFO data:', error)
      }
      setCfoLoading(false)
    }

    const fetchLifecycleData = async () => {
      setLifecycleLoading(true)
      try {
        const [sourcesRes, highRiskRes, reconRes, chStatusRes] = await Promise.all([
          fetch(`${API_URL}/api/lifecycle/sources`),
          fetch(`${API_URL}/api/lifecycle/high-risk-claims`),
          fetch(`${API_URL}/api/lifecycle/reconciliation`),
          fetch(`${API_URL}/api/clearinghouse/status`)
        ])
        setLifecycleSources(await sourcesRes.json())
        setHighRiskClaims((await highRiskRes.json()).claims || [])
        setReconciliationData(await reconRes.json())
        setClearinghouseStatus(await chStatusRes.json())
      } catch (error) {
        console.error('Error fetching lifecycle data:', error)
      }
      setLifecycleLoading(false)
    }

    // Clearinghouse polling functions
    const pollAvaility = async () => {
      setPollingAvaility(true)
      try {
        const res = await fetch(`${API_URL}/api/clearinghouse/availity/poll`, { method: 'POST' })
        const data = await res.json()
        setClearinghouseLogs(prev => [{
          timestamp: new Date().toISOString(),
          clearinghouse: 'Availity',
          files: data.files_processed || 0,
          claims: data.claims_ingested || 0,
          denials: data.denials_found || 0,
          payers: data.payers_included || []
        }, ...prev.slice(0, 9)])
        // Refresh lifecycle data after polling
        fetchLifecycleData()
      } catch (error) {
        console.error('Error polling Availity:', error)
      }
      setPollingAvaility(false)
    }

    const pollChangeHealthcare = async () => {
      setPollingChange(true)
      try {
        const res = await fetch(`${API_URL}/api/clearinghouse/change/poll`, { method: 'POST' })
        const data = await res.json()
        setClearinghouseLogs(prev => [{
          timestamp: new Date().toISOString(),
          clearinghouse: 'Change Healthcare',
          files: data.files_processed || 0,
          claims: data.claims_ingested || 0,
          denials: data.denials_found || 0,
          payers: data.payers_included || []
        }, ...prev.slice(0, 9)])
        // Refresh lifecycle data after polling
        fetchLifecycleData()
      } catch (error) {
        console.error('Error polling Change Healthcare:', error)
      }
      setPollingChange(false)
    }

    const simulateBatchTraffic = async (days: number) => {
      setPollingAvaility(true)
      setPollingChange(true)
      try {
        const res = await fetch(`${API_URL}/api/clearinghouse/simulate/batch?days=${days}`, { method: 'POST' })
        const data = await res.json()
        setClearinghouseLogs(prev => [{
          timestamp: new Date().toISOString(),
          clearinghouse: 'Batch Simulation',
          files: data.total_files || 0,
          claims: data.total_claims || 0,
          denials: data.total_denials || 0,
          payers: ['All Payers']
        }, ...prev.slice(0, 9)])
        fetchLifecycleData()
      } catch (error) {
        console.error('Error simulating batch traffic:', error)
      }
      setPollingAvaility(false)
      setPollingChange(false)
    }

    // Helper functions for agent pipeline processing
    const getAgentOutcome = (agentId: string, claimsCount: number, denialsCount: number): { outcome: string, needsHuman: boolean, risk: RiskLevel } => {
      const outcomes: Record<string, { outcomes: string[], needsHuman: boolean[], risks: RiskLevel[] }> = {
        'intake': { 
          outcomes: [`Parsed ${claimsCount} claims from 835 EDI feed`, `Normalized ${claimsCount} claim records successfully`],
          needsHuman: [false, false],
          risks: ['low', 'low']
        },
        'eligibility': {
          outcomes: [`${Math.max(0, claimsCount - denialsCount)} claims verified eligible`, `${denialsCount > 0 ? Math.ceil(denialsCount * 0.3) : 0} eligibility issues flagged`],
          needsHuman: [false, denialsCount > 2],
          risks: ['low', denialsCount > 2 ? 'medium' : 'low']
        },
        'coding': {
          outcomes: [`Validated CPT/ICD codes for ${claimsCount} claims`, `${denialsCount > 0 ? Math.ceil(denialsCount * 0.4) : 0} coding discrepancies found`],
          needsHuman: [false, denialsCount > 3],
          risks: ['low', denialsCount > 3 ? 'high' : 'medium']
        },
        'medical_necessity': {
          outcomes: [`${Math.max(0, claimsCount - Math.ceil(denialsCount * 0.5))} claims meet medical necessity`, `${Math.ceil(denialsCount * 0.5)} claims need clinical review`],
          needsHuman: [false, true],
          risks: ['low', 'high']
        },
        'timely_filing': {
          outcomes: [`All ${claimsCount} claims within filing deadline`, `${Math.ceil(denialsCount * 0.1)} claims near deadline - expedite`],
          needsHuman: [false, false],
          risks: ['low', 'medium']
        },
        'documentation': {
          outcomes: [`Documentation complete for ${Math.max(0, claimsCount - Math.ceil(denialsCount * 0.3))} claims`, `${Math.ceil(denialsCount * 0.3)} claims missing clinical notes`],
          needsHuman: [false, denialsCount > 1],
          risks: ['low', denialsCount > 1 ? 'high' : 'medium']
        },
        'appeal_strategy': {
          outcomes: [`Generated appeal strategies for ${denialsCount} denials`, `${Math.ceil(denialsCount * 0.6)} denials have high appeal success probability`],
          needsHuman: [false, false],
          risks: ['low', 'low']
        },
        'risk_triage': {
          outcomes: [`Routed ${Math.max(0, denialsCount - Math.ceil(denialsCount * 0.4))} low-risk denials for auto-processing`, `${Math.ceil(denialsCount * 0.4)} high-risk denials queued for nurse review`],
          needsHuman: [false, denialsCount > 0],
          risks: ['low', denialsCount > 2 ? 'high' : 'medium']
        }
      }
      
      const agentData = outcomes[agentId] || { outcomes: ['Processing complete'], needsHuman: [false], risks: ['low' as RiskLevel] }
      const idx = denialsCount > 0 && agentData.outcomes.length > 1 ? 1 : 0
      return {
        outcome: agentData.outcomes[idx],
        needsHuman: agentData.needsHuman[idx],
        risk: agentData.risks[idx]
      }
    }

    const [isLiveAI, setIsLiveAI] = useState(false)
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [aiModelsUsed, _setAiModelsUsed] = useState<string[]>([])
    
    const triggerFeedIngestion = async (source: string) => {
      setFeedRunning(true)
      setAgentSummary(null)
      setIsLiveAI(false)
      
      // Clear any previous animation interval
      if (feedAgentIntervalRef.current) {
        clearInterval(feedAgentIntervalRef.current)
        feedAgentIntervalRef.current = null
      }
      
      // Reset pipeline to initial state
      const resetPipeline = INITIAL_AGENT_PIPELINE.map(a => ({ ...a, status: 'pending' as AgentStatus, risk: null, outcome: null, needsHuman: null }))
      setAgentPipeline(resetPipeline)
      agentStepIndexRef.current = 0
      setAgentStepIndex(0)
      
      // Use refs to store feed data so animation can access it
      const feedDataRef = { current: { claimsCount: 8, denialsCount: 3 } }
      
      // Start the API call in the background (non-blocking)
      const ingestPromise = (async () => {
        try {
          const res = await fetch(`${API_URL}/api/feeds/ingest/${source}`, { method: 'POST' })
          const data = await res.json()
          console.log('Feed ingestion result:', data)
          feedDataRef.current = {
            claimsCount: data.claims_added || data.claims_count || 8,
            denialsCount: data.denials_added || data.denials_count || 3
          }
          return data
        } catch (error) {
          console.error('Error triggering feed ingestion:', error)
          return {}
        }
      })()
      
      // Start the animation IMMEDIATELY (runs in parallel with API call)
      const animatePipeline = () => {
        return new Promise<void>((resolve) => {
          let currentStep = 0
          
          // Mark first step as running immediately
          setAgentPipeline(prev => {
            const next = [...prev]
            next[0] = { ...next[0], status: 'running' }
            return next
          })
          
          feedAgentIntervalRef.current = setInterval(() => {
            setAgentPipeline(prev => {
              const next = [...prev]
              const { claimsCount, denialsCount } = feedDataRef.current
              
              // Complete current step
              if (currentStep < next.length && next[currentStep].status === 'running') {
                const result = getAgentOutcome(next[currentStep].id, claimsCount, denialsCount)
                next[currentStep] = {
                  ...next[currentStep],
                  status: result.needsHuman ? 'needs_review' : 'auto_processed',
                  risk: result.risk,
                  outcome: result.outcome,
                  needsHuman: result.needsHuman
                }
              }
              
              // Move to next step
              currentStep++
              agentStepIndexRef.current = currentStep
              setAgentStepIndex(currentStep)
              
              if (currentStep < next.length) {
                next[currentStep] = { ...next[currentStep], status: 'running' }
              } else {
                // Animation complete
                if (feedAgentIntervalRef.current) {
                  clearInterval(feedAgentIntervalRef.current)
                  feedAgentIntervalRef.current = null
                }
                resolve()
              }
              
              return next
            })
          }, 1500)
        })
      }
      
      // Run animation and API call in parallel
      await Promise.all([ingestPromise, animatePipeline()])
      
      // Now both are complete - update summary with actual data
      const claimsCount = feedDataRef.current.claimsCount
      const denialsCount = feedDataRef.current.denialsCount
      
      setAgentPipeline(prev => {
        const autoProcessed = prev.filter(a => a.status === 'auto_processed').length
        const needsReview = prev.filter(a => a.status === 'needs_review').length
        const lowRisk = prev.filter(a => a.risk === 'low').length
        const highRisk = prev.filter(a => a.risk === 'high').length
        
        setAgentSummary({
          autoProcessed,
          needsReview,
          lowRisk,
          highRisk,
          claimsAnalyzed: claimsCount,
          denialsFound: denialsCount
        })
        
        return prev
      })
      
      // Track last feed result for display
      setLastFeedResult({
        source: source,
        claims: claimsCount,
        denials: denialsCount,
        time: new Date()
      })
      
      // Refresh data after both animation and ingestion complete
      await fetchFeedStatus()
      await fetchDenials()
      await fetchDashboardData()
      
      setFeedRunning(false)
    }

    const AUTO_FEED_INTERVAL_SECONDS = 30 // 30 seconds for demo (was 2 min)
    
    const toggleAutoFeed = async () => {
      try {
        if (autoFeedEnabled) {
          // Stop auto-feed
          await fetch(`${API_URL}/api/feeds/stop-auto`, { method: 'POST' })
          setAutoFeedEnabled(false)
          setAutoFeedCountdown(0)
          // Clear intervals
          if (autoFeedIntervalRef.current) {
            clearInterval(autoFeedIntervalRef.current)
            autoFeedIntervalRef.current = null
          }
          if (countdownIntervalRef.current) {
            clearInterval(countdownIntervalRef.current)
            countdownIntervalRef.current = null
          }
        } else {
          // Start auto-feed
          await fetch(`${API_URL}/api/feeds/start-auto`, { method: 'POST' })
          setAutoFeedEnabled(true)
          
          // Trigger immediate first feed so user sees instant results
          await triggerFeedIngestion('Availity')
          
          // Set countdown for next feed
          setAutoFeedCountdown(AUTO_FEED_INTERVAL_SECONDS)
          
          // Start countdown timer (updates every second)
          countdownIntervalRef.current = setInterval(() => {
            setAutoFeedCountdown(prev => {
              if (prev <= 1) return AUTO_FEED_INTERVAL_SECONDS
              return prev - 1
            })
          }, 1000)
          
          // Start auto-feed interval
          autoFeedIntervalRef.current = setInterval(async () => {
            // Alternate between sources for variety
            const sources = ['Availity', 'Change Healthcare']
            const source = sources[Math.floor(Math.random() * sources.length)]
            await triggerFeedIngestion(source)
          }, AUTO_FEED_INTERVAL_SECONDS * 1000)
        }
      } catch (error) {
        console.error('Error toggling auto feed:', error)
      }
    }
    
    // Cleanup intervals on unmount
    useEffect(() => {
      return () => {
        if (autoFeedIntervalRef.current) clearInterval(autoFeedIntervalRef.current)
        if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current)
        if (feedAgentIntervalRef.current) clearInterval(feedAgentIntervalRef.current)
      }
    }, [])

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

    // Re-evaluate existing denial/PA through all 18 agents using REAL Azure AI endpoints
    const reEvaluateClaim = async (claimType: 'denial' | 'pa', claimId: number) => {
      setReEvalRunning(true)
      setReEvalProgress(0)
      setReEvalSteps([])
      setReEvalResult(null)
      setReEvalCurrentAgent('Connecting to Azure AI agents...')

      // Define all 42 AI agents with insights about what changes could improve approval
      const agents = [
        // Denial Management Agents (18)
        { name: "SDOH Scorer", insight: "Analyzing social determinants of health factors...", category: "Patient-Centric", model: "gpt-4.1" },
        { name: "Care Gap Detector", insight: "Checking for gaps in care documentation...", category: "Patient-Centric", model: "gpt-4.1" },
        { name: "Clinical Urgency", insight: "Evaluating clinical urgency indicators...", category: "Patient-Centric", model: "gpt-4.1" },
        { name: "Financial Value", insight: "Calculating financial impact and ROI...", category: "Patient-Centric", model: "gpt-4.1-mini" },
        { name: "Recovery Predictor", insight: "Predicting appeal success probability...", category: "Revenue Intelligence", model: "o3" },
        { name: "P2P Optimizer", insight: "Identifying peer-to-peer review opportunities...", category: "Revenue Intelligence", model: "gpt-4.1" },
        { name: "Queue Wait Time", insight: "Optimizing submission timing...", category: "Revenue Intelligence", model: "gpt-4.1-mini" },
        { name: "Denial Risk Predictor", insight: "Assessing denial risk factors...", category: "Denial Prevention", model: "o3" },
        { name: "Doc Completeness", insight: "Scanning for missing documentation...", category: "Denial Prevention", model: "gpt-4.1" },
        { name: "Policy Monitor", insight: "Checking payer policy compliance...", category: "Denial Prevention", model: "gpt-4.1" },
        { name: "Root Cause Analyzer", insight: "Identifying root cause of denial...", category: "Learning", model: "o3" },
        { name: "Staff Feedback Processor", insight: "Incorporating staff feedback patterns...", category: "Learning", model: "gpt-4.1-mini" },
        { name: "Safety Validator", insight: "Validating clinical safety requirements...", category: "Validation", model: "o1" },
        { name: "Consensus Checker", insight: "Cross-checking agent recommendations...", category: "Validation", model: "gpt-4.1" },
        { name: "Policy Match Grader", insight: "Grading policy criteria alignment...", category: "Validation", model: "gpt-4.1" },
        { name: "Viability Scorer", insight: "Scoring overall approval viability...", category: "Validation", model: "gpt-4.1" },
        { name: "Eligibility Verifier", insight: "Verifying patient eligibility status...", category: "Validation", model: "gpt-4.1-mini" },
        { name: "Follow-up Scheduler", insight: "Planning optimal follow-up actions...", category: "Validation", model: "gpt-4.1-nano" },
        // CFO Intelligence Agents (12)
        { name: "Revenue Forecaster", insight: "Forecasting revenue impact from denials...", category: "CFO Intelligence", model: "o3" },
        { name: "Cash Flow Analyzer", insight: "Analyzing cash flow implications...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Budget Variance Detector", insight: "Detecting budget variances from denials...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Payer Mix Optimizer", insight: "Optimizing payer mix strategy...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Write-off Predictor", insight: "Predicting potential write-offs...", category: "CFO Intelligence", model: "gpt-4.1-mini" },
        { name: "Collection Probability", insight: "Calculating collection probability...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "AR Aging Analyzer", insight: "Analyzing accounts receivable aging...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Cost-to-Collect", insight: "Calculating cost-to-collect ratios...", category: "CFO Intelligence", model: "gpt-4.1-mini" },
        { name: "Net Revenue Impact", insight: "Calculating net revenue impact...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Denial Rate Trend", insight: "Analyzing denial rate trends...", category: "CFO Intelligence", model: "gpt-4.1-mini" },
        { name: "Appeal ROI Calculator", insight: "Calculating appeal return on investment...", category: "CFO Intelligence", model: "gpt-4.1" },
        { name: "Financial Risk Scorer", insight: "Scoring overall financial risk...", category: "CFO Intelligence", model: "o3" },
        // Status Intelligence Agents (8)
        { name: "Front-End Rejection Analyzer", insight: "Analyzing 277CA front-end rejections...", category: "Status Intelligence", model: "o3" },
        { name: "Appeal Deadline Risk", insight: "Assessing appeal deadline urgency...", category: "Status Intelligence", model: "o3" },
        { name: "Pending Claim Risk", insight: "Scoring risk for pending claims...", category: "Status Intelligence", model: "gpt-4.1" },
        { name: "Aging Trend Forecaster", insight: "Forecasting A/R aging trends...", category: "Status Intelligence", model: "gpt-4.1" },
        { name: "Payer SLA Monitor", insight: "Monitoring payer SLA compliance...", category: "Status Intelligence", model: "gpt-4.1-mini" },
        { name: "COB Coordination", insight: "Analyzing coordination of benefits...", category: "Status Intelligence", model: "gpt-4.1-mini" },
        { name: "Status Pattern Detector", insight: "Detecting status flow anomalies...", category: "Status Intelligence", model: "deepseek" },
        { name: "Status Summarizer", insight: "Summarizing status intelligence...", category: "Status Intelligence", model: "gpt-4.1-nano" },
        // System Agents (2)
        { name: "Audit Agent", insight: "Validating cross-agent consistency...", category: "System", model: "o3" },
        { name: "Health Check Agent", insight: "Monitoring agent health and performance...", category: "System", model: "gpt-4.1-mini" },
        // RAG Agents (2)
        { name: "Policy RAG Agent", insight: "Retrieving relevant payer policies...", category: "RAG Intelligence", model: "gpt-4.1" },
        { name: "Policy Scraper Agent", insight: "Updating payer policy database...", category: "RAG Intelligence", model: "gpt-4.1-mini" },
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

    // Sparkline bar component for KPI cards
    const SparklineBars = ({ data, color }: { data: number[], color: string }) => {
      const colorClasses: Record<string, { bar: string, active: string }> = {
        blue: { bar: 'bg-blue-500/50', active: 'bg-blue-500' },
        emerald: { bar: 'bg-emerald-500/50', active: 'bg-emerald-500' },
        amber: { bar: 'bg-amber-500/50', active: 'bg-amber-500' },
        red: { bar: 'bg-red-500/50', active: 'bg-red-500' },
        violet: { bar: 'bg-violet-500/50', active: 'bg-violet-500' },
        cyan: { bar: 'bg-cyan-500/50', active: 'bg-cyan-500' },
        indigo: { bar: 'bg-indigo-500/50', active: 'bg-indigo-500' },
      }
      const colors = colorClasses[color] || colorClasses.blue
      const maxVal = Math.max(...data)
      return (
        <div className="mt-2 h-6 flex items-end gap-0.5">
          {data.map((val, i) => (
            <div 
              key={i}
              className={`w-2 rounded-t ${i === data.length - 1 ? colors.active : colors.bar}`}
              style={{ height: `${(val / maxVal) * 100}%` }}
            />
          ))}
        </div>
      )
    }

    const renderDashboard = () => (
      <div className="space-y-6">
        {/* Top Stats Row - New Design with Gradient Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Claims - Blue */}
          <div className="kpi-card-blue hover:border-white/10">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center">
                <FileText className="h-5 w-5 text-blue-400" />
              </div>
              <div className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                <TrendingUp className="w-3 h-3" />
                +12%
              </div>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.total_claims.toLocaleString()}</p>
            <p className="text-xs text-gray-500 mt-1">Total Claims</p>
            <SparklineBars data={[40, 55, 45, 70, 60, 80, 100]} color="blue" />
          </div>
        
          {/* Denial Rate - Red */}
          <div className="kpi-card-red hover:border-white/10">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
                <AlertCircle className="h-5 w-5 text-red-400" />
              </div>
              <span className="text-xs text-gray-400">{metrics?.total_denials} denials</span>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.denial_rate}%</p>
            <p className="text-xs text-gray-500 mt-1">Denial Rate</p>
            <SparklineBars data={[100, 90, 85, 75, 70, 65, 55]} color="red" />
          </div>
        
          {persona === 'clinical' ? (
            /* Avg Time to Treat - Emerald */
            <div className="kpi-card-emerald hover:border-white/10 glow-emerald">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Clock className="h-5 w-5 text-emerald-400" />
                </div>
                <div className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                  <TrendingDown className="w-3 h-3" />
                  -1.5 days
                </div>
              </div>
              <p className="text-2xl font-bold text-white">2.3 days</p>
              <p className="text-xs text-gray-500 mt-1">Avg Time to Treat</p>
              <SparklineBars data={[100, 85, 70, 60, 50, 45, 40]} color="emerald" />
            </div>
          ) : (
            /* At Risk Amount - Amber */
            <div className="kpi-card-amber hover:border-white/10">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                  <DollarSign className="h-5 w-5 text-amber-400" />
                </div>
                <span className="text-xs text-amber-400">Pending recovery</span>
              </div>
              <p className="text-2xl font-bold text-white">{formatCurrency(metrics?.total_denied_amount || 0)}</p>
              <p className="text-xs text-gray-500 mt-1">At Risk Amount</p>
              <SparklineBars data={[50, 60, 55, 75, 70, 85, 90]} color="amber" />
            </div>
          )}
        
          {persona === 'clinical' ? (
            /* Quality Score - Violet */
            <div className="kpi-card-violet hover:border-white/10 glow-violet">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                  <Activity className="h-5 w-5 text-violet-400" />
                </div>
                <div className="flex items-center gap-1 text-xs font-medium text-emerald-400">
                  <TrendingUp className="w-3 h-3" />
                  +3.1%
                </div>
              </div>
              <p className="text-2xl font-bold text-white">94.2%</p>
              <p className="text-xs text-gray-500 mt-1">Quality Score</p>
              <SparklineBars data={[70, 75, 80, 85, 88, 92, 94]} color="violet" />
            </div>
          ) : (
            /* Recovery Rate - Emerald */
            <div className="kpi-card-emerald hover:border-white/10 glow-emerald">
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <TrendingUp className="h-5 w-5 text-emerald-400" />
                </div>
                <span className="text-xs text-gray-400">{formatCurrency(metrics?.total_recovered_amount || 0)}</span>
              </div>
              <p className="text-2xl font-bold text-white">{metrics?.recovery_rate}%</p>
              <p className="text-xs text-gray-500 mt-1">Recovery Rate</p>
              <SparklineBars data={[50, 60, 55, 75, 70, 85, 90]} color="emerald" />
            </div>
                  )}
                </div>

                {/* Early Warning Panel - Denial Spikes Alert */}
                {earlyWarning && (earlyWarning.summary?.high_severity > 0 || earlyWarning.health_status === 'warning') && (
                  <div className="vision-card border-l-4 border-amber-500">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-amber-500/20">
                          <AlertTriangle className="h-5 w-5 text-amber-400" />
                        </div>
                        <div>
                          <h3 className="text-lg font-semibold text-white">Early Warning: Denial Spikes Detected</h3>
                          <p className="text-xs text-slate-400">
                            {earlyWarning.summary?.high_severity} high-severity alerts | {earlyWarning.summary?.claims_at_risk} claims at risk | 
                            Est. ${(earlyWarning.summary?.estimated_revenue_at_risk / 1000).toFixed(0)}K revenue at risk
                          </p>
                        </div>
                      </div>
                      <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                        earlyWarning.health_score < 50 ? 'bg-red-500/20 text-red-400' :
                        earlyWarning.health_score < 70 ? 'bg-amber-500/20 text-amber-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        Health Score: {earlyWarning.health_score}/100
                      </div>
                    </div>
            
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                      {/* Payer Spikes */}
                      <div>
                        <div className="text-sm font-medium text-slate-300 mb-2">Top Payer Spikes (vs 30-day baseline)</div>
                        <div className="space-y-2">
                          {earlyWarning.payer_spikes?.slice(0, 3).map((spike: any, i: number) => (
                            <div key={i} className={`p-3 rounded-lg ${
                              spike.severity === 'high' ? 'bg-red-500/10 border border-red-500/30' :
                              spike.severity === 'medium' ? 'bg-amber-500/10 border border-amber-500/30' :
                              'bg-slate-700/50'
                            }`}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-white">{spike.payer} - {spike.category}</span>
                                <span className={`text-sm font-bold ${spike.change_pct > 25 ? 'text-red-400' : 'text-amber-400'}`}>
                                  +{spike.change_pct.toFixed(1)}%
                                </span>
                              </div>
                              <div className="text-xs text-slate-400 mb-1">
                                {spike.baseline_rate.toFixed(1)}% → {spike.current_rate.toFixed(1)}% | {spike.denial_count_7d} denials this week
                              </div>
                              <div className="text-xs text-blue-400">
                                Action: {spike.action}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
              
                      {/* Category Spikes */}
                      <div>
                        <div className="text-sm font-medium text-slate-300 mb-2">Top Category Spikes (all payers)</div>
                        <div className="space-y-2">
                          {earlyWarning.category_spikes?.slice(0, 3).map((spike: any, i: number) => (
                            <div key={i} className={`p-3 rounded-lg ${
                              spike.severity === 'high' ? 'bg-red-500/10 border border-red-500/30' :
                              spike.severity === 'medium' ? 'bg-amber-500/10 border border-amber-500/30' :
                              'bg-slate-700/50'
                            }`}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-white">{spike.category}</span>
                                <span className={`text-sm font-bold ${spike.change_pct > 25 ? 'text-red-400' : 'text-amber-400'}`}>
                                  +{spike.change_pct.toFixed(1)}%
                                </span>
                              </div>
                              <div className="text-xs text-slate-400 mb-1">
                                {spike.baseline_rate.toFixed(1)}% → {spike.current_rate.toFixed(1)}% | Top: {spike.top_payers?.join(', ')}
                              </div>
                              <div className="text-xs text-blue-400">
                                Action: {spike.action}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
            
                    <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between">
                      <div className="text-xs text-slate-500">
                        Comparing: {earlyWarning.comparison_period} vs {earlyWarning.baseline_period}
                      </div>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="text-xs"
                        onClick={() => setActiveTab('denials')}
                      >
                        View All Denials
                      </Button>
                    </div>
                  </div>
                )}

                {/* Second Stats Row - New Design with Gradient Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Pending Appeals - Violet */}
          <div className="kpi-card-violet hover:border-white/10">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-violet-500/20 flex items-center justify-center">
                <Clock className="h-5 w-5 text-violet-400" />
              </div>
              <span className="text-xs text-emerald-400">{metrics?.avg_appeal_success_rate}% success</span>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.pending_appeals}</p>
            <p className="text-xs text-gray-500 mt-1">Pending Appeals</p>
            <SparklineBars data={[30, 45, 35, 50, 40, 55, 45]} color="violet" />
          </div>
        
          {/* High Priority - Red with glow */}
          <div className="kpi-card-red hover:border-white/10 glow-red">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center">
                <Zap className="h-5 w-5 text-red-400" />
              </div>
              <span className="text-xs text-red-400">Immediate attention</span>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.high_priority_denials}</p>
            <p className="text-xs text-gray-500 mt-1">High Priority</p>
            <SparklineBars data={[60, 70, 65, 80, 75, 85, 90]} color="red" />
          </div>
        
          {/* 835 Remittances - Cyan */}
          <div className="kpi-card-cyan hover:border-white/10">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                <FileText className="h-5 w-5 text-cyan-400" />
              </div>
              <span className="text-xs text-gray-400">Processed this month</span>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.total_claims.toLocaleString()}</p>
            <p className="text-xs text-gray-500 mt-1">835 Remittances</p>
            <SparklineBars data={[50, 60, 55, 75, 70, 85, 90]} color="cyan" />
          </div>
        
          {/* Avg Queue Wait - Dynamic color based on wait time */}
          <div className={`${
            (metrics?.avg_queue_wait_time_seconds || 0) > 86400 ? 'kpi-card-red glow-red' : 
            (metrics?.avg_queue_wait_time_seconds || 0) > 3600 ? 'kpi-card-amber' : 'kpi-card-emerald glow-emerald'
          } hover:border-white/10`}>
            <div className="flex items-start justify-between mb-3">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                (metrics?.avg_queue_wait_time_seconds || 0) > 86400 ? 'bg-red-500/20' : 
                (metrics?.avg_queue_wait_time_seconds || 0) > 3600 ? 'bg-amber-500/20' : 'bg-emerald-500/20'
              }`}>
                <Clock className={`h-5 w-5 ${
                  (metrics?.avg_queue_wait_time_seconds || 0) > 86400 ? 'text-red-400' : 
                  (metrics?.avg_queue_wait_time_seconds || 0) > 3600 ? 'text-amber-400' : 'text-emerald-400'
                }`} />
              </div>
              <span className="text-xs text-gray-400">Time in queue</span>
            </div>
            <p className="text-2xl font-bold text-white">{metrics?.avg_queue_wait_time_display || '0m'}</p>
            <p className="text-xs text-gray-500 mt-1">Avg Queue Wait</p>
            <SparklineBars 
              data={[80, 70, 65, 55, 50, 45, 40]} 
              color={(metrics?.avg_queue_wait_time_seconds || 0) > 86400 ? 'red' : (metrics?.avg_queue_wait_time_seconds || 0) > 3600 ? 'amber' : 'emerald'} 
            />
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
                          <TableHead>Queue Time</TableHead>
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
                            <TableCell>
                              <span className={`text-sm font-medium ${
                                (denial.queue_wait_time_seconds || 0) > 86400 ? 'text-red-400' : 
                                (denial.queue_wait_time_seconds || 0) > 3600 ? 'text-amber-400' : 'text-slate-400'
                              }`}>
                                {denial.queue_wait_time_display || '-'}
                              </span>
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

                    {/* Status Intelligence - Case Nurse Reconciliation */}
                    <div className="text-xs text-slate-400 uppercase font-semibold mt-3 mb-1">AI Status Intelligence</div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between p-2 bg-cyan-900/30 rounded border border-cyan-500/30">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4 text-cyan-400" />
                          <div>
                            <div className="text-xs font-medium text-white">COB Resolution</div>
                            <div className="text-xs text-slate-400">Coordination of Benefits analysis</div>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-xs text-cyan-400 border-cyan-400/50">STS-006</Badge>
                      </div>
                      <div className="flex items-center justify-between p-2 bg-amber-900/30 rounded border border-amber-500/30">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-amber-400" />
                          <div>
                            <div className="text-xs font-medium text-white">Claim Risk Alert</div>
                            <div className="text-xs text-slate-400">Pending claim denial risk scoring</div>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-xs text-amber-400 border-amber-400/50">STS-003</Badge>
                      </div>
                      <div className="flex items-center justify-between p-2 bg-red-900/30 rounded border border-red-500/30">
                        <div className="flex items-center gap-2">
                          <Activity className="h-4 w-4 text-red-400" />
                          <div>
                            <div className="text-xs font-medium text-white">Stuck Claims</div>
                            <div className="text-xs text-slate-400">Detects unusual status flow patterns</div>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-xs text-red-400 border-red-400/50">STS-007</Badge>
                      </div>
                    </div>
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

            {/* Re-Evaluate with 42 AI Agents */}
            <Card className={`bg-gradient-to-r from-purple-900/30 to-pink-900/30 ${changesNeedReEval ? 'border-amber-500 border-2 animate-pulse' : 'border-purple-500/30'}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="h-4 w-4 text-purple-400" />
                  Re-Evaluate with 42 AI Agents
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
                          {step.model && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0 h-4 bg-slate-700/50 border-slate-600">
                              {step.model}
                            </Badge>
                          )}
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
                <p className="font-medium text-slate-200">Auto-Ingest (every 30 sec)</p>
                <p className="text-xs text-slate-400">Automatically fetch new claims from clearinghouses</p>
              </div>
              <Button 
                onClick={toggleAutoFeed}
                variant={autoFeedEnabled ? "destructive" : "outline"}
                size="sm"
                className={autoFeedEnabled ? "bg-red-600 hover:bg-red-700" : ""}
              >
                {feedRunning ? (
                  <>
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                    Ingesting...
                  </>
                ) : autoFeedEnabled ? (
                  <>
                    <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse" />
                    Stop
                  </>
                ) : 'Start'}
              </Button>
            </div>
            
            {/* Auto-Feed Status - shows when running */}
            {autoFeedEnabled && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                    <span className="text-emerald-400 font-medium text-sm">Auto-Ingest Running</span>
                  </div>
                  <span className="text-slate-300 text-sm">
                    Next feed in: <span className="font-mono text-emerald-400">{autoFeedCountdown}s</span>
                  </span>
                </div>
                
                {lastFeedResult && !feedRunning && (
                  <p className="text-xs text-slate-400 mt-2">
                    Last: {lastFeedResult.claims} claims ({lastFeedResult.denials} denials) from {lastFeedResult.source} at {lastFeedResult.time.toLocaleTimeString()}
                  </p>
                )}
              </div>
            )}
            
            {/* Step-by-Step Agentic Workflow Timeline */}
            {(feedRunning || agentSummary) && (
              <div className="p-4 bg-slate-900/60 border border-slate-700 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-200 flex items-center gap-2">
                    <Brain className="h-4 w-4 text-blue-400" />
                    Agentic Workflow Pipeline
                    {isLiveAI && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/20 border border-green-500/50 text-green-300 font-normal">
                        Live AI (Azure)
                      </span>
                    )}
                  </span>
                  <div className="flex items-center gap-2">
                    {isLiveAI && aiModelsUsed.length > 0 && (
                      <span className="text-xs text-slate-500">
                        Models: {aiModelsUsed.slice(0, 3).join(', ')}{aiModelsUsed.length > 3 ? '...' : ''}
                      </span>
                    )}
                    {agentSummary && (
                      <span className="text-xs text-slate-400">
                        {agentSummary.claimsAnalyzed} claims · {agentSummary.denialsFound} denials
                      </span>
                    )}
                  </div>
                </div>
                
                {/* Pipeline Steps */}
                <div className="space-y-2">
                  {agentPipeline.map((step, idx) => (
                    <div
                      key={step.id}
                      className={`flex items-start gap-3 p-2 rounded-lg border transition-all duration-300 ${
                        step.status === 'running'
                          ? 'bg-blue-500/10 border-blue-500/40'
                          : step.status === 'needs_review'
                          ? 'bg-amber-500/10 border-amber-500/40'
                          : step.status === 'auto_processed'
                          ? 'bg-emerald-500/10 border-emerald-500/40'
                          : 'bg-slate-800/40 border-slate-700/40'
                      }`}
                    >
                      {/* Step Number */}
                      <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                        step.status === 'running' ? 'bg-blue-500 text-white' :
                        step.status === 'needs_review' ? 'bg-amber-500 text-white' :
                        step.status === 'auto_processed' ? 'bg-emerald-500 text-white' :
                        'bg-slate-700 text-slate-400'
                      }`}>
                        {idx + 1}
                      </div>
                      
                      {/* Step Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`font-medium text-sm ${
                            step.status === 'pending' ? 'text-slate-500' : 'text-slate-100'
                          }`}>
                            {step.name}
                          </span>
                          
                          {/* Status Badge */}
                          {step.status === 'running' && (
                            <span className="flex items-center gap-1 text-xs text-blue-300 bg-blue-500/20 px-2 py-0.5 rounded-full">
                              <RefreshCw className="h-3 w-3 animate-spin" />
                              Processing...
                            </span>
                          )}
                          {step.status === 'auto_processed' && (
                            <span className="flex items-center gap-1 text-xs text-emerald-300 bg-emerald-500/20 px-2 py-0.5 rounded-full">
                              <CheckCircle className="h-3 w-3" />
                              Auto-processed
                              {step.risk && <span className="ml-1 opacity-70">({step.risk} risk)</span>}
                            </span>
                          )}
                          {step.status === 'needs_review' && (
                            <span className="flex items-center gap-1 text-xs text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded-full">
                              <AlertTriangle className="h-3 w-3" />
                              Needs Review
                              {step.risk && <span className="ml-1 opacity-70">({step.risk} risk)</span>}
                            </span>
                          )}
                        </div>
                        
                        {/* Outcome or Description */}
                        <p className={`text-xs mt-0.5 ${
                          step.outcome ? 'text-slate-300' : 'text-slate-500'
                        }`}>
                          {step.outcome || step.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Summary Section */}
                {agentSummary && (
                  <div className="mt-4 pt-3 border-t border-slate-700">
                    <div className="flex flex-wrap gap-2">
                      <span className="text-xs px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300">
                        <CheckCircle className="h-3 w-3 inline mr-1" />
                        {agentSummary.autoProcessed} steps auto-processed
                      </span>
                      <span className="text-xs px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300">
                        <AlertTriangle className="h-3 w-3 inline mr-1" />
                        {agentSummary.needsReview} steps need human review
                      </span>
                      <span className="text-xs px-3 py-1.5 rounded-full bg-blue-500/20 border border-blue-500/40 text-blue-300">
                        Low risk: {agentSummary.lowRisk} · High risk: {agentSummary.highRisk}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-2">
                      Pipeline complete. {agentSummary.needsReview > 0 
                        ? `${agentSummary.needsReview} items flagged for nurse review in Denials tab.`
                        : 'All items auto-processed successfully.'}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Feed Status */}
            {feedStatus && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-2 bg-slate-800/50 rounded text-center">
                  <div className="text-xl font-bold text-blue-400">{feedStatus.total_feeds_today || feedStatus.feeds_today || 0}</div>
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
                    {isNaN(recoveryRate.overall_success_rate) || recoveryRate.overall_success_rate === null 
                      ? '0.0' 
                      : (recoveryRate.overall_success_rate * 100).toFixed(1)}%
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

      {/* Simple note about AI verification */}
      <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 text-center">
        <p className="text-sm text-slate-300">
          <Shield className="h-4 w-4 inline mr-2 text-purple-400" />
          18 AI agents analyze each denial. High-risk decisions require human review.
        </p>
      </div>
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

      <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-slate-800/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold text-white">Denial Rate Comparison</CardTitle>
          <CardDescription className="text-slate-400">Denial rates and appeal success across all payers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart 
                data={payers} 
                layout="vertical"
                margin={{ top: 10, right: 30, left: 10, bottom: 10 }}
                barGap={4}
                barCategoryGap="20%"
              >
                <defs>
                  <linearGradient id="denialGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#dc2626" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#f87171" stopOpacity={0.9} />
                  </linearGradient>
                  <linearGradient id="successGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#059669" stopOpacity={0.9} />
                    <stop offset="100%" stopColor="#34d399" stopOpacity={0.9} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} horizontal={true} vertical={false} />
                <XAxis 
                  type="number" 
                  domain={[0, 0.7]} 
                  tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                  axisLine={{ stroke: '#475569' }}
                  tickLine={{ stroke: '#475569' }}
                />
                <YAxis 
                  type="category" 
                  dataKey="payer_name" 
                  width={140} 
                  tick={{ fill: '#e2e8f0', fontSize: 12, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip 
                  formatter={(value: number, name: string) => [`${(value * 100).toFixed(1)}%`, name]}
                  contentStyle={{ 
                    backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)'
                  }}
                  labelStyle={{ color: '#f1f5f9', fontWeight: 600 }}
                  itemStyle={{ color: '#cbd5e1' }}
                  cursor={{ fill: 'rgba(148, 163, 184, 0.1)' }}
                />
                <Legend 
                  wrapperStyle={{ paddingTop: '20px' }}
                  iconType="circle"
                  formatter={(value) => <span style={{ color: '#e2e8f0', fontSize: '12px', marginLeft: '4px' }}>{value}</span>}
                />
                <Bar 
                  dataKey="avg_denial_rate" 
                  name="Denial Rate" 
                  fill="url(#denialGradient)"
                  radius={[0, 4, 4, 0]}
                  maxBarSize={18}
                />
                <Bar 
                  dataKey="avg_appeal_success_rate" 
                  name="Appeal Success" 
                  fill="url(#successGradient)"
                  radius={[0, 4, 4, 0]}
                  maxBarSize={18}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  const renderPolicySearch = () => {
    const policyPayers = [
      { id: 'FL_BLUE', name: 'Florida Blue', policies: 3, type: 'Commercial' },
      { id: 'HUMANA_FL', name: 'Humana Florida', policies: 3, type: 'Medicare Advantage' },
      { id: 'FL_MEDICAID', name: 'Florida Medicaid', policies: 3, type: 'Medicaid' },
      { id: 'AETNA_FL', name: 'Aetna Florida', policies: 3, type: 'Commercial' },
      { id: 'MEDICARE', name: 'Medicare (CMS)', policies: 3, type: 'Government' },
      { id: 'UNITED', name: 'United Healthcare', policies: 3, type: 'Commercial' },
      { id: 'CIGNA', name: 'Cigna', policies: 2, type: 'Commercial' },
      { id: 'TRICARE', name: 'TRICARE', policies: 2, type: 'Government' },
      { id: 'ANTHEM', name: 'Anthem/BCBS', policies: 3, type: 'Commercial' },
    ]

    const policyTypes = [
      { type: 'medical_policy', label: 'Medical Policies', count: 9 },
      { type: 'prior_auth', label: 'Prior Authorization', count: 9 },
      { type: 'appeal_procedures', label: 'Appeal Procedures', count: 7 },
    ]

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold flex items-center gap-2">
              <Search className="h-6 w-6 text-blue-500" />
              Payer Policy Search
            </h2>
            <p className="text-muted-foreground">Search across 25 comprehensive policy documents from 9 major US payers</p>
          </div>
          <div className="flex gap-2">
            <Badge className="bg-gradient-to-r from-blue-500 to-cyan-500 text-white px-3 py-1">
              <Brain className="h-3 w-3 mr-1" />
              RAG-Powered
            </Badge>
            <Badge className="bg-gradient-to-r from-emerald-500 to-green-500 text-white px-3 py-1">
              ChromaDB
            </Badge>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Semantic Policy Search
            </CardTitle>
            <CardDescription>
              Search for coverage criteria, prior authorization requirements, appeal procedures, and more
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Search policies... (e.g., 'knee replacement prior authorization', 'MRI coverage criteria')"
                  className="w-full px-4 py-3 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <button className="px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-lg font-medium hover:opacity-90 transition-opacity flex items-center gap-2">
                <Search className="h-4 w-4" />
                Search
              </button>
            </div>
            <div className="flex gap-2 mt-4">
              <Badge variant="outline" className="cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700">All Payers</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700">Prior Auth</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700">Medical Policy</Badge>
              <Badge variant="outline" className="cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700">Appeals</Badge>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Supported Payers ({policyPayers.length})
              </CardTitle>
              <CardDescription>Comprehensive policy coverage for major US health insurers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {policyPayers.map((payer) => (
                  <div
                    key={payer.id}
                    className="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-blue-500 dark:hover:border-blue-500 transition-colors cursor-pointer"
                  >
                    <div className="font-medium">{payer.name}</div>
                    <div className="text-sm text-muted-foreground">{payer.type}</div>
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant="secondary">{payer.policies} policies</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Policy Types
              </CardTitle>
              <CardDescription>Documents by category</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {policyTypes.map((pt) => (
                  <div key={pt.type} className="flex items-center justify-between">
                    <span className="text-sm font-medium">{pt.label}</span>
                    <Badge>{pt.count}</Badge>
                  </div>
                ))}
                <div className="pt-4 border-t">
                  <div className="flex items-center justify-between font-semibold">
                    <span>Total Policies</span>
                    <Badge className="bg-blue-500 text-white">25</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-slate-800/50">
          <CardHeader>
            <CardTitle className="text-lg font-semibold text-white flex items-center gap-2">
              <Brain className="h-5 w-5 text-cyan-400" />
              AI-Powered Policy Intelligence
            </CardTitle>
            <CardDescription className="text-slate-400">
              How the RAG system enhances claim validation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-cyan-400 font-semibold mb-2">PolicyRAGAgent (RAG-001)</div>
                <p className="text-sm text-slate-300">
                  Validates claims against payer-specific policies using semantic search. Returns compliance scores (0-100) with specific policy citations.
                </p>
                <Badge className="mt-2 bg-cyan-500/20 text-cyan-300">gpt-4.1</Badge>
              </div>
              <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-emerald-400 font-semibold mb-2">PolicyScraperAgent (SYS-003)</div>
                <p className="text-sm text-slate-300">
                  Automated weekly scraping of payer portals with AI-powered parsing, change detection, and version tracking.
                </p>
                <Badge className="mt-2 bg-emerald-500/20 text-emerald-300">gpt-4.1-mini</Badge>
              </div>
              <div className="p-4 rounded-lg bg-slate-800/50 border border-slate-700">
                <div className="text-violet-400 font-semibold mb-2">ChromaDB Vector Store</div>
                <p className="text-sm text-slate-300">
                  Semantic embeddings enable natural language policy search. Find relevant coverage criteria instantly.
                </p>
                <Badge className="mt-2 bg-violet-500/20 text-violet-300">sentence-transformers</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // CFO Dashboard KPI Card with sparkline bars (new design)
  const CFOKPICard = ({ title, value, trend, trendValue, subtitle, alert, trendData, color = 'blue', icon }: {
    title: string;
    value: string;
    trend?: 'up' | 'down' | 'flat';
    trendValue?: string;
    subtitle?: string;
    alert?: boolean;
    trendData?: { v: number }[];
    color?: 'blue' | 'emerald' | 'amber' | 'violet' | 'red' | 'cyan' | 'indigo';
    icon?: React.ReactNode;
  }) => {
    const colorClasses = {
      blue: 'kpi-card-blue',
      emerald: 'kpi-card-emerald glow-emerald',
      amber: 'kpi-card-amber',
      violet: 'kpi-card-violet',
      red: 'kpi-card-red glow-red',
      cyan: 'kpi-card-cyan',
      indigo: 'kpi-card-indigo',
    };
    const iconBgClasses = {
      blue: 'bg-blue-500/20',
      emerald: 'bg-emerald-500/20',
      amber: 'bg-amber-500/20',
      violet: 'bg-violet-500/20',
      red: 'bg-red-500/20',
      cyan: 'bg-cyan-500/20',
      indigo: 'bg-indigo-500/20',
    };
    const iconColorClasses = {
      blue: 'text-blue-400',
      emerald: 'text-emerald-400',
      amber: 'text-amber-400',
      violet: 'text-violet-400',
      red: 'text-red-400',
      cyan: 'text-cyan-400',
      indigo: 'text-indigo-400',
    };
    const barColorClasses = {
      blue: 'bg-blue-500/50',
      emerald: 'bg-emerald-500/50',
      amber: 'bg-amber-500/50',
      violet: 'bg-violet-500/50',
      red: 'bg-red-500/50',
      cyan: 'bg-cyan-500/50',
      indigo: 'bg-indigo-500/50',
    };
    const barActiveClasses = {
      blue: 'bg-blue-500',
      emerald: 'bg-emerald-500',
      amber: 'bg-amber-500',
      violet: 'bg-violet-500',
      red: 'bg-red-500',
      cyan: 'bg-cyan-500',
      indigo: 'bg-indigo-500',
    };
    
    return (
      <div className={`${colorClasses[color]} hover:border-white/10`}>
        <div className="flex items-start justify-between mb-3">
          <div className={`w-10 h-10 rounded-xl ${iconBgClasses[color]} flex items-center justify-center`}>
            {icon || <DollarSign className={`w-5 h-5 ${iconColorClasses[color]}`} />}
          </div>
          {trend && trendValue && (
            <div className={`flex items-center gap-1 text-xs font-medium ${
              trend === 'up' ? 'text-emerald-400' : 
              trend === 'down' ? 'text-red-400' : 
              'text-gray-400'
            }`}>
              {trend === 'up' ? <TrendingUp className="w-3 h-3" /> : 
               trend === 'down' ? <TrendingDown className="w-3 h-3" /> : null}
              {trendValue}
            </div>
          )}
          {subtitle && !trendValue && (
            <span className="text-xs text-gray-400">{subtitle}</span>
          )}
        </div>
        <p className={`text-2xl font-bold ${alert ? 'text-red-400' : 'text-white'}`}>{value}</p>
        <p className="text-xs text-gray-500 mt-1">{title}</p>
        {subtitle && trendValue && <p className="text-xs text-gray-600">{subtitle}</p>}
        {trendData && (
          <div className="mt-2 h-6 flex items-end gap-0.5">
            {trendData.map((d, i) => (
              <div 
                key={i} 
                className={`w-2 rounded-t ${i === trendData.length - 1 ? barActiveClasses[color] : barColorClasses[color]}`}
                style={{ height: `${Math.max(20, d.v * 10)}%` }}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  // Generate sparkline trend data
  const generateSparkline = (direction: 'up' | 'down', variance = 0.1) => {
    const base = direction === 'up' ? [3, 4, 3.5, 5, 4.5, 6, 5.5, 7] : [7, 6, 6.5, 5, 5.5, 4, 4.5, 3];
    return base.map((v) => ({ v: v + (Math.random() - 0.5) * variance }));
  };

  // Static data for CFO Dashboard charts (matching reference design)
  const cfoWaterfallData = [
    { name: 'Submitted', value: 12400000, fill: '#3b82f6' },
    { name: 'Contractual', value: -2100000, fill: '#64748b' },
    { name: 'Denials', value: -890000, fill: '#ef4444' },
    { name: 'Patient', value: -310000, fill: '#f59e0b' },
    { name: 'Expected', value: 9100000, fill: '#10b981' },
  ];

  const cfoDenialTrendData = [
    { month: 'Jul', rate: 22.1, predicted: null },
    { month: 'Aug', rate: 21.3, predicted: null },
    { month: 'Sep', rate: 20.8, predicted: null },
    { month: 'Oct', rate: 19.6, predicted: null },
    { month: 'Nov', rate: 18.9, predicted: null },
    { month: 'Dec', rate: 18.5, predicted: 18.5 },
    { month: 'Jan', rate: null, predicted: 17.8 },
    { month: 'Feb', rate: null, predicted: 17.2 },
    { month: 'Mar', rate: null, predicted: 16.5 },
  ];

  const cfoCashForecastData = [
    { week: 'W1', expected: 2100, low: 1850, high: 2350, lastYear: 1950 },
    { week: 'W2', expected: 2400, low: 2100, high: 2700, lastYear: 2200 },
    { week: 'W3', expected: 2650, low: 2300, high: 3000, lastYear: 2400 },
    { week: 'W4', expected: 2200, low: 1900, high: 2500, lastYear: 2100 },
    { week: 'W5', expected: 2500, low: 2150, high: 2850, lastYear: 2300 },
    { week: 'W6', expected: 2800, low: 2400, high: 3200, lastYear: 2500 },
    { week: 'W7', expected: 2300, low: 1950, high: 2650, lastYear: 2150 },
    { week: 'W8', expected: 2600, low: 2250, high: 2950, lastYear: 2400 },
    { week: 'W9', expected: 2450, low: 2100, high: 2800, lastYear: 2250 },
    { week: 'W10', expected: 2700, low: 2350, high: 3050, lastYear: 2500 },
    { week: 'W11', expected: 2550, low: 2200, high: 2900, lastYear: 2350 },
    { week: 'W12', expected: 2900, low: 2500, high: 3300, lastYear: 2600 },
  ];

  const cfoPayerTrendData = [
    { payer: 'Medicare', current: 8, prev: 9, trend: 'improving' as const, forecast: 7.5 },
    { payer: 'BCBS FL', current: 28, prev: 22, trend: 'worsening' as const, forecast: 31 },
    { payer: 'United', current: 17, prev: 19, trend: 'improving' as const, forecast: 15 },
    { payer: 'Aetna', current: 32, prev: 28, trend: 'worsening' as const, forecast: 35 },
    { payer: 'Cigna', current: 21, prev: 21, trend: 'stable' as const, forecast: 21 },
    { payer: 'Humana', current: 19, prev: 20, trend: 'improving' as const, forecast: 18 },
  ];

  const cfoBudgetData = [
    { month: 'Dec 2025', budget: 10.2, forecast: 10.1, variance: -0.1, confidence: 94, status: 'on-track' as const },
    { month: 'Jan 2026', budget: 9.8, forecast: 9.4, variance: -0.4, confidence: 87, status: 'monitor' as const },
    { month: 'Feb 2026', budget: 10.5, forecast: 10.8, variance: 0.3, confidence: 82, status: 'on-track' as const },
    { month: 'Mar 2026', budget: 11.2, forecast: 10.1, variance: -1.1, confidence: 75, status: 'at-risk' as const },
  ];

  const cfoHighRiskClaims = [
    { id: 'CLM-10892', patient: 'Adams, R', payer: 'Aetna', amount: 12400, risk: 78, confidence: 92, factor: 'No prior auth', deadline: '24h', trend: 'Pattern: 94% denial rate for this procedure without PA' },
    { id: 'CLM-10893', patient: 'Baker, S', payer: 'BCBS FL', amount: 8200, risk: 72, confidence: 87, factor: 'Missing H&P', deadline: '48h', trend: 'BCBS denial rate up 6% this month' },
    { id: 'CLM-10901', patient: 'Clark, J', payer: 'United', amount: 5100, risk: 54, confidence: 81, factor: 'Coding review', deadline: '72h', trend: 'Similar claims denied 3x in last 30 days' },
  ];

  // Scenario modeler calculations
  const baselineCollection = 40.4;
  const denialImpact = (18.5 - scenarioDenialRate) * 0.56;
  const appealImpact = (scenarioAppealSuccess - 67) * 0.08;
  const projectedCollection = baselineCollection + denialImpact + appealImpact;
  const annualImpact = (denialImpact + appealImpact) * 4;

  const renderCFODashboard = () => (
    <div className="space-y-6">
      {cfoLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin mr-2" />
          <span>Loading CFO Dashboard...</span>
        </div>
      ) : (
        <>
          {/* Executive Summary Banner */}
          <Card className="bg-gradient-to-r from-blue-900/50 via-indigo-900/50 to-slate-950/80 border-blue-700/50">
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white mb-2">Executive Summary</h2>
                  <p className="text-slate-300 max-w-3xl">
                    This month we've submitted $12.4M in claims with an expected collection of $10.1M (81.5% yield). 
                    Our AI prediction accuracy remains strong. We've flagged 23 high-risk claims that need action this week.
                  </p>
                </div>
                <div className="flex items-center space-x-2 bg-red-500/20 px-3 py-1.5 rounded-lg border border-red-500/30">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-red-400 font-medium">23 High-Risk Claims</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 8 KPI Cards with Sparklines - Different colors per card */}
          <div className="grid grid-cols-4 gap-4">
            <CFOKPICard 
              title="Submitted (837s MTD)" 
              value="$12.4M" 
              trend="up" 
              trendValue="+8.2%" 
              subtitle="vs $11.5M last month"
              trendData={generateSparkline('up')}
              color="blue"
              icon={<FileText className="w-5 h-5 text-blue-400" />}
            />
            <CFOKPICard 
              title="Expected Collection" 
              value="$10.1M" 
              trend="up" 
              trendValue="+6.1%" 
              subtitle="81.5% predicted yield"
              trendData={generateSparkline('up')}
              color="emerald"
              icon={<DollarSign className="w-5 h-5 text-emerald-400" />}
            />
            <CFOKPICard 
              title="Churn Rate" 
              value="18.5%" 
              trend="down" 
              trendValue="-2.1%" 
              subtitle="Trending down from 22.1% in July"
              trendData={generateSparkline('down')}
              color="amber"
              icon={<TrendingDown className="w-5 h-5 text-amber-400" />}
            />
            <CFOKPICard 
              title="Recoverable via Appeal" 
              value="$1.8M" 
              trend="up" 
              trendValue="+12.4%" 
              subtitle="67% success rate with AI"
              trendData={generateSparkline('up')}
              color="violet"
              icon={<RefreshCw className="w-5 h-5 text-violet-400" />}
            />
            <CFOKPICard 
              title="Write-off Risk" 
              value="$890K" 
              trend="down" 
              trendValue="-15.3%" 
              subtitle="Down from $1.05M last month"
              alert
              trendData={generateSparkline('down')}
              color="red"
              icon={<AlertTriangle className="w-5 h-5 text-red-400" />}
            />
            <CFOKPICard 
              title="Days to Cash" 
              value="42 days" 
              trend="down" 
              trendValue="-3 days" 
              subtitle="Medicare: 28d, Commercial: 45d"
              trendData={generateSparkline('down')}
              color="cyan"
              icon={<Clock className="w-5 h-5 text-cyan-400" />}
            />
            <CFOKPICard 
              title="Forecast Accuracy" 
              value="94.2%" 
              trend="up" 
              trendValue="+1.8%" 
              subtitle="Based on last 90 days"
              trendData={generateSparkline('up')}
              color="indigo"
              icon={<Target className="w-5 h-5 text-indigo-400" />}
            />
            <CFOKPICard 
              title="Cash This Week" 
              value="$2.1M" 
              trend="up" 
              trendValue="+4.2%" 
              subtitle="87% confidence interval"
              trendData={generateSparkline('up')}
              color="emerald"
              icon={<Wallet className="w-5 h-5 text-emerald-400" />}
            />
          </div>

          {/* Row 1: Churn Waterfall + Denial Rate Trend */}
          <div className="grid grid-cols-2 gap-6">
            {/* Churn Waterfall */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">Churn Waterfall - December 2025</CardTitle>
                <CardDescription>From billed amount to expected collection</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cfoWaterfallData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
                      <XAxis 
                        type="number" 
                        tickFormatter={(v) => `$${Math.abs(v/1000000).toFixed(1)}M`} 
                        stroke="#64748b"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                      />
                      <YAxis 
                        type="category" 
                        dataKey="name" 
                        width={80} 
                        stroke="#64748b"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                      />
                      <Tooltip 
                        formatter={(v: number) => `$${Math.abs(v/1000000).toFixed(2)}M`}
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                        labelStyle={{ color: '#f1f5f9' }}
                      />
                      <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                        {cfoWaterfallData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center mt-4 space-x-4 text-xs">
                  <span className="flex items-center text-slate-400"><span className="w-3 h-3 bg-blue-500 rounded mr-1.5"></span>Billed</span>
                  <span className="flex items-center text-slate-400"><span className="w-3 h-3 bg-slate-500 rounded mr-1.5"></span>Contractual</span>
                  <span className="flex items-center text-slate-400"><span className="w-3 h-3 bg-red-500 rounded mr-1.5"></span>Denials</span>
                  <span className="flex items-center text-slate-400"><span className="w-3 h-3 bg-amber-500 rounded mr-1.5"></span>Patient</span>
                  <span className="flex items-center text-slate-400"><span className="w-3 h-3 bg-emerald-500 rounded mr-1.5"></span>Expected</span>
                </div>
              </CardContent>
            </Card>

            {/* Denial Rate Trend & Prediction */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg font-semibold text-white">Denial Rate Trend & Prediction</CardTitle>
                    <CardDescription>6-month history → 3-month forecast</CardDescription>
                  </div>
                  <div className="flex items-center space-x-2 bg-emerald-500/20 px-2 py-1 rounded-lg">
                    <TrendingDown className="w-3 h-3 text-emerald-400" />
                    <span className="text-xs text-emerald-400">-3.6% projected</span>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={cfoDenialTrendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="month" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                      <YAxis 
                        domain={[14, 24]} 
                        tickFormatter={(v) => `${v}%`} 
                        stroke="#64748b"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                        labelStyle={{ color: '#f1f5f9' }}
                        formatter={(v: number) => v ? `${v}%` : 'N/A'}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="rate" 
                        stroke="#3b82f6" 
                        strokeWidth={3} 
                        dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                        name="Actual"
                        connectNulls={false}
                      />
                      <Line 
                        type="monotone" 
                        dataKey="predicted" 
                        stroke="#10b981" 
                        strokeWidth={3} 
                        strokeDasharray="8 4"
                        dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
                        name="Predicted"
                        connectNulls={false}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center mt-2 space-x-6 text-xs">
                  <span className="flex items-center text-slate-400">
                    <span className="w-6 h-0.5 bg-blue-500 rounded mr-2"></span>Historical
                  </span>
                  <span className="flex items-center text-slate-400">
                    <span className="w-6 h-0.5 bg-emerald-500 rounded mr-2"></span>AI Forecast
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Row 2: Cash Forecast + Payer Churn Trends */}
          <div className="grid grid-cols-2 gap-6">
            {/* 90-Day Cash Forecast */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold text-white">90-Day Cash Forecast</CardTitle>
                  <span className="text-xs text-slate-400 bg-slate-700/50 px-2 py-1 rounded">85% confidence</span>
                </div>
                <CardDescription>Expected: $29.4M | Range: $26.8M - $32.1M</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={cfoCashForecastData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                      <XAxis dataKey="week" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <YAxis tickFormatter={(v) => `$${v/1000}K`} stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <Tooltip 
                        formatter={(v: number) => `$${(v * 1000).toLocaleString()}`}
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px' }}
                      />
                      <Area type="monotone" dataKey="high" stroke="transparent" fill="#3b82f6" fillOpacity={0.1} />
                      <Area type="monotone" dataKey="low" stroke="transparent" fill="#0f172a" />
                      <Line type="monotone" dataKey="lastYear" stroke="#64748b" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Last Year" />
                      <Line type="monotone" dataKey="expected" stroke="#3b82f6" strokeWidth={3} dot={false} name="Forecast" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex justify-center mt-2 space-x-6 text-xs">
                  <span className="flex items-center text-slate-400">
                    <span className="w-6 h-0.5 bg-blue-500 rounded mr-2"></span>Forecast
                  </span>
                  <span className="flex items-center text-slate-400">
                    <span className="w-6 h-0.5 bg-slate-500 rounded mr-2"></span>Last Year
                  </span>
                  <span className="flex items-center text-slate-400">
                    <span className="w-4 h-3 bg-blue-500/20 rounded mr-2"></span>Confidence Band
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Payer Churn Trends */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">Payer Churn Trends</CardTitle>
                <CardDescription>Churn rate and trend by payer</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {cfoPayerTrendData.map((payer) => (
                    <div key={payer.payer} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <span className="text-white font-medium w-24">{payer.payer}</span>
                        <div className="flex items-center space-x-2">
                          <span className={`text-sm font-bold ${payer.current > 25 ? 'text-red-400' : payer.current > 15 ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {payer.current}%
                          </span>
                          <span className="text-slate-500 text-xs">churn</span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className={`flex items-center space-x-1 text-xs px-2 py-0.5 rounded-full ${
                          payer.trend === 'improving' ? 'bg-emerald-500/20 text-emerald-400' :
                          payer.trend === 'worsening' ? 'bg-red-500/20 text-red-400' :
                          'bg-slate-600/50 text-slate-400'
                        }`}>
                          {payer.trend === 'improving' ? <TrendingDown className="w-3 h-3" /> :
                           payer.trend === 'worsening' ? <TrendingUp className="w-3 h-3" /> :
                           <span>→</span>}
                          <span>{payer.trend}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs text-slate-400">Forecast: </span>
                          <span className={`text-xs font-medium ${payer.forecast > payer.current ? 'text-red-400' : 'text-emerald-400'}`}>
                            {payer.forecast}%
                          </span>
                        </div>
                        {payer.trend === 'worsening' && (
                          <button className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs font-medium hover:bg-red-500/30 transition-colors">
                            Action
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Row 3: Budget Variance + Scenario Modeler + High-Risk Claims */}
          <div className="grid grid-cols-3 gap-6">
            {/* Budget Variance */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">Q1 Budget vs Trend Forecast</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {cfoBudgetData.map((row) => (
                    <div key={row.month} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div>
                        <span className="text-white font-medium text-sm">{row.month}</span>
                        <div className="text-xs text-slate-400">
                          Budget: ${row.budget}M → Forecast: ${row.forecast}M
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className={`text-sm font-bold ${row.variance >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {row.variance >= 0 ? '+' : ''}{row.variance}M
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          row.status === 'on-track' ? 'bg-emerald-500/20 text-emerald-400' :
                          row.status === 'monitor' ? 'bg-amber-500/20 text-amber-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {row.confidence}%
                        </span>
                      </div>
                    </div>
                  ))}
                  <div className="flex items-center justify-between p-3 bg-slate-600/30 rounded-lg border border-slate-600/50">
                    <div>
                      <span className="text-white font-bold text-sm">Q1 Total</span>
                      <div className="text-xs text-slate-400">$41.7M → $40.4M</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-red-400 font-bold">-$1.3M</span>
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400">
                        84%
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Scenario Modeler */}
            <Card className="bg-slate-900/70 border-slate-800/80">
              <CardHeader>
                <CardTitle className="text-lg font-semibold text-white">What-If Scenario</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-5">
                  <div>
                    <div className="flex justify-between mb-2">
                      <label className="text-sm text-slate-300">Denial Rate</label>
                      <span className="text-sm text-cyan-400 font-medium">{scenarioDenialRate.toFixed(1)}%</span>
                    </div>
                    <input
                      type="range"
                      min="10"
                      max="25"
                      step="0.5"
                      value={scenarioDenialRate}
                      onChange={(e) => setScenarioDenialRate(parseFloat(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>10%</span>
                      <span>Current: 18.5%</span>
                      <span>25%</span>
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between mb-2">
                      <label className="text-sm text-slate-300">Appeal Success</label>
                      <span className="text-sm text-cyan-400 font-medium">{scenarioAppealSuccess}%</span>
                    </div>
                    <input
                      type="range"
                      min="30"
                      max="85"
                      step="1"
                      value={scenarioAppealSuccess}
                      onChange={(e) => setScenarioAppealSuccess(parseInt(e.target.value))}
                      className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>30%</span>
                      <span>Current: 67%</span>
                      <span>85%</span>
                    </div>
                  </div>
                  <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 rounded-xl p-4 border border-cyan-500/20">
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Q1 Impact</span>
                        <span className={`font-bold ${projectedCollection > baselineCollection ? 'text-emerald-400' : 'text-red-400'}`}>
                          {projectedCollection > baselineCollection ? '+' : ''}${(projectedCollection - baselineCollection).toFixed(1)}M
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Annual Impact</span>
                        <span className={`font-bold text-lg ${annualImpact > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {annualImpact > 0 ? '+' : ''}${annualImpact.toFixed(1)}M
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">ROI</span>
                        <span className="font-bold text-cyan-400">{annualImpact > 0 ? Math.round(annualImpact / 0.25) : 0}x</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* High-Risk Claims */}
            <Card className="bg-slate-900/70 border-red-500/20">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg font-semibold text-white">High-Risk Claims</CardTitle>
                  <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full text-xs font-medium animate-pulse">
                    Action Required
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {cfoHighRiskClaims.map((claim) => (
                    <div key={claim.id} className="p-3 bg-red-500/10 rounded-lg border border-red-500/20">
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-medium text-white text-sm">{claim.id}</span>
                          <span className="text-slate-400 text-xs ml-2">{claim.patient}</span>
                        </div>
                        <span className="font-bold text-emerald-400">${claim.amount.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs mb-2">
                        <span className="text-slate-400">{claim.payer}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-red-400 font-medium">{claim.risk}% risk</span>
                          <span className="text-slate-500">({claim.confidence}% conf)</span>
                          <span className="text-amber-400 font-medium">{claim.deadline}</span>
                        </div>
                      </div>
                      <div className="text-xs text-red-300 bg-red-500/10 px-2 py-1 rounded">
                        {claim.trend}
                      </div>
                    </div>
                  ))}
                </div>
                <button className="w-full mt-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm font-medium flex items-center justify-center transition-colors border border-red-500/30">
                  View All 23 Claims <ArrowRight className="w-4 h-4 ml-2" />
                </button>
              </CardContent>
            </Card>
          </div>

          {/* AI Insight Banner */}
          <Card className="bg-gradient-to-r from-cyan-500/20 via-blue-500/20 to-indigo-500/20 border border-cyan-500/30">
            <CardContent className="p-6">
              <div className="flex items-start space-x-4">
                <div className="p-3 bg-cyan-500/20 rounded-xl">
                  <Zap className="w-6 h-6 text-cyan-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-white text-lg mb-2">AI Trend Analysis & Prediction</h3>
                  <p className="text-slate-300 text-sm leading-relaxed">
                    <strong className="text-white">Based on 6-month trend analysis:</strong> Your denial rate has dropped from 22.1% to 18.5% (-3.6%). 
                    AI predicts continued improvement to <strong className="text-emerald-400">16.5% by March</strong> if current interventions continue. 
                    However, <strong className="text-red-400">BCBS Florida is trending negative</strong> (+6% denial rate) — the model detects 
                    a policy change in their prior auth requirements. Recommend scheduling a payer meeting within 2 weeks.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )

  const renderLifecycle = () => (
    <div className="space-y-6">
      {lifecycleLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 animate-spin mr-2" />
          <span>Loading Lifecycle Data...</span>
        </div>
      ) : (
        <>
          {/* Clearinghouse Feed Panel - Two Column Layout */}
          <Card className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 border-slate-800/50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Activity className="h-5 w-5 text-blue-400" />
                    Clearinghouse Feed
                  </CardTitle>
                  <CardDescription className="text-slate-400">
                    {clearinghouseStatus?.mode === 'simulation' ? 'Simulation Mode' : 'Production Mode'} - Real-time 835 ingestion from Availity and Change Healthcare
                  </CardDescription>
                </div>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => simulateBatchTraffic(7)}
                  disabled={pollingAvaility || pollingChange}
                  className="text-xs"
                >
                  Simulate 7 Days
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-6">
                {/* Availity Column */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2.5 h-2.5 rounded-full ${clearinghouseStatus?.availity?.status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`} />
                      <span className="font-semibold text-white">Availity</span>
                      <Badge variant="outline" className="text-xs">{clearinghouseStatus?.availity?.connection_type || 'SFTP'}</Badge>
                    </div>
                    <Button 
                      size="sm" 
                      onClick={pollAvaility}
                      disabled={pollingAvaility}
                      className="text-xs bg-blue-600 hover:bg-blue-700"
                    >
                      {pollingAvaility ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : null}
                      Poll Now
                    </Button>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 space-y-2">
                    <div className="text-xs text-slate-400">Payers:</div>
                    <div className="flex flex-wrap gap-1">
                      {(clearinghouseStatus?.availity?.payers || ['Florida Blue', 'Humana', 'Cigna', 'Medicare']).map((payer: string, i: number) => (
                        <Badge key={i} variant="secondary" className="text-xs bg-blue-900/50 text-blue-300">{payer}</Badge>
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                      <div className="bg-slate-900/50 rounded p-2">
                        <div className="text-slate-400">Files Pending</div>
                        <div className="text-lg font-bold text-white">{clearinghouseStatus?.availity?.files_pending || 0}</div>
                      </div>
                      <div className="bg-slate-900/50 rounded p-2">
                        <div className="text-slate-400">Last Poll</div>
                        <div className="text-sm font-medium text-white">{clearinghouseStatus?.availity?.last_poll ? new Date(clearinghouseStatus.availity.last_poll).toLocaleTimeString() : 'Never'}</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Change Healthcare Column */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-2.5 h-2.5 rounded-full ${clearinghouseStatus?.change_healthcare?.status === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-slate-500'}`} />
                      <span className="font-semibold text-white">Change Healthcare (Optum)</span>
                      <Badge variant="outline" className="text-xs">{clearinghouseStatus?.change_healthcare?.connection_type || 'REST API'}</Badge>
                    </div>
                    <Button 
                      size="sm" 
                      onClick={pollChangeHealthcare}
                      disabled={pollingChange}
                      className="text-xs bg-emerald-600 hover:bg-emerald-700"
                    >
                      {pollingChange ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : null}
                      Poll Now
                    </Button>
                  </div>
                  <div className="bg-slate-800/50 rounded-lg p-3 space-y-2">
                    <div className="text-xs text-slate-400">Payers:</div>
                    <div className="flex flex-wrap gap-1">
                      {(clearinghouseStatus?.change_healthcare?.payers || ['UnitedHealthcare', 'Aetna', 'Anthem', 'Medicaid']).map((payer: string, i: number) => (
                        <Badge key={i} variant="secondary" className="text-xs bg-emerald-900/50 text-emerald-300">{payer}</Badge>
                      ))}
                    </div>
                    <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                      <div className="bg-slate-900/50 rounded p-2">
                        <div className="text-slate-400">Files Pending</div>
                        <div className="text-lg font-bold text-white">{clearinghouseStatus?.change_healthcare?.files_pending || 0}</div>
                      </div>
                      <div className="bg-slate-900/50 rounded p-2">
                        <div className="text-slate-400">Last Poll</div>
                        <div className="text-sm font-medium text-white">{clearinghouseStatus?.change_healthcare?.last_poll ? new Date(clearinghouseStatus.change_healthcare.last_poll).toLocaleTimeString() : 'Never'}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Activity Log */}
              {clearinghouseLogs.length > 0 && (
                <div className="mt-4 border-t border-slate-700/50 pt-4">
                  <div className="text-xs font-medium text-slate-400 mb-2">Recent Activity</div>
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {clearinghouseLogs.map((log, i) => (
                      <div key={i} className="flex items-center justify-between text-xs bg-slate-800/30 rounded px-2 py-1">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                          <Badge variant="outline" className={`text-xs ${log.clearinghouse === 'Availity' ? 'border-blue-500/50 text-blue-400' : 'border-emerald-500/50 text-emerald-400'}`}>
                            {log.clearinghouse}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 text-slate-300">
                          <span>{log.files} files</span>
                          <span>{log.claims} claims</span>
                          <span className="text-red-400">{log.denials} denials</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Manual EDI File Upload */}
              <div className="mt-4 border-t border-slate-700/50 pt-4">
                <div className="text-xs font-medium text-slate-400 mb-2">Manual EDI Upload</div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="border-2 border-dashed border-slate-600 rounded-lg p-4 text-center hover:border-blue-500/50 transition-colors cursor-pointer">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-blue-400" />
                    <div className="text-sm font-medium text-white">Upload 837 File</div>
                    <div className="text-xs text-slate-400">Claim submissions (837P/837I)</div>
                    <input 
                      type="file" 
                      accept=".edi,.txt,.x12"
                      className="hidden"
                      id="upload-837"
                      onChange={async (e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const content = await file.text()
                          const fileType = file.name.toLowerCase().includes('837i') ? '837I' : '837P'
                          try {
                            const res = await fetch(`${API_URL}/api/ingest/837?file_type=${fileType}&file_content=${encodeURIComponent(content)}`, { method: 'POST' })
                            const data = await res.json()
                            setClearinghouseLogs(prev => [{
                              timestamp: new Date().toISOString(),
                              clearinghouse: 'Manual Upload',
                              files: 1,
                              claims: data.total_claims || 0,
                              denials: 0,
                              payers: [fileType]
                            }, ...prev.slice(0, 9)])
                          } catch (err) {
                            console.error('Error uploading 837:', err)
                          }
                        }
                      }}
                    />
                    <label htmlFor="upload-837" className="mt-2 inline-block">
                      <Button size="sm" variant="outline" className="text-xs pointer-events-none">
                        Select File
                      </Button>
                    </label>
                  </div>
                  <div className="border-2 border-dashed border-slate-600 rounded-lg p-4 text-center hover:border-emerald-500/50 transition-colors cursor-pointer">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-emerald-400" />
                    <div className="text-sm font-medium text-white">Upload 835 File</div>
                    <div className="text-xs text-slate-400">Remittance advice (payments/denials)</div>
                    <input 
                      type="file" 
                      accept=".edi,.txt,.x12"
                      className="hidden"
                      id="upload-835"
                      onChange={async (e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          const content = await file.text()
                          try {
                            const res = await fetch(`${API_URL}/api/ingest/835?file_content=${encodeURIComponent(content)}`, { method: 'POST' })
                            const data = await res.json()
                            setClearinghouseLogs(prev => [{
                              timestamp: new Date().toISOString(),
                              clearinghouse: 'Manual Upload',
                              files: 1,
                              claims: data.total_claims || 0,
                              denials: data.denials_found || 0,
                              payers: ['835']
                            }, ...prev.slice(0, 9)])
                            fetchLifecycleData()
                          } catch (err) {
                            console.error('Error uploading 835:', err)
                          }
                        }
                      }}
                    />
                    <label htmlFor="upload-835" className="mt-2 inline-block">
                      <Button size="sm" variant="outline" className="text-xs pointer-events-none">
                        Select File
                      </Button>
                    </label>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Data Sources Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                837/835 Data Sources
              </CardTitle>
              <CardDescription>Clearinghouse and payer feed connections</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                {lifecycleSources.length > 0 ? lifecycleSources.map((source: any, i: number) => (
                  <Card key={i} className="bg-slate-800/50">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">{source.name}</span>
                        <Badge variant={source.status === 'active' ? 'default' : 'secondary'}>
                          {source.status}
                        </Badge>
                      </div>
                      <div className="text-sm text-slate-400">Type: {source.type}</div>
                      <div className="text-sm text-slate-400">Last sync: {source.last_sync}</div>
                      <div className="text-sm text-slate-400">Records: {source.record_count?.toLocaleString()}</div>
                    </CardContent>
                  </Card>
                )) : (
                  <div className="col-span-3 text-center py-8 text-slate-400">
                    <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No data sources configured</p>
                    <p className="text-sm">Connect clearinghouse feeds to enable lifecycle tracking</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* High-Risk Claims */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-500" />
                High-Risk Claims - Churn Prediction
              </CardTitle>
              <CardDescription>Claims with high predicted churn requiring intervention</CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Claim ID</TableHead>
                    <TableHead>Patient</TableHead>
                    <TableHead>Procedure</TableHead>
                    <TableHead>Payer</TableHead>
                    <TableHead>Billed</TableHead>
                    <TableHead>Churn Risk</TableHead>
                    <TableHead>Risk Factors</TableHead>
                    <TableHead>Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {highRiskClaims.length > 0 ? highRiskClaims.map((claim: any, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-sm">{claim.claim_id}</TableCell>
                      <TableCell>{claim.patient_name}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">{claim.procedure_code}</div>
                          <div className="text-xs text-slate-400">{claim.procedure_name}</div>
                        </div>
                      </TableCell>
                      <TableCell>{claim.payer}</TableCell>
                      <TableCell className="font-medium">{formatCurrency(claim.billed_amount)}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress 
                            value={claim.churn_risk * 100} 
                            className={`w-16 h-2 ${claim.churn_risk > 0.6 ? '[&>div]:bg-red-500' : claim.churn_risk > 0.4 ? '[&>div]:bg-orange-500' : '[&>div]:bg-yellow-500'}`} 
                          />
                          <span className={`text-sm font-medium ${claim.churn_risk > 0.6 ? 'text-red-400' : claim.churn_risk > 0.4 ? 'text-orange-400' : 'text-yellow-400'}`}>
                            {(claim.churn_risk * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {claim.risk_factors?.slice(0, 2).map((factor: string, j: number) => (
                            <Badge key={j} variant="outline" className="text-xs">{factor}</Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Button size="sm" variant="outline" className="text-xs">
                          {claim.recommended_action || 'Review'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  )) : (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-slate-400">
                        No high-risk claims detected
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Reconciliation Summary */}
          {reconciliationData && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  837/835 Reconciliation
                </CardTitle>
                <CardDescription>Claim submission to payment reconciliation</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                    <div className="text-2xl font-bold text-blue-400">{reconciliationData.submitted_837?.toLocaleString() || 0}</div>
                    <div className="text-sm text-slate-400">837 Submitted</div>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                    <div className="text-2xl font-bold text-green-400">{reconciliationData.matched_835?.toLocaleString() || 0}</div>
                    <div className="text-sm text-slate-400">835 Matched</div>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                    <div className="text-2xl font-bold text-orange-400">{reconciliationData.pending?.toLocaleString() || 0}</div>
                    <div className="text-sm text-slate-400">Pending Response</div>
                  </div>
                  <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                    <div className="text-2xl font-bold text-red-400">{reconciliationData.variances?.toLocaleString() || 0}</div>
                    <div className="text-sm text-slate-400">Variances</div>
                  </div>
                </div>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={reconciliationData.timeline || []}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line type="monotone" dataKey="submitted" stroke="#3b82f6" name="837 Submitted" />
                      <Line type="monotone" dataKey="paid" stroke="#22c55e" name="835 Paid" />
                      <Line type="monotone" dataKey="denied" stroke="#ef4444" name="835 Denied" />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
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
                          <Badge className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs font-semibold px-3 py-1">
                            <Brain className="h-3 w-3 mr-1 inline" />
                            42 AI Agents
                          </Badge>
                          <Badge className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white text-xs font-semibold px-3 py-1">
                            <Building2 className="h-3 w-3 mr-1 inline" />
                            9 Payers
                          </Badge>
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
                      {PERSONA_CONFIG[persona].visibleTabs.includes('cfo') && (
                        <TabsTrigger value="cfo" className="flex items-center gap-2">
                          <DollarSign className="h-4 w-4" />
                          Financial Intelligence
                        </TabsTrigger>
                      )}
                      {PERSONA_CONFIG[persona].visibleTabs.includes('dashboard') && (
                        <TabsTrigger value="dashboard" className="flex items-center gap-2">
                          <Activity className="h-4 w-4" />
                          Denial Operations
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
                      {PERSONA_CONFIG[persona].visibleTabs.includes('lifecycle') && (
                        <TabsTrigger value="lifecycle" className="flex items-center gap-2">
                          <FileText className="h-4 w-4" />
                          837/835 Lifecycle
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
                      {PERSONA_CONFIG[persona].visibleTabs.includes('policy') && (
                        <TabsTrigger value="policy" className="flex items-center gap-2">
                          <Search className="h-4 w-4" />
                          Policy Search
                        </TabsTrigger>
                      )}
                    </TabsList>

          <TabsContent value="cfo">{renderCFODashboard()}</TabsContent>
          <TabsContent value="dashboard">{renderDashboard()}</TabsContent>
          <TabsContent value="pa">{renderPriorAuths()}</TabsContent>
          <TabsContent value="denials">{renderDenials()}</TabsContent>
          <TabsContent value="ai">{renderAI()}</TabsContent>
          <TabsContent value="lifecycle">{renderLifecycle()}</TabsContent>
          <TabsContent value="learning">{renderLearning()}</TabsContent>
          <TabsContent value="payer">{renderPayer()}</TabsContent>
          <TabsContent value="policy">{renderPolicySearch()}</TabsContent>
        </Tabs>
      </main>
    </div>
  )
}

export default App
