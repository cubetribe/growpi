'use client';

import { useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Home, Lightbulb, Activity, Settings, LogOut, Sun, Moon, Languages, Leaf, Menu, X, History } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/contexts/LanguageContext';
import { useTheme } from 'next-themes';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { language, setLanguage, t } = useLanguage();
  const { theme, setTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { href: '/dashboard', icon: Home, label: t.nav.dashboard },
    { href: '/lighting', icon: Lightbulb, label: t.nav.lighting },
    { href: '/sensors', icon: Activity, label: t.nav.sensors },
    { href: '/history', icon: History, label: 'History' },
    { href: '/settings', icon: Settings, label: t.nav.settings },
  ];

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' });
    router.push('/login');
    router.refresh();
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <Button
        variant="outline"
        size="icon"
        className="fixed top-4 left-4 z-50 md:hidden border-green-500/20 bg-black/50 backdrop-blur-xl hover:bg-green-500/10"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
      >
        {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </Button>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/80 z-40 md:hidden"
          onClick={closeMobileMenu}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:static
          w-64 h-screen
          bg-black/50 backdrop-blur-xl
          border-r border-green-500/20
          flex flex-col
          relative overflow-hidden
          z-40
          transition-transform duration-300
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/5 to-transparent pointer-events-none" />

        <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-green-500/50 via-green-500/20 to-transparent" />

        <div className="p-6 border-b border-green-500/20 relative z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
              <Leaf className="w-6 h-6 text-green-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-green-400 to-green-600 bg-clip-text text-transparent">
                Grow-Pi
              </h1>
              <p className="text-xs text-gray-400">v1.0.0</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-2 relative z-10">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} onClick={closeMobileMenu}>
                <Button
                  variant="ghost"
                  className={`w-full justify-start gap-3 transition-all duration-300 ${
                    isActive
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30 shadow-lg shadow-green-500/20'
                      : 'text-gray-400 hover:text-green-400 hover:bg-green-500/10'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </Button>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-green-500/20 space-y-2 relative z-10">
          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" className="flex-1 border-green-500/20 hover:bg-green-500/10">
                  <Languages className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem onClick={() => setLanguage('de')}>
                  {language === 'de' && '✓ '}Deutsch
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setLanguage('en')}>
                  {language === 'en' && '✓ '}English
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <Button
              variant="outline"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="flex-1 border-green-500/20 hover:bg-green-500/10"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </Button>
          </div>

          <Button
            variant="outline"
            className="w-full justify-start gap-3 border-red-500/20 text-red-400 hover:bg-red-500/10 hover:text-red-300"
            onClick={handleLogout}
          >
            <LogOut className="w-5 h-5" />
            {t.nav.logout}
          </Button>
        </div>

        <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-green-500/5 to-transparent pointer-events-none" />
      </aside>
    </>
  );
}
