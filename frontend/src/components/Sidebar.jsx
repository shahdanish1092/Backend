import { NavLink, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  Mic, 
  Users, 
  Settings, 
  CheckCircle,
  Menu,
  X
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Invoice Manager', href: '/invoices', icon: FileText },
  { name: 'Meeting Summarizer', href: '/meetings', icon: Mic },
  { name: 'Approval Center', href: '/approvals', icon: CheckCircle },
  { name: 'HR Connect', href: '/hr-connect', icon: Users },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-slate-700">
        <img 
          src="https://customer-assets.emergentagent.com/job_office-auto-hub/artifacts/k42pj7ep_image.pngb" 
          alt="Spatial+ Logo" 
          className="h-10 w-auto"
          onError={(e) => {
            e.target.style.display = 'none';
            e.target.nextSibling.style.display = 'flex';
          }}
        />
        <div className="hidden items-center gap-2">
          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center">
            <Settings className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-outfit font-semibold text-white">spatial<sup className="text-orange-500">+</sup></span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              data-testid={`nav-${item.name.toLowerCase().replace(/\s+/g, '-')}`}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer',
                isActive 
                  ? 'bg-slate-800 text-white border-l-2 border-orange-500' 
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white'
              )}
              onClick={() => setMobileOpen(false)}
            >
              <item.icon className={cn('w-5 h-5', isActive ? 'text-orange-500' : '')} />
              {item.name}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-slate-700">
        <p className="text-xs text-slate-500 text-center">
          create efficiencies
        </p>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile menu button */}
      <button
        data-testid="mobile-menu-toggle"
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-slate-900 text-white rounded-lg"
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside 
        className={cn(
          'lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-[#0F172A] flex flex-col transform transition-transform duration-300',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <SidebarContent />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:fixed lg:inset-y-0 lg:left-0 lg:z-50 lg:w-64 bg-[#0F172A]">
        <SidebarContent />
      </aside>
    </>
  );
}
