import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { appointmentsAPI, usersAPI } from '../utils/api';
import { toast } from 'sonner';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Clock, User, FileText, MessageCircle, Search, Inbox } from 'lucide-react';

export const PendingAssignments = ({ isOpen, onClose, onAssigned }) => {
  const { user } = require('../context/AuthContext').useAuth();
  const [pendingAppointments, setPendingAppointments] = useState([]);
  const [attendants, setAttendants] = useState([]);
  const [selectedAttendant, setSelectedAttendant] = useState({});
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadData();
      setSearchTerm('');
    }
  }, [isOpen]);

  const loadData = async () => {
    try {
      const pendingRes = await appointmentsAPI.getPending();
      setPendingAppointments(pendingRes.data);
      if (user?.role === 'admin' || user?.role === 'supervisor') {
        try {
          const attendantsRes = await usersAPI.getAttendants();
          setAttendants(attendantsRes.data);
        } catch (e) {
          console.error('Erro ao carregar agentes:', e);
          setAttendants([]);
        }
      } else {
        setAttendants([]);
      }
    } catch (error) {
      toast.error('Erro ao carregar dados');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const filteredAppointments = useMemo(() => {
    if (!searchTerm) return pendingAppointments;
    const search = searchTerm.toLowerCase();
    return pendingAppointments.filter(apt => 
      apt.first_name?.toLowerCase().includes(search) ||
      apt.last_name?.toLowerCase().includes(search) ||
      apt.protocol_number?.toLowerCase().includes(search)
    );
  }, [pendingAppointments, searchTerm]);

  const handleAssign = async (appointmentId) => {
    const attendantId = selectedAttendant[appointmentId];
    if (!attendantId) {
      toast.error('Selecione um agente');
      return;
    }

    try {
      await appointmentsAPI.assign(appointmentId, attendantId);
      toast.success('Agendamento atribuído com sucesso!');
      await loadData();
      onAssigned();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao atribuir agendamento');
      console.error(error);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto" data-testid="pending-assignments-modal">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold tracking-tight">
            Agendamentos Pendentes de Atribuição
          </DialogTitle>
          <DialogDescription>
            Atribua os agendamentos criados pela equipe aos agentes disponíveis.
          </DialogDescription>
        </DialogHeader>

        {/* Busca em tempo real */}
        {!loading && pendingAppointments.length > 0 && (
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nome ou protocolo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
              data-testid="pending-search"
            />
          </div>
        )}

        {loading ? (
          <div className="py-8 space-y-3">
            <div className="h-16 bg-muted rounded-lg animate-pulse"></div>
            <div className="h-16 bg-muted rounded-lg animate-pulse"></div>
          </div>
        ) : pendingAppointments.length === 0 ? (
          <div className="py-12 text-center">
            <Inbox className="w-12 h-12 mx-auto text-muted-foreground/30 mb-3" />
            <p className="text-muted-foreground">Nenhum agendamento pendente de atribuição.</p>
            <p className="text-sm text-muted-foreground/70 mt-1">Todos os agendamentos foram atribuídos!</p>
          </div>
        ) : filteredAppointments.length === 0 ? (
          <div className="py-8 text-center text-muted-foreground">
            Nenhum resultado para "{searchTerm}"
          </div>
        ) : (
          <div className="space-y-4 mt-4">
            {filteredAppointments.map((apt) => {
              const clientName = `${apt.first_name} ${apt.last_name}`;
              const totalProtocols = 1 + (apt.additional_protocols?.length || 0);
              
              return (
                <div key={apt.id} className="border border-border rounded-lg p-4 bg-muted/50" data-testid={`pending-item-${apt.id}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-semibold text-foreground text-lg">{clientName}</h3>
                      <p className="text-sm text-muted-foreground mt-1">Protocolo: {apt.protocol_number}</p>
                      <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          <span>{format(parseISO(apt.date), "dd 'de' MMM", { locale: ptBR })} - {apt.time_slot}</span>
                        </div>
                        {totalProtocols > 1 && (
                          <span className="px-2 py-1 bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded text-xs font-medium">
                            {totalProtocols} protocolos
                          </span>
                        )}
                        {apt.document_urls?.length > 0 && (
                          <span className="flex items-center gap-1 text-xs text-muted-foreground">
                            <FileText className="w-3 h-3" /> {apt.document_urls.length} doc(s)
                          </span>
                        )}
                        {apt.has_chat && (
                          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                            <MessageCircle className="w-3 h-3" /> Chat
                          </span>
                        )}
                      </div>
                      {apt.notes && (
                        <p className="text-sm text-muted-foreground mt-2">
                          <span className="font-medium">Obs:</span> {apt.notes}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 min-w-[300px]">
                      <Select
                        value={selectedAttendant[apt.id] || ''}
                        onValueChange={(value) => setSelectedAttendant({ ...selectedAttendant, [apt.id]: value })}
                      >
                        <SelectTrigger data-testid={`assign-select-${apt.id}`}>
                          <SelectValue placeholder="Selecione o agente" />
                        </SelectTrigger>
                        <SelectContent>
                          {attendants.map(attendant => (
                            <SelectItem key={attendant.id} value={attendant.id}>
                              <div className="flex items-center gap-2">
                                <User className="w-4 h-4" />
                                {attendant.name}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button
                        onClick={() => handleAssign(apt.id)}
                        disabled={!selectedAttendant[apt.id]}
                        data-testid={`assign-button-${apt.id}`}
                      >
                        Atribuir
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex justify-end pt-4">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
