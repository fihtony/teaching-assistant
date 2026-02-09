/**
 * Greeting banner component
 */

import { useQuery } from "@tanstack/react-query";
import { greetingApi, settingsApi } from "@/services/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Sparkles, BookOpen } from "lucide-react";

export function GreetingBanner() {
  const { data: greeting, isLoading: greetingLoading } = useQuery({
    queryKey: ["greeting"],
    queryFn: greetingApi.get,
    staleTime: 0, // Always fetch fresh greeting
  });

  const { data: profile } = useQuery({
    queryKey: ["teacher-profile"],
    queryFn: settingsApi.getTeacherProfile,
  });

  return (
    <div className="mb-8 overflow-hidden rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white shadow-lg">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Avatar className="h-16 w-16 border-2 border-white/30">
            <AvatarImage src={profile?.avatar_url} />
            <AvatarFallback className="bg-white/20 text-xl text-white">{profile?.name?.charAt(0) || "T"}</AvatarFallback>
          </Avatar>
          <div>
            <h2 className="text-2xl font-bold">Welcome back, {profile?.name || "Teacher"}!</h2>
            {greetingLoading ? (
              <p className="mt-1 flex items-center gap-2 text-white/80">
                <Sparkles className="h-4 w-4 animate-pulse" />
                Loading your personalized greeting...
              </p>
            ) : (
              <p className="mt-1 max-w-2xl text-white/90">{greeting?.greeting || "Ready to inspire young minds today?"}</p>
            )}
          </div>
        </div>

        {greeting?.source && (
          <div className="flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm">
            <BookOpen className="h-4 w-4" />
            <span>
              From: {greeting.source.title}
              {greeting.source.author && ` by ${greeting.source.author}`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
