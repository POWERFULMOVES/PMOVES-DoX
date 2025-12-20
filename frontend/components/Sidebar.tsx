"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, FileText, Server, Tags, Archive, Settings, Activity } from 'lucide-react';

const navItems = [
  { name: 'Workspace', href: '/', icon: LayoutDashboard },
  { name: 'Logs', href: '/logs', icon: Activity },
  { name: 'APIs', href: '/apis', icon: Server },
  { name: 'Tags', href: '/tags', icon: Tags },
  { name: 'Artifacts', href: '/artifacts', icon: Archive },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col w-64 bg-gray-950 h-screen border-r border-gray-800">
      <div className="flex items-center justify-center h-16 border-b border-gray-800">
        <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600">
          PMOVES-DoX
        </h1>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 ${
                isActive
                  ? 'bg-blue-600/10 text-blue-400 border-l-4 border-blue-500'
                  : 'text-gray-400 hover:bg-gray-900 hover:text-white border-l-4 border-transparent'
              }`}
            >
              <Icon className="w-5 h-5 mr-3" />
              {item.name}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-gray-800">
        <Link
          href="/settings"
          className="flex items-center px-4 py-3 text-sm font-medium text-gray-400 rounded-lg hover:bg-gray-900 hover:text-white transition-colors duration-200"
        >
          <Settings className="w-5 h-5 mr-3" />
          Settings
        </Link>
      </div>
    </div>
  );
}
