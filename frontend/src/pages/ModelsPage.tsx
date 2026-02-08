// The Foundry - Open Core LLM Training Ecosystem
// Copyright (c) 2026 Hermes Lekkas
//
// This file is part of the open-core release (MIT License).
// See LICENSE file for full terms.

import { useEffect, useState } from 'react'
import {
  CloudArrowDownIcon,
  CheckCircleIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  CpuChipIcon,
  KeyIcon,
  ServerIcon,
  BeakerIcon,
  InformationCircleIcon,
  ArrowPathIcon,
  BoltIcon
} from '@heroicons/react/24/outline'
import GlassCard from '../components/GlassCard'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'

interface ModelInfo {
  id: string
  name: string
  description: string
  size: string
  params: string
  vram_required_gb: number
  provider: string
  tags: string[]
  is_downloaded: boolean
}

interface ProviderInfo {
  id: string
  name: string
  description: string
  requires_api_key: boolean
  models: { id: string; name: string; description: string }[]
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [sizes, setSizes] = useState<{ value: string; label: string; vram_range: string }[]>([])
  const [tags, setTags] = useState<string[]>([])
  const [keyStatus, setKeyStatus] = useState<Record<string, unknown>[]>([])

  const [searchQuery, setSearchQuery] = useState('')
  const [selectedSize, setSelectedSize] = useState('')
  const [selectedTag, setSelectedTag] = useState('')
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [downloadedModels, setDownloadedModels] = useState<Set<string>>(new Set())
  const [downloadingProgress, setDownloadingProgress] = useState<Record<string, string>>({})

  // BYOK State
  const [activeTab, setActiveTab] = useState<'models' | 'byok'>('models')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedTeacherModel, setSelectedTeacherModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [hfToken, setHfToken] = useState('')
  const [studentModel, setStudentModel] = useState('')

  useEffect(() => {
    loadModels()
    loadDownloadedModels()
    loadFilters()
    loadKeys()
    loadProviders()
  }, [])

  // Reload keys when switching to BYOK tab
  useEffect(() => {
    if (activeTab === 'byok') {
      loadKeys()
      loadCurrentConfigs()
    }
  }, [activeTab])

  const loadCurrentConfigs = async () => {
    try {
      const [teacher, student] = await Promise.all([
        api.getCurrentTeacher(),
        api.getCurrentStudent(),
      ])

      // Set teacher config
      const teacherData = teacher as { provider: string; model: string }
      if (teacherData.provider) {
        setSelectedProvider(teacherData.provider)
        setSelectedTeacherModel(teacherData.model)
      }

      // Set student config
      const studentData = student as { model_id: string }
      if (studentData.model_id) {
        setStudentModel(studentData.model_id)
      }
    } catch {
      // Silent fail - configs may not be set yet
    }
  }

  const loadModels = async () => {
    try {
      const params: { size?: string; tag?: string; search?: string } = {}
      if (selectedSize) params.size = selectedSize
      if (selectedTag) params.tag = selectedTag
      if (searchQuery) params.search = searchQuery

      const data = await api.getModelCatalog(params)
      setModels(data as ModelInfo[])
    } catch {
      toast.error('Failed to load model catalog')
    }
  }

  const loadDownloadedModels = async () => {
    try {
      const data = await api.getDownloadedModels()
      const downloadedIds = new Set((data as ModelInfo[]).map(m => m.id))
      setDownloadedModels(downloadedIds)
    } catch {
      // Silent fail
    }
  }

  const loadFilters = async () => {
    try {
      const [sizesData, tagsData] = await Promise.all([
        api.getModelSizes(),
        api.getModelTags(),
      ])
      setSizes(sizesData as { value: string; label: string; vram_range: string }[])
      setTags(tagsData as string[])
    } catch {
      // Silent fail for filters
    }
  }

  const loadKeys = async () => {
    try {
      const data = await api.getKeyStatus()
      setKeyStatus(data)
    } catch {
      // Silent fail
    }
  }

