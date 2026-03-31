import React from 'react';
import { Skeleton } from './skeleton';
import { Card, CardContent, CardHeader } from './card';
import { Calendar, Users, Clock, FileText, Inbox } from 'lucide-react';

// Skeleton para cards de métricas do dashboard
export const MetricCardSkeleton = () => (
  <Card>
    <CardHeader className="pb-2">
      <Skeleton className="h-4 w-24" />
    </CardHeader>
    <CardContent>
      <Skeleton className="h-9 w-16 mb-1" />
      <Skeleton className="h-3 w-12" />
    </CardContent>
  </Card>
);

// Skeleton para lista de usuários
export const UserListSkeleton = ({ count = 3 }) => (
  <div className="space-y-3">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="flex items-center gap-4 p-4 border border-border rounded-lg bg-card">
        <Skeleton className="w-12 h-12 rounded-full" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-3 w-48" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>
    ))}
  </div>
);

// Skeleton para slots de agenda
export const AgendaSlotSkeleton = ({ count = 5 }) => (
  <div className="space-y-2">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="border border-border rounded-lg p-3 bg-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="h-5 w-12" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-7 w-16" />
        </div>
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-2">
          <Skeleton className="h-16 rounded" />
          <Skeleton className="h-16 rounded" />
        </div>
      </div>
    ))}
  </div>
);

// Skeleton para cards de agendamento
export const AppointmentCardSkeleton = ({ count = 3 }) => (
  <div className="space-y-3">
    {Array.from({ length: count }).map((_, i) => (
      <div key={i} className="rounded-lg border-l-4 border-muted bg-muted/30 p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-28" />
            <div className="flex items-center gap-4 mt-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
            </div>
          </div>
          <Skeleton className="h-6 w-20 rounded" />
        </div>
      </div>
    ))}
  </div>
);

// Skeleton para relatórios
export const ReportSkeleton = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-muted/50 rounded-lg p-4 text-center">
          <Skeleton className="h-9 w-16 mx-auto mb-2" />
          <Skeleton className="h-4 w-24 mx-auto" />
        </div>
      ))}
    </div>
    <div className="space-y-2">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-20 rounded-lg" />
      ))}
    </div>
  </div>
);

// Componente de estado vazio genérico com ilustração
export const EmptyState = ({ 
  icon: Icon, 
  title, 
  description, 
  action,
  actionLabel,
  variant = 'default' // 'default' | 'calendar' | 'users' | 'inbox'
}) => {
  // Ilustrações SVG inline baseadas no variant
  const illustrations = {
    calendar: (
      <svg className="w-32 h-32 mx-auto mb-4 opacity-40" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="30" y="40" width="140" height="130" rx="12" className="stroke-muted-foreground" strokeWidth="3" fill="none"/>
        <path d="M30 70H170" className="stroke-muted-foreground" strokeWidth="3"/>
        <rect x="50" y="25" width="4" height="30" rx="2" className="fill-muted-foreground"/>
        <rect x="90" y="25" width="4" height="30" rx="2" className="fill-muted-foreground"/>
        <rect x="130" y="25" width="4" height="30" rx="2" className="fill-muted-foreground"/>
        <circle cx="70" cy="100" r="8" className="fill-primary/30"/>
        <circle cx="100" cy="100" r="8" className="fill-primary/50"/>
        <circle cx="130" cy="100" r="8" className="fill-muted-foreground/30"/>
        <circle cx="70" cy="130" r="8" className="fill-muted-foreground/30"/>
        <circle cx="100" cy="130" r="8" className="fill-muted-foreground/30"/>
        <circle cx="130" cy="130" r="8" className="fill-muted-foreground/30"/>
      </svg>
    ),
    users: (
      <svg className="w-32 h-32 mx-auto mb-4 opacity-40" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="100" cy="70" r="30" className="stroke-muted-foreground" strokeWidth="3" fill="none"/>
        <path d="M50 160C50 130 70 110 100 110C130 110 150 130 150 160" className="stroke-muted-foreground" strokeWidth="3" strokeLinecap="round" fill="none"/>
        <circle cx="160" cy="80" r="18" className="stroke-muted-foreground/50" strokeWidth="2" fill="none"/>
        <path d="M140 140C140 125 148 115 165 115" className="stroke-muted-foreground/50" strokeWidth="2" strokeLinecap="round" fill="none"/>
        <circle cx="40" cy="80" r="18" className="stroke-muted-foreground/50" strokeWidth="2" fill="none"/>
        <path d="M60 140C60 125 52 115 35 115" className="stroke-muted-foreground/50" strokeWidth="2" strokeLinecap="round" fill="none"/>
      </svg>
    ),
    inbox: (
      <svg className="w-32 h-32 mx-auto mb-4 opacity-40" viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M40 60L100 100L160 60" className="stroke-muted-foreground" strokeWidth="3" strokeLinecap="round" fill="none"/>
        <rect x="40" y="60" width="120" height="100" rx="8" className="stroke-muted-foreground" strokeWidth="3" fill="none"/>
        <path d="M40 100H70L85 115H115L130 100H160" className="stroke-muted-foreground" strokeWidth="3" strokeLinecap="round" fill="none"/>
      </svg>
    ),
    default: null
  };

  const SelectedIllustration = illustrations[variant];

  return (
    <div className="text-center py-12 fade-in">
      {SelectedIllustration ? (
        SelectedIllustration
      ) : (
        Icon && <Icon className="w-16 h-16 mx-auto text-muted-foreground/30 mb-4" />
      )}
      <h3 className="text-lg font-semibold text-foreground mb-2">{title}</h3>
      {description && <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">{description}</p>}
      {action && actionLabel && (
        <button
          onClick={action}
          className="inline-flex items-center px-4 py-2 text-sm font-medium text-primary hover:text-primary/80 bg-primary/5 hover:bg-primary/10 rounded-lg transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
};

// Skeleton para grid de disponibilidade
export const AvailabilityGridSkeleton = () => (
  <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
    {Array.from({ length: 16 }).map((_, i) => (
      <Skeleton key={i} className="h-16 rounded-lg" />
    ))}
  </div>
);

// Loading spinner inline
export const InlineLoader = ({ text = 'Carregando...' }) => (
  <div className="flex items-center gap-2 text-sm text-muted-foreground">
    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
    </svg>
    <span>{text}</span>
  </div>
);
