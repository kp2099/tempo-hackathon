import { Link, useLocation } from 'react-router-dom';
import { Bot, Home, PlusCircle, Shield, FileText } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Dashboard', icon: Home },
  { path: '/submit', label: 'Submit Expense', icon: PlusCircle },
  { path: '/admin', label: 'Admin', icon: Shield },
  { path: '/audit', label: 'Audit Trail', icon: FileText },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="bg-slate-800/80 backdrop-blur-md border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2 rounded-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold text-white">Tempo</span>
              <span className="text-lg font-light text-blue-400">ExpenseAI</span>
            </div>
          </Link>

          {/* Nav links */}
          <div className="flex items-center gap-1">
            {navItems.map(({ path, label, icon: Icon }) => {
              const isActive = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}
          </div>

          {/* Agent status */}
          <div className="flex items-center gap-2 bg-slate-700/50 px-3 py-1.5 rounded-full">
            <div className="w-2 h-2 bg-green-400 rounded-full pulse-dot" />
            <span className="text-xs font-medium text-green-400">AgentFin Online</span>
          </div>
        </div>
      </div>
    </nav>
  );
}

