import React from 'react';
import { useTheme } from '../context/ThemeContext';
import { Moon, Sun } from 'lucide-react';
import { Button } from './ui/button';

export const ThemeToggle = ({ className = '', showLabel = false }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <Button
      variant="outline"
      size={showLabel ? "default" : "sm"}
      onClick={toggleTheme}
      className={`${showLabel ? 'gap-2' : 'w-9 h-9 p-0'} ${className}`}
      title={theme === 'light' ? 'Ativar modo escuro' : 'Ativar modo claro'}
      data-testid="theme-toggle"
    >
      {theme === 'light' ? (
        <>
          <Moon className="w-4 h-4" />
          {showLabel && <span>Modo Escuro</span>}
        </>
      ) : (
        <>
          <Sun className="w-4 h-4" />
          {showLabel && <span>Modo Claro</span>}
        </>
      )}
    </Button>
  );
};

// Botão grande para configurações ou preferências
export const ThemeToggleLarge = ({ className = '' }) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className={`flex items-center justify-between w-full p-3 rounded-lg border border-border hover:bg-accent transition-colors ${className}`}
      data-testid="theme-toggle-large"
    >
      <div className="flex items-center gap-3">
        {theme === 'light' ? (
          <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800">
            <Moon className="w-5 h-5 text-slate-600 dark:text-slate-300" />
          </div>
        ) : (
          <div className="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
            <Sun className="w-5 h-5 text-amber-600" />
          </div>
        )}
        <div className="text-left">
          <p className="font-medium text-foreground">
            {theme === 'light' ? 'Modo Claro' : 'Modo Escuro'}
          </p>
          <p className="text-xs text-muted-foreground">
            {theme === 'light' ? 'Clique para ativar modo escuro' : 'Clique para ativar modo claro'}
          </p>
        </div>
      </div>
      <div className={`w-12 h-6 rounded-full p-1 transition-colors ${theme === 'dark' ? 'bg-primary' : 'bg-slate-200'}`}>
        <div className={`w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${theme === 'dark' ? 'translate-x-6' : 'translate-x-0'}`} />
      </div>
    </button>
  );
};

export default ThemeToggle;
