/**
 * Settings page - configure AI, teacher profile, and app settings
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Save, User, Brain, Search, Eye, EyeOff } from "lucide-react";

export function SettingsPage() {
  const queryClient = useQueryClient();
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

  // Load data
  const { data: profileData, isLoading: profileLoading } = useQuery({
    queryKey: ["teacher-profile"],
    queryFn: settingsApi.getTeacherProfile,
  });

  const { data: aiConfigData, isLoading: aiConfigLoading } = useQuery({
    queryKey: ["ai-config"],
    queryFn: settingsApi.getAIConfig,
  });

  const { data: searchEngineData, isLoading: searchEngineLoading } = useQuery({
    queryKey: ["search-engine"],
    queryFn: settingsApi.getSearchEngine,
  });

  // Mutations (定义在前面，这样 useEffect 可以使用它们)
  const profileMutation = useMutation({
    mutationFn: settingsApi.updateTeacherProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher-profile"] });
    },
  });

  const aiConfigMutation = useMutation({
    mutationFn: settingsApi.updateAIConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-config"] });
    },
  });

  const searchEngineMutation = useMutation({
    mutationFn: (engine: string) => settingsApi.updateSearchEngine(engine),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["search-engine"] });
    },
  });

  React.useEffect(() => {
    if (profileData) {
      setProfile({
        name: profileData.name || "",
        email: profileData.email || "",
        avatar_url: profileData.avatar_url || "",
        bio: profileData.bio || "",
      });
    }
  }, [profileData]);

  React.useEffect(() => {
    if (profileMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["teacher-profile"] });
    }
  }, [profileMutation.isSuccess, queryClient]);

  React.useEffect(() => {
    if (aiConfigData) {
      setAiConfig({
        provider: aiConfigData.provider || "openai",
        model: aiConfigData.model || "gpt-4",
        api_key: aiConfigData.api_key || "",
        base_url: aiConfigData.base_url || "",
        temperature: aiConfigData.temperature || 0.7,
        max_tokens: aiConfigData.max_tokens || 4096,
      });
    }
  }, [aiConfigData]);

  React.useEffect(() => {
    if (searchEngineData) {
      setSearchEngine(searchEngineData.engine || "duckduckgo");
    }
  }, [searchEngineData]);

  React.useEffect(() => {
    if (aiConfigMutation.isSuccess) {
      queryClient.invalidateQueries({ queryKey: ["ai-config"] });
    }
  }, [aiConfigMutation.isSuccess, queryClient]);

  const handleSaveProfile = () => {
    profileMutation.mutate(profile);
  };

  const handleSaveAIConfig = () => {
    aiConfigMutation.mutate(aiConfig);
  };

  const handleSaveSearchEngine = () => {
    searchEngineMutation.mutate(searchEngine);
  };

  const handleGetModels = async () => {
    if (!aiConfig.base_url && aiConfig.provider !== "copilot") {
      alert("Please enter a Base URL first");
      return;
    }

    if (aiConfig.provider !== "copilot" && !aiConfig.api_key) {
      alert("Please enter an API Key first");
      return;
    }

    setIsLoadingModels(true);
    try {
      const models = await settingsApi.getModels(aiConfig.provider, aiConfig.base_url);
      setAvailableModels(models);
    } catch (error) {
      console.error("Failed to fetch models:", error);
      alert("Failed to fetch models. Please check your settings.");
    } finally {
      setIsLoadingModels(false);
    }
  };

  if (profileLoading || aiConfigLoading || searchEngineLoading) {
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
            <Button onClick={handleSaveProfile} disabled={profileMutation.isPending}>
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

                  // Auto-populate base_url based on provider if empty
                  if (
                    !aiConfig.base_url ||
                    aiConfig.base_url === "https://api.openai.com/v1" ||
                    aiConfig.base_url === "https://api.anthropic.com" ||
                    aiConfig.base_url === "https://generativelanguage.googleapis.com" ||
                    aiConfig.base_url === "http://localhost:1287"
                  ) {
                    if (newProvider === "openai") {
                      newBaseUrl = "https://api.openai.com/v1";
                    } else if (newProvider === "anthropic") {
                      newBaseUrl = "https://api.anthropic.com";
                    } else if (newProvider === "google") {
                      newBaseUrl = "https://generativelanguage.googleapis.com";
                    } else if (newProvider === "copilot") {
                      newBaseUrl = "http://localhost:1287";
                    }
                  }

                  setAiConfig((c) => ({ ...c, provider: newProvider, base_url: newBaseUrl }));
                  setAvailableModels([]);
                }}
                className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="google">Google</option>
                <option value="copilot">Copilot Bridge</option>
              </select>
            </div>
            <div>
              <Label htmlFor="base_url">Base URL {aiConfig.provider !== "copilot" && <span className="text-red-500">*</span>}</Label>
              <Input
                id="base_url"
                value={aiConfig.base_url}
                onChange={(e) => setAiConfig((c) => ({ ...c, base_url: e.target.value }))}
                placeholder={
                  aiConfig.provider === "openai"
                    ? "https://api.openai.com/v1"
                    : aiConfig.provider === "anthropic"
                      ? "https://api.anthropic.com"
                      : aiConfig.provider === "google"
                        ? "https://generativelanguage.googleapis.com"
                        : "http://localhost:1287"
                }
                className="mt-1"
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
                placeholder={aiConfig.provider === "copilot" ? "(Not required for Copilot Bridge)" : "sk-..."}
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
                className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">-- Select a model --</option>
                {availableModels.length > 0 ? (
                  availableModels.map((m, idx) => {
                    // Handle both string and object formats
                    const modelId = typeof m === "string" ? m : (m as any).id || (m as any).name;
                    const modelName = typeof m === "string" ? m : (m as any).name;
                    return (
                      <option key={`${modelId}-${idx}`} value={modelId}>
                        {modelName}
                      </option>
                    );
                  })
                ) : (
                  <option value={aiConfig.model}>{aiConfig.model || "No models loaded"}</option>
                )}
              </select>
            </div>
            <div className="flex flex-col justify-end">
              <Button
                onClick={handleGetModels}
                disabled={
                  isLoadingModels ||
                  (!aiConfig.base_url && aiConfig.provider !== "copilot") ||
                  (aiConfig.provider !== "copilot" && !aiConfig.api_key)
                }
                variant="outline"
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
            <Button onClick={handleSaveAIConfig} disabled={aiConfigMutation.isPending}>
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
            <Button onClick={handleSaveSearchEngine} disabled={searchEngineMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {searchEngineMutation.isPending ? "Saving..." : "Save Search Settings"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
