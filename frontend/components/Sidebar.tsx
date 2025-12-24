"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  LayoutDashboard, 
  FileText, 
  Database, 
  Code, 
  Tag, 
  Settings, 
  ChevronLeft, 
  ChevronRight, 
  Activity,
  Search,
  BookOpen
} from 'lucide-react';
import { cn } from "@/lib/utils";

/**
 * Sidebar Component
 * 
 * Main navigation for the application.
 * Supports collapsible state and renders navigation links with active state highlighting.
 * Includes user profile summary at the bottom.
 */
export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  const navItems = [
    { label: "Workspace", href: "/", icon: LayoutDashboard },
    { label: "Artifacts", href: "/artifacts", icon: FileText },
    { label: "Cookbooks", href: "/cookbooks", icon: BookOpen },
    { label: "Logs", href: "/logs", icon: Activity },
    { label: "APIs", href: "/apis", icon: Code },
    { label: "Tags", href: "/tags", icon: Tag },
  ];

  return (
    <motion.aside 
      initial={{ width: 260 }}
      animate={{ width: collapsed ? 80 : 260 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="relative z-50 h-screen shrink-0 border-r border-white/10 glass-card bg-card/80 backdrop-blur-xl"
    >
      <div className="flex h-16 items-center justify-between px-6 border-b border-white/5">
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2"
            >
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-cyan-400 to-purple-600 flex items-center justify-center text-white font-bold shadow-lg shadow-purple-500/20">
                P
              </div>
              <span className="font-bold text-lg bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                PMOVES-DoX
              </span>
            </motion.div>
          )}
        </AnimatePresence>
        
        <button 
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground transition-colors absolute -right-3 top-6 bg-card border border-white/10 shadow-sm"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      <nav className="p-4 space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          
          return (
            <Link 
              key={item.href} 
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group relative overflow-hidden",
                isActive 
                  ? "bg-primary/20 text-white shadow-lg shadow-primary/10 border border-primary/20" 
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="active-indicator"
                  className="absolute inset-0 bg-primary/10 rounded-xl"
                  initial={false}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <Icon size={20} className={cn("relative z-10", isActive && "text-primary-foreground")} />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    className="font-medium whitespace-nowrap relative z-10"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-4 left-0 right-0 px-4">
        <div className={cn(
          "bg-white/5 rounded-xl border border-white/5 p-4 transition-all",
          collapsed ? "items-center justify-center flex" : ""
        )}>
          {!collapsed ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-gradient-to-r from-pink-500 to-purple-500" />
                <div>
                  <div className="text-sm font-medium text-white">Guest User</div>
                  <div className="text-xs text-muted-foreground">Admin Access</div>
                </div>
              </div>
              <button className="w-full py-1.5 text-xs font-medium bg-white/5 hover:bg-white/10 rounded-lg transition-colors border border-white/5">
                Manage Account
              </button>
            </div>
          ) : (
             <div className="h-8 w-8 rounded-full bg-gradient-to-r from-pink-500 to-purple-500" />
          )}
        </div>
      </div>
    </motion.aside>
  );
}
