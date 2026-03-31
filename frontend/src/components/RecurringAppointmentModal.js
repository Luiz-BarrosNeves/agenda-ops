import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { appointmentsAPI } from '../utils/api';
import { toast } from 'sonner';
import { format, addDays, addWeeks } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { RepeatIcon, Calendar, Clock, AlertCircle, Loader2, X } from 'lucide-react';

export const RecurringAppointmentModal = ({ 
  isOpen, 
  onClose, 
  originalAppointment, 
  onSuccess 
}) => {
  const [loading, setLoading] = useState(false);
  const [checkingSlots, setCheckingSlots] = useState(false);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [additionalProtocols, setAdditionalProtocols] = useState([]);
  const [newProtocolInput, setNewProtocolInput] = useState('');
  
  const [formData, setFormData] = useState({
    new_protocol: '',
    date: '',
    time_slot: '',
    has_chat: false,
    notes: '',
  });

  useEffect(() => {
    if (isOpen && originalAppointment) {
      // Calcular próxima data (1 semana depois)
      const originalDate = new Date(originalAppointment.date);
      const nextWeekDate = addWeeks(originalDate, 1);
      
      setFormData({
        new_protocol: '',
        date: format(nextWeekDate, 'yyyy-MM-dd'),
        time_slot: originalAppointment.time_slot,
        has_chat: originalAppointment.has_chat,
        notes: '',
      });
      setAdditionalProtocols([]);
    }
  }, [isOpen, originalAppointment]);

  useEffect(() => {
    if (formData.date) {
      checkAvailableSlots();
    }
  }, [formData.date]);

  const checkAvailableSlots = async () => {
    if (!formData.date) return;
    
    setCheckingSlots(true);
    try {
      const response = await appointmentsAPI.getAvailableSlots(formData.date);
      setAvailableSlots(response.data.available_slots || []);
    } catch (error) {
      console.error('Error checking slots:', error);
      setAvailableSlots([]);
    } finally {
      setCheckingSlots(false);
    }
  };

  const handleAddProtocol = () => {
    if (newProtocolInput.trim() && !additionalProtocols.includes(newProtocolInput.trim())) {
      setAdditionalProtocols([...additionalProtocols, newProtocolInput.trim()]);
      setNewProtocolInput('');
    }
  };

  const handleRemoveProtocol = (index) => {
    setAdditionalProtocols(additionalProtocols.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.new_protocol) {
      toast.error('Por favor, informe o novo número de protocolo');
      return;
    }
    
    if (!formData.date || !formData.time_slot) {
      toast.error('Por favor, selecione data e horário');
      return;
    }
    
    setLoading(true);
    try {
      await appointmentsAPI.createRecurring({
        first_name: originalAppointment.first_name,
        last_name: originalAppointment.last_name,
        base_protocol: originalAppointment.protocol_number,
        new_protocol: formData.new_protocol,
        additional_protocols: additionalProtocols,
        has_chat: formData.has_chat,
        date: formData.date,
        time_slot: formData.time_slot,
        notes: formData.notes,
        original_appointment_id: originalAppointment.id,
      });
      
      toast.success('Reagendamento criado com sucesso!');
      onSuccess?.();
      onClose();
    } catch (error) {
      const message = error.response?.data?.detail || 'Erro ao criar reagendamento';
      toast.error(message);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const totalProtocols = 1 + additionalProtocols.length;
  const needsTwoSlots = totalProtocols >= 3;

  if (!originalAppointment) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="recurring-modal">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold tracking-tight flex items-center gap-2 text-foreground">
            <RepeatIcon className="w-5 h-5" />
            Reagendamento Semanal
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Crie um novo agendamento para a próxima semana
          </DialogDescription>
        </DialogHeader>

        {/* Info do agendamento original */}
        <div className="bg-primary/5 rounded-lg p-4 border border-primary/20 mt-2">
          <p className="text-sm font-medium text-primary mb-2">Agendamento Original</p>
          <div className="text-sm text-foreground space-y-1">
            <p><strong>Cliente:</strong> {originalAppointment.first_name} {originalAppointment.last_name}</p>
            <p><strong>Protocolo:</strong> {originalAppointment.protocol_number}</p>
            <p><strong>Data:</strong> {format(new Date(originalAppointment.date), 'dd/MM/yyyy', { locale: ptBR })}</p>
            <p><strong>Horário:</strong> {originalAppointment.time_slot}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 mt-4">
          {/* Novo Protocolo (OBRIGATÓRIO) */}
          <div className="space-y-2">
            <Label htmlFor="new_protocol" className="text-sm font-medium text-foreground">
              Novo Número de Protocolo *
            </Label>
            <Input
              id="new_protocol"
              value={formData.new_protocol}
              onChange={(e) => setFormData({ ...formData, new_protocol: e.target.value })}
              placeholder="Ex: 2025-001235"
              required
              data-testid="recurring-new-protocol"
              className="h-11"
            />
            <p className="text-xs text-muted-foreground">
              Informe o novo protocolo para este reagendamento
            </p>
          </div>

          {/* Protocolos Adicionais */}
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground">Protocolos Adicionais</Label>
            <div className="flex gap-2">
              <Input
                value={newProtocolInput}
                onChange={(e) => setNewProtocolInput(e.target.value)}
                placeholder="Adicionar protocolo"
                className="h-10"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddProtocol())}
              />
              <Button type="button" variant="outline" onClick={handleAddProtocol} className="px-4">
                +
              </Button>
            </div>
            
            {additionalProtocols.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {additionalProtocols.map((proto, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm">
                    <span>{proto}</span>
                    <button type="button" onClick={() => handleRemoveProtocol(idx)} className="hover:text-primary/80">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {needsTwoSlots && (
            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
                    Atenção: {totalProtocols} protocolos
                  </p>
                  <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                    Este agendamento ocupará 2 horários consecutivos
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Data e Horário */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="date" className="text-sm font-medium text-foreground">
                <Calendar className="w-4 h-4 inline mr-1" />
                Nova Data *
              </Label>
              <Input
                id="date"
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                min={format(new Date(), 'yyyy-MM-dd')}
                required
                data-testid="recurring-date"
                className="h-11"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="time_slot" className="text-sm font-medium text-foreground">
                <Clock className="w-4 h-4 inline mr-1" />
                Horário * {checkingSlots && '(Carregando...)'}
              </Label>
              <Select
                value={formData.time_slot}
                onValueChange={(value) => setFormData({ ...formData, time_slot: value })}
                disabled={checkingSlots || availableSlots.length === 0}
              >
                <SelectTrigger data-testid="recurring-time-select" className="h-11">
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  {availableSlots.map((slot) => {
                    // Compatível com string ou objeto
                    const key = typeof slot === 'object' && slot !== null ? slot.time_slot : slot;
                    const value = typeof slot === 'object' && slot !== null ? slot.time_slot : slot;
                    const text = typeof slot === 'object' && slot !== null ? slot.time_slot : slot;
                    return (
                      <SelectItem key={key} value={value}>
                        {text}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              {!checkingSlots && availableSlots.length === 0 && formData.date && (
                <p className="text-xs text-destructive">Nenhum horário disponível</p>
              )}
            </div>
          </div>

          {/* Chat */}
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
            <div>
              <Label htmlFor="has_chat" className="text-sm font-medium text-foreground cursor-pointer">
                Cliente tem chat
              </Label>
              <p className="text-xs text-muted-foreground mt-1">Indica se o cliente está online no chat</p>
            </div>
            <Switch
              id="has_chat"
              checked={formData.has_chat}
              onCheckedChange={(checked) => setFormData({ ...formData, has_chat: checked })}
            />
          </div>

          {/* Observações */}
          <div className="space-y-2">
            <Label htmlFor="notes" className="text-sm font-medium text-foreground">Observações</Label>
            <Input
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Observações adicionais..."
              className="h-11"
            />
          </div>

          {/* Botões */}
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={onClose} className="px-6">
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={loading || !formData.new_protocol || !formData.time_slot}
              className="px-6"
              data-testid="recurring-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Criando...
                </>
              ) : (
                <>
                  <RepeatIcon className="w-4 h-4 mr-2" />
                  Criar Reagendamento
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