  const loadProviders = async () => {
    try {
      const data = await api.getTeacherProviders()
      setProviders(data as ProviderInfo[])
    } catch {
      // Silent fail
    }
  }

  const handleDownload = async (modelId: string) => {
    const model = models.find(m => m.id === modelId)
    if (!model) return

    setDownloadingId(modelId)
    setDownloadingProgress(prev => ({ ...prev, [modelId]: 'Starting download...' }))
    
    try {
      const result = await api.downloadModel(modelId) as { job_id: string; message: string }
      toast.success(result.message)
      
      // Poll for download completion via WebSocket or polling
      // For now, simulate polling with setTimeout
      setDownloadingProgress(prev => ({ ...prev, [modelId]: 'Downloading from HuggingFace...' }))
      
      // Poll every 5 seconds for download status
      const pollInterval = setInterval(async () => {
        try {
          const downloaded = await api.getDownloadedModels()
          const downloadedIds = new Set((downloaded as ModelInfo[]).map(m => m.id))
          
          if (downloadedIds.has(modelId)) {
            clearInterval(pollInterval)
            setDownloadedModels(downloadedIds)
            setDownloadingId(null)
            setDownloadingProgress(prev => {
              const newProgress = { ...prev }
              delete newProgress[modelId]
              return newProgress
            })
            toast.success(`${model.name} downloaded successfully!`)
          }
        } catch {
          // Continue polling
        }
      }, 5000)
      
      // Stop polling after 30 minutes (max download time)
      setTimeout(() => {
        clearInterval(pollInterval)
        setDownloadingId(null)
      }, 30 * 60 * 1000)
      
    } catch (err) {
      toast.error(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
      setDownloadingId(null)
      setDownloadingProgress(prev => {
        const newProgress = { ...prev }
        delete newProgress[modelId]
        return newProgress
      })
    }
  }

  const handleSetAsStudent = async (modelId: string) => {
    try {
      await api.setModelAsStudent(modelId)
      toast.success('Model set as student (training target)')
      setStudentModel(modelId)
      loadKeys()
    } catch (err) {
      toast.error(`Failed to set as student: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleSetAsTeacher = async (modelId: string) => {
    try {
      await api.setModelAsTeacher(modelId)
      toast.success('Model set as local teacher')
      setSelectedProvider('local')
      setSelectedTeacherModel(modelId)
      loadKeys()
    } catch (err) {
      toast.error(`Failed to set as teacher: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleConfigureTeacher = async () => {
    if (!selectedProvider || !selectedTeacherModel) {
      toast.error('Please select a provider and model')
      return
    }

    try {
      await api.configureTeacher({
        provider: selectedProvider,
        model: selectedTeacherModel,
        api_key: apiKey || undefined,
      })
      toast.success('Teacher configuration saved')
      loadKeys()
    } catch (err) {
      toast.error(`Failed to configure teacher: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const [isTestingTeacher, setIsTestingTeacher] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null)

  const handleTestTeacher = async () => {
    if (!selectedProvider || !selectedTeacherModel) {
      toast.error('Please select a provider and model first')
      return
    }

    setIsTestingTeacher(true)
    setTestResult(null)

    try {
      const result = await api.testTeacher({
        provider: selectedProvider,
        model: selectedTeacherModel,
        api_key: apiKey || undefined,
      }) as { status: string; message: string; response_preview?: string }

      setTestResult(result)

      if (result.status === 'success') {
        toast.success(`Teacher test successful! Response: "${result.response_preview}"`)
      } else {
        toast.error(`Teacher test failed: ${result.message}`)
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error'
      setTestResult({ status: 'error', message: errorMsg })
      toast.error(`Test failed: ${errorMsg}`)
    } finally {
      setIsTestingTeacher(false)
    }
  }

  const handleConfigureStudent = async () => {
    if (!studentModel) {
      toast.error('Please select a student model')
      return
    }

    try {
      await api.configureStudent({
        model_id: studentModel,
        use_local: true,
      })
      toast.success('Student configuration saved')
      loadKeys() // Refresh key status
    } catch (err) {
      toast.error(`Failed to configure student: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const handleSaveHFToken = async () => {
    if (!hfToken) {
      toast.error('Please enter a HuggingFace token')
      return
    }

    try {
      await api.setHuggingFaceToken(hfToken)
      toast.success('HuggingFace token saved')
      setHfToken('')
      loadKeys()
    } catch (err) {
      toast.error(`Failed to save token: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  const selectedProviderInfo = providers.find(p => p.id === selectedProvider)

  return (
    <div className="space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Models & BYOK</h1>
          <p className="text-gray-500 text-sm mt-1">
            Download LLMs and configure your Teacher/Student models
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('models')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'models'
                ? 'bg-foundry-primary text-white'
                : 'bg-glass-100 text-gray-400 hover:text-white'
              }`}
          >
            <CloudArrowDownIcon className="w-4 h-4 inline mr-2" />
            Download Models
          </button>
          <button
            onClick={() => setActiveTab('byok')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === 'byok'
                ? 'bg-foundry-primary text-white'
                : 'bg-glass-100 text-gray-400 hover:text-white'
              }`}
          >
            <KeyIcon className="w-4 h-4 inline mr-2" />
            BYOK Config
          </button>
        </div>
      </div>

      {activeTab === 'models' ? (
        <>
          {/* Filters */}
          <GlassCard title="Filter Models" accent="primary">
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search models..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white placeholder-gray-500 focus:outline-none focus:border-foundry-primary/50"
                  />
                </div>
              </div>
              <select
                value={selectedSize}
                onChange={(e) => setSelectedSize(e.target.value)}
                className="px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white focus:outline-none focus:border-foundry-primary/50"
              >
                <option value="">All Sizes</option>
                {sizes.map((size) => (
                  <option key={size.value} value={size.value}>
                    {size.label}
                  </option>
                ))}
              </select>
              <select
                value={selectedTag}
                onChange={(e) => setSelectedTag(e.target.value)}
                className="px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white focus:outline-none focus:border-foundry-primary/50"
              >
                <option value="">All Tags</option>
                {tags.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
              </select>
              <button
                onClick={loadModels}
                className="px-4 py-2 bg-foundry-primary hover:bg-foundry-primary/80 rounded-lg text-white font-medium transition-colors"
              >
                <FunnelIcon className="w-4 h-4 inline mr-2" />
                Apply
              </button>
            </div>
          </GlassCard>

          {/* Model Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {models.map((model) => (
              <GlassCard
                key={model.id}
                accent={downloadedModels.has(model.id) ? 'success' : 'accent'}
                className="relative group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white">{model.name}</h3>
                    <p className="text-xs text-gray-500 font-mono mt-1">{model.id}</p>
                  </div>
                  {downloadedModels.has(model.id) && (
                    <CheckCircleIcon className="w-5 h-5 text-foundry-success" />
                  )}
                </div>

                <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                  {model.description}
                </p>

                <div className="flex flex-wrap gap-2 mb-4">
                  <span className="px-2 py-1 bg-foundry-primary/20 text-foundry-primary text-xs rounded-full">
                    {model.params}
                  </span>
                  <span className="px-2 py-1 bg-glass-100 text-gray-400 text-xs rounded-full flex items-center gap-1">
                    <CpuChipIcon className="w-3 h-3" />
                    {model.vram_required_gb} GB VRAM
                  </span>
                  {model.tags.slice(0, 2).map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-glass-100 text-gray-400 text-xs rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* Download Progress */}
                {downloadingId === model.id && downloadingProgress[model.id] && (
                  <div className="mb-3 p-2 bg-foundry-primary/10 rounded-lg">
                    <div className="flex items-center gap-2">
                      <ArrowPathIcon className="w-4 h-4 text-foundry-primary animate-spin" />
                      <span className="text-xs text-foundry-primary">
                        {downloadingProgress[model.id]}
                      </span>
                    </div>
                  </div>
                )}

                {/* Download or Set Buttons */}
                {downloadedModels.has(model.id) ? (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-foundry-success text-sm">
                      <CheckCircleIcon className="w-4 h-4" />
                      <span>Downloaded</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => handleSetAsStudent(model.id)}
                        className="py-2 bg-foundry-accent hover:bg-foundry-accent/80 rounded-lg text-white text-xs font-medium transition-colors"
                      >
                        Set as Student
                      </button>
                      <button
                        onClick={() => handleSetAsTeacher(model.id)}
                        className="py-2 bg-foundry-primary hover:bg-foundry-primary/80 rounded-lg text-white text-xs font-medium transition-colors"
                      >
                        Set as Teacher
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    onClick={() => handleDownload(model.id)}
                    disabled={downloadingId === model.id}
                    className={`w-full py-2 rounded-lg font-medium text-sm transition-colors ${
                      downloadingId === model.id
                        ? 'bg-foundry-primary/50 text-white cursor-wait'
                        : 'bg-foundry-primary hover:bg-foundry-primary/80 text-white'
                    }`}
                  >
                    {downloadingId === model.id ? (
                      <span className="flex items-center justify-center gap-2">
                        <ArrowPathIcon className="w-4 h-4 animate-spin" />
                        Downloading...
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <CloudArrowDownIcon className="w-4 h-4" />
                        Download
                      </span>
                    )}
                  </button>
                )}
              </GlassCard>
            ))}
          </div>

          {models.length === 0 && (
            <div className="text-center py-12">
              <p className="text-gray-500">No models found matching your criteria.</p>
            </div>
          )}
        </>
      ) : (
        /* BYOK Configuration */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Teacher Configuration */}
          <GlassCard title="Teacher Model (BYOK)" subtitle="The AI that generates training data" accent="primary">
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  <ServerIcon className="w-4 h-4 inline mr-1" />
                  Provider
                </label>
                <select
                  value={selectedProvider}
                  onChange={(e) => {
                    setSelectedProvider(e.target.value)
                    setSelectedTeacherModel('')
                    setApiKey('')
                  }}
                  className="w-full px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white focus:outline-none focus:border-foundry-primary/50"
                >
                  <option value="">Select a provider...</option>
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.name}
                    </option>
                  ))}
                </select>
                {!selectedProviderInfo && providers.length > 0 && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-gray-400 mb-3">All Available Providers</h4>
                    <div className="space-y-3">
                      {providers.map((provider) => (
                        <div
                          key={provider.id}
                          className="p-3 bg-glass-50 rounded-lg border border-glass-200"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-white">{provider.name}</span>
                            {provider.requires_api_key ? (
                              <span className="text-xs px-2 py-0.5 bg-foundry-warning/20 text-foundry-warning rounded-full">
                                API Key Required
                              </span>
                            ) : (
                              <span className="text-xs px-2 py-0.5 bg-foundry-success/20 text-foundry-success rounded-full">
                                Free / Local
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mb-2">{provider.description}</p>
                          <div className="text-xs text-gray-500">
                            <span className="font-medium">Models:</span>{' '}
                            {provider.models.map(m => m.name).join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedProviderInfo && (
                  <p className="text-xs text-gray-500 mt-2">{selectedProviderInfo.description}</p>
                )}
              </div>

              {selectedProviderInfo && (
                <>
                  {/* Available Models for this Provider */}
                  <div>
                    <label className="block text-sm text-gray-400 mb-2">
                      <BeakerIcon className="w-4 h-4 inline mr-1" />
                      Available Models ({selectedProviderInfo.models.length})
                    </label>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {selectedProviderInfo.models.map((model) => (
                        <div
                          key={model.id}
                          onClick={() => setSelectedTeacherModel(model.id)}
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${selectedTeacherModel === model.id
                              ? 'bg-foundry-primary/20 border border-foundry-primary/50'
                              : 'bg-glass-50 border border-glass-200 hover:bg-glass-100'
                            }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-white">{model.name}</span>
                            {selectedTeacherModel === model.id && (
                              <CheckCircleIcon className="w-4 h-4 text-foundry-primary" />
                            )}
                          </div>
                          <p className="text-xs text-gray-400 mt-1">{model.description}</p>
                          <p className="text-xs text-gray-500 font-mono mt-1">{model.id}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {selectedProviderInfo.requires_api_key && (
                    <div>
                      <label className="block text-sm text-gray-400 mb-2">
                        <KeyIcon className="w-4 h-4 inline mr-1" />
                        API Key
                      </label>
                      <input
                        type="password"
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={selectedProviderInfo.id === 'anthropic' ? 'sk-ant-...' : selectedProviderInfo.id === 'openai' ? 'sk-...' : 'API key...'}
                        className="w-full px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white placeholder-gray-500 focus:outline-none focus:border-foundry-primary/50"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Your API key is stored securely in .env and never shared.
                      </p>
                    </div>
                  )}

                  <button
                    onClick={handleConfigureTeacher}
                    disabled={!selectedTeacherModel}
                    className={`w-full py-2 rounded-lg text-white font-medium transition-colors ${selectedTeacherModel
                        ? 'bg-foundry-primary hover:bg-foundry-primary/80'
                        : 'bg-gray-600 cursor-not-allowed'
                      }`}
                  >
                    {selectedTeacherModel
                      ? `Save: ${selectedProviderInfo.models.find(m => m.id === selectedTeacherModel)?.name || selectedTeacherModel}`
                      : 'Select a model above'}
                  </button>

                  {/* Test Connection Button */}
                  {selectedTeacherModel && (
                    <button
                      onClick={handleTestTeacher}
                      disabled={isTestingTeacher}
                      className={`w-full py-2 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${isTestingTeacher
                          ? 'bg-foundry-accent/50 text-white cursor-wait'
                          : 'bg-foundry-accent hover:bg-foundry-accent/80 text-white'
                        }`}
                    >
                      {isTestingTeacher ? (
                        <>
                          <ArrowPathIcon className="w-4 h-4 animate-spin" />
                          Testing connection...
                        </>
                      ) : (
                        <>
                          <BoltIcon className="w-4 h-4" />
                          Test Connection
                        </>
                      )}
                    </button>
                  )}

                  {/* Test Result */}
                  {testResult && (
                    <div className={`p-3 rounded-lg text-sm ${testResult.status === 'success'
                        ? 'bg-foundry-success/10 border border-foundry-success/30 text-foundry-success'
                        : 'bg-foundry-error/10 border border-foundry-error/30 text-foundry-error'
                      }`}>
                      <div className="flex items-center gap-2 mb-1">
                        {testResult.status === 'success' ? (
                          <CheckCircleIcon className="w-4 h-4" />
                        ) : (
                          <InformationCircleIcon className="w-4 h-4" />
                        )}
                        <span className="font-medium">
                          {testResult.status === 'success' ? 'Connection Successful' : 'Connection Failed'}
                        </span>
                      </div>
                      <p className="text-xs opacity-90">{testResult.message}</p>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* API Key Status */}
            <div className="mt-6 pt-6 border-t border-glass-200">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-400 flex items-center gap-2">
                  <KeyIcon className="w-4 h-4" />
                  Configured Keys & Status
                </h4>
                <button
                  onClick={loadKeys}
                  className="text-xs text-foundry-primary hover:text-foundry-primary/80 flex items-center gap-1 transition-colors"
                  title="Refresh key status"
                >
                  <ArrowPathIcon className="w-3 h-3" />
                  Refresh
                </button>
              </div>
              <div className="space-y-2">
                {keyStatus.length === 0 ? (
                  <p className="text-sm text-gray-500">Loading key status...</p>
                ) : (
                  keyStatus.map((key) => (
                    <div
                      key={key.provider as string}
                      className="flex items-center justify-between py-2.5 px-3 bg-glass-50 rounded-lg border border-glass-100"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-white capitalize font-medium">
                          {key.provider as string}
                        </span>
                        {(key.provider as string) === 'anthropic' && (
                          <span className="text-xs text-gray-500">Teacher</span>
                        )}
                        {(key.provider as string) === 'openai' && (
                          <span className="text-xs text-gray-500">Teacher</span>
                        )}
                        {(key.provider as string) === 'huggingface' && (
                          <span className="text-xs text-gray-500">Models</span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        {key.is_set ? (
                          <>
                            <CheckCircleIcon className="w-4 h-4 text-foundry-success" />
                            <span className="text-xs px-2 py-1 rounded-full bg-foundry-success/20 text-foundry-success font-mono">
                              {(key.masked_key as string) || 'Configured'}
                            </span>
                          </>
                        ) : (
                          <>
                            <InformationCircleIcon className="w-4 h-4 text-foundry-error" />
                            <span className="text-xs px-2 py-1 rounded-full bg-foundry-error/20 text-foundry-error">
                              Not Set
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Current Configuration Summary */}
              <div className="mt-4 p-3 bg-foundry-primary/5 rounded-lg border border-foundry-primary/20">
                <h5 className="text-xs font-medium text-foundry-primary mb-2">Active Configuration</h5>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Teacher Provider:</span>
                    <span className="text-white capitalize">
                      {providers.find(p => p.id === selectedProvider)?.name || 'Not configured'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Teacher Model:</span>
                    <span className="text-white">
                      {selectedProviderInfo?.models.find(m => m.id === selectedTeacherModel)?.name || 'Not selected'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Student Model:</span>
                    <span className="text-white">
                      {models.find(m => m.id === studentModel)?.name || 'Not selected'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </GlassCard>

          {/* Student Configuration */}
          <div className="space-y-6">
            <GlassCard title="Student Model" subtitle="The model you want to train" accent="accent">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    <CpuChipIcon className="w-4 h-4 inline mr-1" />
                    Base Model
                  </label>
                  <select
                    value={studentModel}
                    onChange={(e) => setStudentModel(e.target.value)}
                    className="w-full px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white focus:outline-none focus:border-foundry-primary/50"
                  >
                    <option value="">Select a base model...</option>
                    {models
                      .filter((m) => ['tiny', 'small', 'medium'].includes(m.size))
                      .map((model) => (
                        <option key={model.id} value={model.id}>
                          {model.name} ({model.params})
                        </option>
                      ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-2">
                    Choose a smaller model for faster training. Recommended: 0.5B - 3B parameters.
                  </p>
                </div>

                <button
                  onClick={handleConfigureStudent}
                  className="w-full py-2 bg-foundry-accent hover:bg-foundry-accent/80 rounded-lg text-white font-medium transition-colors"
                >
                  Save Student Configuration
                </button>
              </div>
            </GlassCard>

            <GlassCard title="HuggingFace Token" subtitle="For gated/private models" accent="warning">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    <KeyIcon className="w-4 h-4 inline mr-1" />
                    Access Token
                  </label>
                  <input
                    type="password"
                    value={hfToken}
                    onChange={(e) => setHfToken(e.target.value)}
                    placeholder="hf_..."
                    className="w-full px-4 py-2 bg-foundry-surface/50 rounded-lg border border-glass-200 text-white placeholder-gray-500 focus:outline-none focus:border-foundry-primary/50"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Required for some models like Llama. Get yours at{' '}
                    <a
                      href="https://huggingface.co/settings/tokens"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-foundry-primary hover:underline"
                    >
                      huggingface.co/settings/tokens
                    </a>
                  </p>
                </div>

                <button
                  onClick={handleSaveHFToken}
                  className="w-full py-2 bg-foundry-warning hover:bg-foundry-warning/80 rounded-lg text-white font-medium transition-colors"
                >
                  Save HuggingFace Token
                </button>
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </div>
  )
}
