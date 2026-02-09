/**
 * Layout components for the application
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Home, FileText, History, Settings, BookTemplate, Database } from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { label: "Dashboard", href: "/", icon: <Home className="h-6 w-6" /> },
  { label: "Grade", href: "/grade", icon: <FileText className="h-6 w-6" /> },
  { label: "History", href: "/history", icon: <History className="h-6 w-6" /> },
  { label: "Templates", href: "/templates", icon: <BookTemplate className="h-6 w-6" /> },
  { label: "Settings", href: "/settings", icon: <Settings className="h-6 w-6" /> },
];

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-white">
        {/* Logo */}
        <div className="flex h-16 items-center border-b px-6">
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Grading</h1>
              <p className="text-xs text-gray-500">English Teaching</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="space-y-1 p-4">
          {navItems.map((item) => (
            <Link
              key={item.href}
              to={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors",
                location.pathname === item.href ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-100 hover:text-gray-900",
              )}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Cache info */}
        <div className="absolute bottom-4 left-4 right-4">
          <Link to="/cache" className="flex items-center gap-2 rounded-lg border bg-gray-50 p-3 text-sm text-gray-600 hover:bg-gray-100">
            <Database className="h-4 w-4" />
            <span>Article Cache</span>
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <div className="p-8">{children}</div>
      </main>
    </div>
  );
}
