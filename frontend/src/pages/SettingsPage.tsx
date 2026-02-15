/**
 * Settings page - configure AI, teacher profile, and app settings
 */

import React, { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNotification } from "@/contexts";
import { settingsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Save, User, Brain, Search, Eye, EyeOff } from "lucide-react";

export function SettingsPage() {
  const { show: showNotification } = useNotification();
  const [showApiKey, setShowApiKey] = useState(false);
  const [availableModels, setAvailableModels] = useState<(string | { name: string; vendor: string; id: string })[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  // Teacher profile state
  const [profile, setProfile] = useState({
    name: "",
    email: "",
    avatar_url: "",
    bio: "",
  });

  // AI config state
  const [aiConfig, setAiConfig] = useState({
    provider: "openai",
    model: "gpt-4",
    api_key: "",
    base_url: "",
    temperature: 0.7,
    max_tokens: 4096,
  });

  // Search engine state
  const [searchEngine, setSearchEngine] = useState("duckduckgo");

  // Last-saved values: save buttons enabled only when form is dirty
  const [lastSavedProfile, setLastSavedProfile] = useState<Partial<typeof profile> | null>(null);
  const [lastSavedAiConfig, setLastSavedAiConfig] = useState<{
    provider: string;
    model: string;
    base_url: string;
    temperature: number;
    max_tokens: number;
  } | null>(null);
  const [lastSavedSearchEngine, setLastSavedSearchEngine] = useState<string | null>(null);

  // Load data: only two endpoints - settings (AI + search_engine) and teacher-profile
  const { data: profileData, isLoading: profileLoading } = useQuery({
    queryKey: ["teacher-profile"],
    queryFn: settingsApi.getTeacherProfile,
    refetchOnMount: "always",
    staleTime: 0,
  });

  const { data: settingsData, isLoading: settingsLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: settingsApi.getSettings,
    refetchOnMount: "always",
    staleTime: 0,
  });

  // Mutations: no invalidate on success; update lastSaved so save button goes grey again
  const profileMutation = useMutation({
    mutationFn: settingsApi.updateTeacherProfile,
    onSuccess: (_data, variables) => {
      setLastSavedProfile(variables);
      showNotification({ type: "success", message: "Profile saved successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to save profile." });
    },
  });

  const aiConfigMutation = useMutation({
    mutationFn: (payload: {
      provider?: string;
      model?: string;
      base_url?: string;
      api_key?: string;
      temperature?: number;
      max_tokens?: number;
    }) => settingsApi.updateAIProvider(payload),
    onSuccess: (_data, _variables) => {
      setLastSavedAiConfig({
        provider: aiConfig.provider,
        model: aiConfig.model,
        base_url: aiConfig.base_url,
        temperature: aiConfig.temperature,
        max_tokens: aiConfig.max_tokens,
      });
      setAiConfig((c) => ({ ...c, api_key: "" }));
      showNotification({ type: "success", message: "AI config saved successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to save AI config." });
    },
  });

  const searchEngineMutation = useMutation({
    mutationFn: (engine: string) => settingsApi.updateSearchEngine(engine),
    onSuccess: (_data, variables) => {
      setLastSavedSearchEngine(variables);
      showNotification({ type: "success", message: "Search settings saved successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to save search settings." });
    },
  });

  React.useEffect(() => {
    if (profileData) {
      const p = {
        name: profileData.name || "",
        email: profileData.email || "",
        avatar_url: profileData.avatar_url || "",
        bio: profileData.bio || "",
      };
      setProfile(p);
      setLastSavedProfile(p);
    }
  }, [profileData]);

  React.useEffect(() => {
    if (settingsData) {
      const d = settingsData as unknown as Record<string, unknown>;
      const provider = ((d.provider ?? d.default_provider) as string) || "openai";
      const model = ((d.model ?? d.default_model) as string) || "gpt-4";
      const base_url = ((d.base_url ?? d.api_base_url) as string) || "";
      const temperature = (d.temperature as number) ?? 0.7;
      const max_tokens = (d.max_tokens as number) ?? 4096;
      const search_engine = (d.search_engine as string) || "duckduckgo";

      setAiConfig({
        provider,
        model,
        api_key: "",
        base_url,
        temperature,
        max_tokens,
      });
      setSearchEngine(search_engine);
      setLastSavedAiConfig({ provider, model, base_url, temperature, max_tokens });
      setLastSavedSearchEngine(search_engine);
    }
  }, [settingsData]);

  const isProfileDirty =
    lastSavedProfile == null ||
    profile.name !== lastSavedProfile.name ||
    profile.email !== lastSavedProfile.email ||
    profile.avatar_url !== lastSavedProfile.avatar_url ||
    profile.bio !== lastSavedProfile.bio;

  const isAiConfigDirty =
    lastSavedAiConfig == null ||
    aiConfig.provider !== lastSavedAiConfig.provider ||
    aiConfig.model !== lastSavedAiConfig.model ||
    aiConfig.base_url !== lastSavedAiConfig.base_url ||
    aiConfig.temperature !== lastSavedAiConfig.temperature ||
    aiConfig.max_tokens !== lastSavedAiConfig.max_tokens ||
    aiConfig.api_key !== "";

  const isSearchEngineDirty = lastSavedSearchEngine == null || searchEngine !== lastSavedSearchEngine;

  // Get Models button: (a) Copilot -> enable if base_url not empty; (b) non-Copilot -> enable if base_url and api_key both not empty; (c) saved config for current provider -> enable if base_url not empty
  const settings = settingsData as unknown as Record<string, unknown> | undefined;
  const savedProvider = settings && (settings.default_provider ?? settings.provider);
  const isSavedConfigForProvider = !!settings && String(savedProvider) === aiConfig.provider;
  const getModelsDisabled =
    isLoadingModels ||
    !aiConfig.base_url?.trim() ||
    (aiConfig.provider !== "copilot" && !isSavedConfigForProvider && !aiConfig.api_key?.trim());

  const handleSaveProfile = () => {
    profileMutation.mutate(profile);
  };

  const handleSaveAIConfig = () => {
    aiConfigMutation.mutate({
      provider: aiConfig.provider,
      model: aiConfig.model,
      base_url: aiConfig.base_url || undefined,
      api_key: aiConfig.api_key || undefined,
      temperature: aiConfig.temperature,
      max_tokens: aiConfig.max_tokens,
    });
  };

  const handleSaveSearchEngine = () => {
    searchEngineMutation.mutate(searchEngine);
  };

  const handleGetModels = async () => {
    const needBaseUrl = aiConfig.provider !== "copilot";
    if (needBaseUrl && !aiConfig.base_url?.trim()) {
      showNotification({ type: "warning", message: "Please enter a Base URL first." });
      return;
    }
    setIsLoadingModels(true);
    try {
      const result = await settingsApi.getModels(aiConfig.provider, aiConfig.base_url, aiConfig.api_key || undefined);
      setAvailableModels(result.models);
      if (result.error) {
        showNotification({ type: "error", message: result.error });
      } else if (result.models.length > 0) {
        showNotification({
          type: "success",
          message: `Loaded ${result.models.length} model(s).`,
        });
      }
    } catch (error) {
      console.error("Failed to fetch models:", error);
      showNotification({
        type: "error",
        message: "Failed to fetch models. Please check your settings.",
      });
    } finally {
      setIsLoadingModels(false);
    }
  };

  if (profileLoading || settingsLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <p className="text-gray-500">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Teacher Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Teacher Profile
          </CardTitle>
          <CardDescription>Your profile information for personalized greetings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-6">
            <Avatar className="h-20 w-20">
              <AvatarImage src={profile.avatar_url} />
              <AvatarFallback className="text-2xl">{profile.name?.charAt(0) || "T"}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <Label htmlFor="avatar_url">Avatar URL</Label>
              <Input
                id="avatar_url"
                value={profile.avatar_url}
                onChange={(e) => setProfile((p) => ({ ...p, avatar_url: e.target.value }))}
                placeholder="https://example.com/avatar.jpg"
                className="mt-1"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={profile.name}
                onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                placeholder="Your name"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={profile.email}
                onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))}
                placeholder="your@email.com"
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="bio">Bio</Label>
            <Textarea
              id="bio"
              value={profile.bio}
              onChange={(e) => setProfile((p) => ({ ...p, bio: e.target.value }))}
              placeholder="A short bio about yourself"
              className="mt-1"
              rows={3}
            />
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleSaveProfile}
              disabled={!isProfileDirty || profileMutation.isPending}
              variant={isProfileDirty ? "default" : "secondary"}
            >
              <Save className="mr-2 h-4 w-4" />
              {profileMutation.isPending ? "Saving..." : "Save Profile"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* AI Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5" />
            AI Configuration
          </CardTitle>
          <CardDescription>Configure the AI provider and model settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Row 1: AI Provider + Base URL */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="provider">AI Provider</Label>
              <select
                id="provider"
                value={aiConfig.provider}
                onChange={(e) => {
                  const newProvider = e.target.value;
                  let newBaseUrl = aiConfig.base_url;

                  // Auto-populate base_url based on provider (from ai-provider skills)
                  const defaultUrls: Record<string, string> = {
                    openai: "https://api.openai.com/v1",
                    anthropic: "https://api.anthropic.com",
                    google: "https://generativelanguage.googleapis.com/v1beta/openai",
                    gemini: "https://generativelanguage.googleapis.com/v1beta/openai",
                    zhipuai: "https://open.bigmodel.cn/api/coding/paas/v4",
                    copilot: "http://localhost:1287",
                  };

                  // Check if current base_url is any provider's known default (including old URLs)
                  const allKnownDefaultUrls = [
                    ...Object.values(defaultUrls),
                    "https://open.bigmodel.cn/api/paas/v4", // Old incorrect zhipu URL
                  ];
                  const isCurrentUrlADefault = allKnownDefaultUrls.includes(aiConfig.base_url);

                  // Replace base_url if it's empty or is any provider's default URL
                  if (!aiConfig.base_url || isCurrentUrlADefault) {
                    newBaseUrl = defaultUrls[newProvider] ?? aiConfig.base_url;
                  }

                  setAiConfig((c) => ({
                    ...c,
                    provider: newProvider,
                    base_url: newBaseUrl,
                    api_key: "",
                    model: "", // Clear model when switching provider
                  }));
                  setAvailableModels([]);
                }}
                className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google Gemini</option>
                <option value="zhipuai">ZhipuAI (智谱AI)</option>
                <option value="copilot">Copilot Bridge</option>
              </select>
            </div>
            <div>
              <Label htmlFor="base_url">Base URL {aiConfig.provider !== "copilot" && <span className="text-red-500">*</span>}</Label>
              <Input
                id="base_url"
                value={aiConfig.base_url}
                onChange={(e) => {
                  setAiConfig((c) => ({ ...c, base_url: e.target.value }));
                }}
                placeholder={
                  aiConfig.provider === "openai"
                    ? "https://api.openai.com/v1"
                    : aiConfig.provider === "anthropic"
                      ? "https://api.anthropic.com"
                      : aiConfig.provider === "google"
                        ? "https://generativelanguage.googleapis.com/v1beta/openai"
                        : aiConfig.provider === "zhipuai"
                          ? "https://open.bigmodel.cn/api/coding/paas/v4"
                          : "http://localhost:1287"
                }
              />
            </div>
          </div>

          {/* Row 2: API Key (optional for Copilot) */}
          <div>
            <Label htmlFor="api_key">
              API Key{" "}
              {aiConfig.provider === "copilot" ? (
                <span className="text-gray-500"> (Optional)</span>
              ) : (
                <span className="text-red-500">*</span>
              )}
            </Label>
            <div className="relative mt-1">
              <Input
                id="api_key"
                type={showApiKey ? "text" : "password"}
                value={aiConfig.api_key}
                onChange={(e) => setAiConfig((c) => ({ ...c, api_key: e.target.value }))}
                placeholder={
                  aiConfig.provider === "copilot"
                    ? "(Not required for Copilot Bridge)"
                    : settingsData
                      ? "Leave empty to keep current key; enter new key to change"
                      : "Enter your API key"
                }
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-1 top-1/2 -translate-y-1/2"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Row 3: Model Selector + Get Models Button */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="model">Model</Label>
              <select
                id="model"
                value={aiConfig.model}
                onChange={(e) => setAiConfig((c) => ({ ...c, model: e.target.value }))}
                disabled={availableModels.length === 0}
                className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="">-- Select a model --</option>
                {(availableModels || []).length > 0 ? (
                  availableModels.map((m, idx) => {
                    const modelId =
                      typeof m === "string" ? m : ((m as { id?: string; name?: string }).id ?? (m as { name?: string }).name ?? "");
                    const modelName =
                      typeof m === "string" ? m : ((m as { name?: string; id?: string }).name ?? (m as { id?: string }).id ?? modelId);
                    return (
                      <option key={`${modelId}-${idx}`} value={modelId}>
                        {modelName || modelId}
                      </option>
                    );
                  })
                ) : (
                  <option value={aiConfig.model}>{aiConfig.model || "No models loaded"}</option>
                )}
              </select>
            </div>
            <div className="flex flex-col justify-end">
              {/* Get Models button background: edit className below (very light blue) */}
              <Button
                onClick={handleGetModels}
                disabled={getModelsDisabled}
                variant="secondary"
                className="bg-sky-200 hover:bg-sky-300 text-slate-800 border border-sky-200"
              >
                {isLoadingModels ? "Loading..." : "Get Models"}
              </Button>
            </div>
          </div>

          {/* Row 4: Max Tokens + Temperature (hide temperature for Copilot) */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label htmlFor="max_tokens">Max Tokens</Label>
              <Input
                id="max_tokens"
                type="number"
                value={aiConfig.max_tokens}
                onChange={(e) => setAiConfig((c) => ({ ...c, max_tokens: parseInt(e.target.value) }))}
                className="mt-1"
              />
            </div>
            {aiConfig.provider !== "copilot" && (
              <div>
                <Label htmlFor="temperature">Temperature</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={aiConfig.temperature}
                  onChange={(e) => setAiConfig((c) => ({ ...c, temperature: parseFloat(e.target.value) }))}
                  className="mt-1"
                />
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <Button
              onClick={handleSaveAIConfig}
              disabled={!isAiConfigDirty || aiConfigMutation.isPending}
              variant={isAiConfigDirty ? "default" : "secondary"}
            >
              <Save className="mr-2 h-4 w-4" />
              {aiConfigMutation.isPending ? "Saving..." : "Save AI Config"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Search Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Search Configuration
          </CardTitle>
          <CardDescription>Configure web search for referenced materials</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="search_engine">Search Engine</Label>
            <select
              id="search_engine"
              value={searchEngine}
              onChange={(e) => setSearchEngine(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="duckduckgo">DuckDuckGo (Default)</option>
              <option value="google">Google</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">Used to search for referenced books and articles</p>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={handleSaveSearchEngine}
              disabled={!isSearchEngineDirty || searchEngineMutation.isPending}
              variant={isSearchEngineDirty ? "default" : "secondary"}
            >
              <Save className="mr-2 h-4 w-4" />
              {searchEngineMutation.isPending ? "Saving..." : "Save Search Settings"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
