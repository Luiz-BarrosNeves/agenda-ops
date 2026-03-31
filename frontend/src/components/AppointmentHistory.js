import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { appointmentsAPI } from '../utils/api';
import { toast } from 'sonner';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { History, User, Clock, ArrowRight, FileText, RefreshCw, UserPlus, Loader2 } from 'lucide-react';

const actionLabels = {
  created: 'Criado',
  updated: 'Atualizado',
  status_changed: 'Status alterado',
  assigned: 'Atribuído',
  rescheduled: 'Reagendado',
};

const actionIcons = {
  created: FileText,
  updated: RefreshCw,
  status_changed: ArrowRight,
  assigned: UserPlus,
  rescheduled: Clock,
};

const actionColors = {
  created: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
  updated: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  status_changed: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  assigned: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  rescheduled: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
};

const fieldLabels = {
  status: 'Status',
  user_id: 'Agente',
  date: 'Data',
  time_slot: 'Horário',
  first_name: 'Nome',
  last_name: 'Sobrenome',
  protocol_number: 'Protocolo',
  notes: 'Observações',
  has_chat: 'Chat',
  recurring: 'Recorrência',
};

const statusLabels = {
  pendente_atribuicao: 'Pendente',
  confirmado: 'Confirmado',
  emitido: 'Emitido',
  reagendar: 'Reagendar',
  presencial: 'Presencial',
  cancelado: 'Cancelado',
};

export const AppointmentHistory = ({ isOpen, onClose, appointmentId }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen && appointmentId) {
      loadHistory();
    }
  }, [isOpen, appointmentId]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const response = await appointmentsAPI.getHistory(appointmentId);
      setHistory(response.data);
    } catch (error) {
      toast.error('Erro ao carregar histórico');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const formatValue = (field, value) => {
    if (!value) return '-';
    if (field === 'status') return statusLabels[value] || value;
    if (field === 'has_chat') return value === 'True' || value === 'true' ? 'Sim' : 'Não';
    if (field === 'date') {
      try {
        return format(parseISO(value), 'dd/MM/yyyy');
      } catch {
        return value;
      }
    }
    return value;
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto" data-testid="history-modal">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold tracking-tight flex items-center gap-2 text-foreground">
            <History className="w-5 h-5" />
            Histórico de Alterações
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Visualize todas as alterações feitas neste agendamento
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>Nenhuma alteração registrada</p>
          </div>
        ) : (
          <div className="space-y-4 mt-4">
            {history.map((entry, index) => {
              const Icon = actionIcons[entry.action] || RefreshCw;
              const colorClass = actionColors[entry.action] || 'bg-muted text-muted-foreground';
              
              return (
                <div 
                  key={entry.id} 
                  className="relative pl-8 pb-4 border-l-2 border-border last:border-l-0 last:pb-0"
                  data-testid={`history-entry-${index}`}
                >
                  {/* Ícone na linha do tempo */}
                  <div className={`absolute -left-3 p-1.5 rounded-full ${colorClass}`}>
                    <Icon className="w-3 h-3" />
                  </div>
                  
                  {/* Conteúdo */}
                  <div className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}>
                          {actionLabels[entry.action] || entry.action}
                        </span>
                        {entry.field_changed && (
                          <span className="ml-2 text-sm text-muted-foreground">
                            • {fieldLabels[entry.field_changed] || entry.field_changed}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">
                        {format(parseISO(entry.changed_at), "dd/MM/yy 'às' HH:mm", { locale: ptBR })}
                      </span>
                    </div>
                    
                    {/* Detalhes da alteração */}
                    {entry.old_value || entry.new_value ? (
                      <div className="flex items-center gap-2 text-sm mt-2">
                        {entry.old_value && (
                          <span className="px-2 py-1 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded line-through">
                            {formatValue(entry.field_changed, entry.old_value)}
                          </span>
                        )}
                        {entry.old_value && entry.new_value && (
                          <ArrowRight className="w-4 h-4 text-muted-foreground" />
                        )}
                        {entry.new_value && (
                          <span className="px-2 py-1 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded">
                            {formatValue(entry.field_changed, entry.new_value)}
                          </span>
                        )}
                      </div>
                    ) : null}
                    
                    {/* Quem alterou */}
                    <div className="flex items-center gap-1 mt-3 text-xs text-muted-foreground">
                      <User className="w-3 h-3" />
                      <span>Por {entry.changed_by_name}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex justify-end pt-4 border-t border-border mt-4">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
