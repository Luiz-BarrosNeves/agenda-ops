import React, { useState, useEffect } from 'react';
import { slotsAPI } from '../utils/api';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { toast } from 'sonner';
import { Clock, Plus, Minus, Calendar } from 'lucide-react';
import { format, addDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const EXTRA_SLOTS = ['07:40', '12:40', '18:00', '18:20', '18:40'];

export const ExtraHoursManager = () => {
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [activeSlots, setActiveSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadExtraHours();
  }, [selectedDate]);

  const loadExtraHours = async () => {
    setLoading(true);
    try {
      const response = await slotsAPI.getExtraHours(selectedDate);
      setActiveSlots(response.data.active_slots || []);
    } catch (error) {
      console.error('Erro ao carregar horários extras:', error);
      // Fallback para localStorage se o backend falhar
      const stored = localStorage.getItem(`extra_hours_${selectedDate}`);
      if (stored) {
        setActiveSlots(JSON.parse(stored));
      } else {
        setActiveSlots([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleSlot = (slot) => {
    if (activeSlots.includes(slot)) {
      setActiveSlots(activeSlots.filter(s => s !== slot));
    } else {
      setActiveSlots([...activeSlots, slot]);
    }
  };

  const saveExtraHours = async () => {
    setSaving(true);
    try {
      await slotsAPI.updateExtraHours(selectedDate, activeSlots);
      // Backup em localStorage
      localStorage.setItem(`extra_hours_${selectedDate}`, JSON.stringify(activeSlots));
      toast.success(`${activeSlots.length} horário(s) extra(s) ativado(s) para ${format(new Date(selectedDate + 'T12:00:00'), "dd/MM/yyyy")}`);
    } catch (error) {
      console.error('Erro ao salvar:', error);
      // Salvar apenas em localStorage como fallback
      localStorage.setItem(`extra_hours_${selectedDate}`, JSON.stringify(activeSlots));
      toast.success('Horários salvos localmente');
    } finally {
      setSaving(false);
    }
  };

  const activateAll = () => {
    setActiveSlots([...EXTRA_SLOTS]);
  };

  const deactivateAll = () => {
    setActiveSlots([]);
  };

  // Atalhos de data
  const quickDates = [
    { label: 'Hoje', date: format(new Date(), 'yyyy-MM-dd') },
    { label: 'Amanhã', date: format(addDays(new Date(), 1), 'yyyy-MM-dd') },
    { label: 'Depois', date: format(addDays(new Date(), 2), 'yyyy-MM-dd') },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Clock className="w-5 h-5 text-amber-500" />
          Horários Extras (Hora Extra)
        </CardTitle>
        <CardDescription>
          Ative horários especiais quando necessário para hora extra da equipe
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Seletor de data */}
        <div className="flex items-center gap-3">
          <Calendar className="w-4 h-4 text-slate-400" />
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="border border-slate-200 rounded-md px-3 py-1.5 text-sm"
          />
          <div className="flex gap-1">
            {quickDates.map((qd) => (
              <Button
                key={qd.date}
                variant={selectedDate === qd.date ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedDate(qd.date)}
                className="text-xs"
              >
                {qd.label}
              </Button>
            ))}
          </div>
        </div>

        {/* Data selecionada */}
        <div className="p-3 bg-slate-50 rounded-lg">
          <p className="text-sm font-medium text-slate-700">
            {format(new Date(selectedDate + 'T12:00:00'), "EEEE, dd 'de' MMMM", { locale: ptBR })}
          </p>
        </div>

        {loading ? (
          <div className="text-center py-4 text-slate-500">Carregando...</div>
        ) : (
          <>
            {/* Grid de horários */}
            <div className="grid grid-cols-5 gap-2">
              {EXTRA_SLOTS.map((slot) => {
                const isActive = activeSlots.includes(slot);
                return (
                  <button
                    key={slot}
                    onClick={() => toggleSlot(slot)}
                    className={`p-3 rounded-lg border-2 transition-all ${
                      isActive
                        ? 'border-amber-400 bg-amber-50 text-amber-800'
                        : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    <Clock className={`w-5 h-5 mx-auto mb-1 ${isActive ? 'text-amber-500' : 'text-slate-400'}`} />
                    <span className="text-sm font-medium">{slot}</span>
                    <div className="mt-1">
                      {isActive ? (
                        <span className="text-xs text-amber-600 flex items-center justify-center gap-1">
                          <Minus className="w-3 h-3" /> Ativo
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400 flex items-center justify-center gap-1">
                          <Plus className="w-3 h-3" /> Inativo
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Ações */}
            <div className="flex items-center justify-between pt-4 border-t">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={activateAll}>
                  Ativar Todos
                </Button>
                <Button variant="outline" size="sm" onClick={deactivateAll}>
                  Desativar Todos
                </Button>
              </div>
              <Button onClick={saveExtraHours} disabled={saving}>
                {saving ? 'Salvando...' : 'Salvar Alterações'}
              </Button>
            </div>

            {/* Status */}
            <div className="text-sm text-slate-500">
              {activeSlots.length === 0 ? (
                <span>Nenhum horário extra ativado para esta data</span>
              ) : (
                <span>{activeSlots.length} horário(s) extra(s) ativado(s): {activeSlots.sort().join(', ')}</span>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};
