import React, { useState, useEffect } from 'react';
import { appointmentsAPI } from '../utils/api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { CheckCircle, Clock, XCircle } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { AvailabilityGridSkeleton } from './ui/loading-states';

export const AvailabilityView = ({ date, secondary }) => {
  const [capacity, setCapacity] = useState({ filled: 0, total: 0 });
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAvailability();
    const interval = setInterval(loadAvailability, 30000);
    return () => clearInterval(interval);
  }, [date]);

  const loadAvailability = async () => {
    try {
      const response = await appointmentsAPI.getAvailableSlots(date);
      const data = response.data;
      // Suporta tanto formato antigo (array) quanto novo (objeto com available_slots)
      const slotsList = Array.isArray(data) ? data : (data.available_slots || []);
      setSlots(slotsList);
      // Calcular capacidade do dia
      let filled = 0;
      let total = 0;
      slotsList.forEach(slot => {
        total += 1;
        if (slot.occupied || slot.appointments?.length > 0) filled += 1;
      });
      setCapacity({ filled, total });
    } catch (error) {
      console.error('Erro ao carregar disponibilidade:', error);
      setSlots([]);
      setCapacity({ filled: 0, total: 0 });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card className={secondary ? 'bg-muted/60 border border-border/40 shadow-none' : ''}>
        <CardHeader className="pb-4">
          <CardTitle className={secondary ? 'text-base font-medium text-muted-foreground' : 'text-lg font-semibold text-foreground'}>
            Horários Disponíveis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AvailabilityGridSkeleton />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={secondary ? 'bg-muted/60 border border-border/40 shadow-none' : 'shadow-sm border-border'} data-testid="availability-view">
      <CardHeader className="pb-4">
        <CardTitle className={secondary ? 'text-base font-medium text-muted-foreground' : 'text-lg font-semibold text-foreground'}>
          Horários Disponíveis - {format(parseISO(date), "dd 'de' MMMM", { locale: ptBR })}
        </CardTitle>
        {/* Barra de capacidade do dia */}
        {capacity.total > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-muted-foreground font-medium">Capacidade do dia</span>
              <span className="text-xs text-muted-foreground font-semibold">{Math.round((capacity.filled / capacity.total) * 100)}%</span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-2 bg-primary transition-all duration-500"
                style={{ width: `${(capacity.filled / capacity.total) * 100}%` }}
              ></div>
            </div>
            <div className="text-xs text-muted-foreground mt-1 text-right">
              {capacity.filled} de {capacity.total} slots preenchidos
            </div>
          </div>
        )}
      </CardHeader>
      <CardContent>
        {slots.length === 0 ? (
          <div className="text-center py-8">
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <p className="text-foreground font-medium">Não há horários disponíveis</p>
            <p className="text-sm text-muted-foreground mt-1">Todos os agentes estão ocupados hoje</p>
          </div>
        ) : (
          <div className="grid grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
            {slots.map((slot) => (
              <button
                key={slot.time_slot}
                type="button"
                className={`
                  group relative w-full p-3 rounded-lg border text-center transition-all duration-200
                  ${secondary ? 'border-border/30 bg-muted/40' : 'bg-background/80'}
                  ${slot.is_current
                    ? 'border-sky-400/40 bg-sky-50/60 dark:bg-sky-900/10 ring-1 ring-sky-300/20'
                    : slot.is_past
                      ? 'border-border bg-muted/60 opacity-50 pointer-events-none'
                      : slot.available_agents > 2
                        ? 'bg-green-50/60 dark:bg-green-900/10 border-green-200/30 dark:border-green-700/20'
                        : slot.available_agents > 0
                          ? 'bg-amber-50/60 dark:bg-amber-900/10 border-amber-200/20 dark:border-amber-700/20'
                          : 'bg-red-50/60 dark:bg-red-900/10 border-red-200/20 dark:border-red-700/20 opacity-60 pointer-events-none'}
                  ${!slot.is_past && !slot.is_current ? 'hover:brightness-105 hover:shadow-2xl hover:z-10 hover:bg-white/80 dark:hover:bg-zinc-900/80' : ''}
                  focus:outline-none focus:ring-2 focus:ring-primary/30
                  ${slot.is_past ? '' : 'cursor-pointer'}
                `}
                data-testid={`slot-${slot.time_slot}`}
                onClick={() => {
                  if (!slot.is_past && !slot.is_current && slot.available_agents > 0 && typeof window.handleCreateAppointment === 'function') {
                    window.handleCreateAppointment({
                      date,
                      time_slot: slot.time_slot
                    });
                  }
                }}
                tabIndex={slot.is_past ? -1 : 0}
                disabled={slot.is_past || slot.is_current || slot.available_agents === 0}
              >
                {slot.is_current && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 rounded-r bg-sky-400/60" style={{boxShadow:'0 0 4px 0 #38bdf8aa'}}></div>
                )}
                <div className="flex items-center justify-center mb-1">
                  {slot.available_agents > 2 ? (
                    <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                  ) : slot.available_agents > 0 ? (
                    <Clock className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                  )}
                </div>
                <p className="text-sm font-semibold text-foreground">{slot.time_slot}</p>
                <p className={`
                  text-xs font-medium mt-1
                  ${slot.available_agents > 2 ? 'text-green-700 dark:text-green-300' : 
                    slot.available_agents > 0 ? 'text-yellow-700 dark:text-yellow-300' : 'text-red-700 dark:text-red-300'}
                `}>
                  {slot.available_agents} livre{slot.available_agents !== 1 ? 's' : ''}
                </p>
              </button>
            ))}
          </div>
        )}

        <div className="flex items-center justify-center gap-6 mt-6 pt-6 border-t border-border">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-100 dark:bg-green-900/40 border-2 border-green-300 dark:border-green-600 rounded"></div>
            <span className="text-sm text-muted-foreground">Muito disponível</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-100 dark:bg-yellow-900/40 border-2 border-yellow-300 dark:border-yellow-600 rounded"></div>
            <span className="text-sm text-muted-foreground">Pouco disponível</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-100 dark:bg-red-900/40 border-2 border-red-300 dark:border-red-600 rounded opacity-60"></div>
            <span className="text-sm text-muted-foreground">Indisponível</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
