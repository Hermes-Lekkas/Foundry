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
  InformationCircleIcon
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
  
  // BYOK State
  const [activeTab, setActiveTab] = useState<'models' | 'byok'>('models')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedTeacherModel, setSelectedTeacherModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [hfToken, setHfToken] = useState('')
  const [studentModel, setStudentModel] = useState('')

  useEffect(() => {
    loadModels()
    loadFilters()
    loadKeys()
    loadProviders()
  }, [])

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
    setDownloadingId(modelId)
    try {
      const result = await api.downloadModel(modelId) as { message: string }
      toast.success(result.message)
    } catch (err) {
      toast.error(`Download failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setDownloadingId(null)
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
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'models'
                ? 'bg-foundry-primary text-white'
                : 'bg-glass-100 text-gray-400 hover:text-white'
            }`}
          >
            <CloudArrowDownIcon className="w-4 h-4 inline mr-2" />
            Download Models
          </button>
          <button
            onClick={() => setActiveTab('byok')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === 'byok'
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
                accent={model.is_downloaded ? 'success' : 'accent'}
                className="relative group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-white">{model.name}</h3>
                    <p className="text-xs text-gray-500 font-mono mt-1">{model.id}</p>
                  </div>
                  {model.is_downloaded && (
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
                
                <button
                  onClick={() => handleDownload(model.id)}
                  disabled={downloadingId === model.id || model.is_downloaded}
                  className={`w-full py-2 rounded-lg font-medium text-sm transition-colors ${
                    model.is_downloaded
                      ? 'bg-foundry-success/20 text-foundry-success cursor-default'
                      : downloadingId === model.id
                      ? 'bg-foundry-primary/50 text-white cursor-wait'
                      : 'bg-foundry-primary hover:bg-foundry-primary/80 text-white'
                  }`}
                >
                  {model.is_downloaded
                    ? 'Downloaded'
                    : downloadingId === model.id
                    ? 'Queuing...'
                    : 'Download'}
                </button>
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
                          className={`p-3 rounded-lg cursor-pointer transition-colors ${
                            selectedTeacherModel === model.id
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
                    className={`w-full py-2 rounded-lg text-white font-medium transition-colors ${
                      selectedTeacherModel
                        ? 'bg-foundry-primary hover:bg-foundry-primary/80'
                        : 'bg-gray-600 cursor-not-allowed'
                    }`}
                  >
                    {selectedTeacherModel 
                      ? `Save: ${selectedProviderInfo.models.find(m => m.id === selectedTeacherModel)?.name || selectedTeacherModel}`
                      : 'Select a model above'}
                  </button>
                </>
              )}
            </div>

            {/* API Key Status */}
            <div className="mt-6 pt-6 border-t border-glass-200">
              <h4 className="text-sm font-medium text-gray-400 mb-3">Configured Keys</h4>
              <div className="space-y-2">
                {keyStatus.map((key) => (
                  <div
                    key={key.provider as string}
                    className="flex items-center justify-between py-2 px-3 bg-glass-50 rounded-lg"
                  >
                    <span className="text-sm text-white capitalize">{key.provider as string}</span>
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        key.is_set
                          ? 'bg-foundry-success/20 text-foundry-success'
                          : 'bg-foundry-error/20 text-foundry-error'
                      }`}
                    >
                      {key.is_set ? (key.masked_key as string) || 'Configured' : 'Not Set'}
                    </span>
                  </div>
                ))}
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
