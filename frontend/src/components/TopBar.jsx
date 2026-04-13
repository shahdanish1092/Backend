import { LogOut, Bell, User } from 'lucide-react';
import { Button } from './ui/button';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from './ui/dropdown-menu';
import { Avatar, AvatarFallback } from './ui/avatar';

export function TopBar({ userEmail, onDisconnect }) {
  const initials = userEmail 
    ? userEmail.split('@')[0].slice(0, 2).toUpperCase() 
    : 'U';

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 lg:px-8 sticky top-0 z-40">
      {/* Left spacer for mobile menu */}
      <div className="lg:hidden w-10" />
      
      {/* Page title placeholder */}
      <div className="hidden lg:block" />

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative"
          data-testid="notifications-btn"
        >
          <Bell className="w-5 h-5 text-slate-500" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-orange-500 rounded-full" />
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button 
              variant="ghost" 
              className="flex items-center gap-3 h-auto py-2"
              data-testid="user-menu-trigger"
            >
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-orange-100 text-orange-700 text-sm font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="hidden md:block text-left">
                <p className="text-sm font-medium text-slate-900">{userEmail || 'User'}</p>
                <p className="text-xs text-slate-500">Connected</p>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem className="flex items-center gap-2">
              <User className="w-4 h-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem 
              className="flex items-center gap-2 text-red-600 focus:text-red-600"
              onClick={onDisconnect}
              data-testid="disconnect-btn"
            >
              <LogOut className="w-4 h-4" />
              Disconnect
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
