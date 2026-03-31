import React, { useState, useEffect, useCallback } from 'react';
import { format, parseISO, addDays, subDays } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calendar, Clock, User, FileText, ChevronLeft, ChevronRight,
  Edit, X, AlertTriangle, Loader2, Search, RefreshCw, Plus
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { AppointmentModal } from './AppointmentModal';
import { useAuth } from '../context/AuthContext';
import { appointmentsAPI } from '../utils/api';
import { toast } from 'sonner';

// Status labels e cores
const statusConfig = {
  pendente_atribuicao: { 
    label: 'Pendente', 
    color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800' 
  },
  confirmado: { 
    label: 'Confirmado', 
    color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800' 
  },
  emitido: { 
    label: 'Emitido', 
    color: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-800' 
  },
  reagendar: { 
    label: 'Reagendar', 
    color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800' 
  },
  presencial: { 
    label: 'Presencial', 
    color: 'bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-200 dark:border-violet-800' 
  },
  cancelado: { 
    label: 'Cancelado', 
    color: 'bg-muted text-muted-foreground border-border opacity-60' 
  },
};

// Componente de Card de Agendamento
const AppointmentCard = ({ appointment, onEdit, onCancel, userRole }) => {
  const status = statusConfig[appointment.status] || statusConfig.pendente_atribuicao;
  const isEmitido = appointment.status === 'emitido';
  const isCancelado = appointment.status === 'cancelado';
  const hasPendingRequest = appointment.has_pending_request;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`
        relative p-4 rounded-xl border transition-all duration-200
        ${status.color}
        ${hasPendingRequest ? 'ring-2 ring-amber-400/50' : ''}
        hover:shadow-md
      `}
    >
      {/* Badge de solicitação pendente */}
      {hasPendingRequest && (
        <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-amber-500 text-white text-[10px] font-bold rounded-full">
          Aguardando aprovação
        </div>
      )}
      
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-foreground">
            {appointment.first_name} {appointment.last_name}
          </h3>
          <p className="text-xs text-muted-foreground font-mono mt-0.5">
            {appointment.protocol_number}
          </p>
        </div>
        <span className={`text-[10px] px-2 py-1 rounded-full font-medium border ${status.color}`}>
          {status.label}
        </span>
      </div>
      
      {/* Info */}
      <div className="space-y-2 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="w-4 h-4" />
          <span>{format(parseISO(appointment.date), "dd 'de' MMM, yyyy", { locale: ptBR })}</span>
          <Clock className="w-4 h-4 ml-2" />
          <span>{appointment.time_slot}</span>
        </div>
        
        <div className="flex items-center gap-2 text-muted-foreground">
          <User className="w-4 h-4" />
          <span>Agente: {appointment.agent_name ? appointment.agent_name : (!appointment.user_id ? 'Não atribuído' : appointment.user_id)}</span>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          {appointment.has_chat && appointment.chat_platform && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              appointment.chat_platform === 'blip' 
                ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' 
                : 'bg-green-500/20 text-green-600 dark:text-green-400'
            }`}>
              {appointment.chat_platform.toUpperCase()}
            </span>
          )}
          {appointment.emission_system && (
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
              appointment.emission_system === 'safeweb'
                ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400'
                : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
            }`}>
              {appointment.emission_system.toUpperCase()}
            </span>
          )}
        </div>
        
        {appointment.notes && (
          <div className="flex items-start gap-2 text-muted-foreground">
            <FileText className="w-4 h-4 mt-0.5" />
            <span className="text-xs line-clamp-2">{appointment.notes}</span>
          </div>
        )}
      </div>
      
      {/* Actions */}
      {!isEmitido && !isCancelado && !hasPendingRequest && (
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/50">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onEdit(appointment)}
            className="flex-1 h-8 text-xs"
            data-testid={`edit-apt-${appointment.id}`}
          >
            <Edit className="w-3 h-3 mr-1" />
            Editar
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onCancel(appointment)}
            className="flex-1 h-8 text-xs text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
            data-testid={`cancel-apt-${appointment.id}`}
          >
            <X className="w-3 h-3 mr-1" />
            Cancelar
          </Button>
        </div>
      )}
      
      {/* Info de status bloqueado */}
      {(isEmitido || isCancelado) && (
        <div className="mt-4 pt-3 border-t border-border/50">
          <p className="text-xs text-muted-foreground text-center">
            {isEmitido ? 'Agendamento emitido - não pode ser alterado' : 'Agendamento cancelado'}
          </p>
        </div>
      )}
    </motion.div>
  );
};



// Componente Principal
export const MyAppointments = () => {
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [stats, setStats] = useState({ total: 0, today: 0, pending: 0, emitidos: 0, pending_requests: 0 });
  const [loading, setLoading] = useState(true);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  

  // Modal state para edição
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [modalInitialData, setModalInitialData] = useState(null);
  
  const dateStr = format(currentDate, 'yyyy-MM-dd');
  
  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [appointmentsRes, statsRes] = await Promise.all([
        appointmentsAPI.getMyAppointments(dateStr),
        appointmentsAPI.getMyAppointmentsStats()
      ]);
      setAppointments(appointmentsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Erro ao carregar agendamentos');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [dateStr]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  // Handlers
  const handlePrevDay = () => setCurrentDate(prev => subDays(prev, 1));
  const handleNextDay = () => setCurrentDate(prev => addDays(prev, 1));
  const handleToday = () => setCurrentDate(new Date());
  

  // Ao clicar em Editar, abre o AppointmentModal
  const handleEdit = (appointment) => {
    setSelectedAppointment(appointment);
    setModalInitialData(null);
    setIsModalOpen(true);
  };

  // Ao clicar em Cancelar, cria uma solicitação de cancelamento
  const handleCancel = async (appointment) => {
    try {
      await appointmentsAPI.createChangeRequest({
        appointment_id: appointment.id,
        request_type: 'cancel',
        reason: 'Solicitação de cancelamento via painel',
      });
      toast.info('Solicitação de cancelamento enviada para aprovação do supervisor');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao solicitar cancelamento');
    }
  };

  // Lógica para submissão customizada do modal (apenas para não-supervisor)
  const handleSubmitOverride = async (formData, ctx) => {
    if (!selectedAppointment) return;
    // Se for cancelamento, envie apenas os campos necessários
    if (ctx?.requestType === 'cancel') {
      try {
        await appointmentsAPI.createChangeRequest({
          appointment_id: selectedAppointment.id,
          request_type: 'cancel',
          reason: formData.reason || 'Solicitação de cancelamento via painel',
        });
        toast.info('Solicitação de cancelamento enviada para aprovação do supervisor');
        setModalOpen(false);
        fetchData();
      } catch (error) {
        toast.error(error.response?.data?.detail || 'Erro ao solicitar cancelamento');
      }
      return;
    }
    // Edição normal
    try {
      await appointmentsAPI.createChangeRequest({
        appointment_id: selectedAppointment.id,
        request_type: 'edit',
        new_first_name: formData.first_name,
        new_last_name: formData.last_name,
        new_protocol_number: formData.protocol_number,
        new_additional_protocols: formData.additional_protocols,
        new_date: formData.date,
        new_time_slot: formData.time_slot,
        new_notes: formData.notes,
        reason: formData.reason || 'Solicitação de alteração via painel',
      });
      toast.info('Solicitação de alteração enviada para aprovação do supervisor');
      setModalOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao solicitar alteração');
    }
  };
  
  // Filter appointments
  const filteredAppointments = appointments.filter(apt => {
    const matchesSearch = searchTerm === '' || 
      apt.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      apt.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      apt.protocol_number.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'all' || apt.status === statusFilter;
    
    return matchesSearch && matchesStatus;
  });
  
  // Role label
  const getRoleDescription = () => {
    if (user?.role === 'agente') return 'Agendamentos atribuídos a você';
    if (user?.role === 'televendas') return 'Agendamentos criados por você';
    return 'Seus agendamentos (criados ou atribuídos)';
  };
  
  return (
    <div className="space-y-6" data-testid="my-appointments">
      {/* Header com stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-foreground">{stats.total}</div>
            <p className="text-xs text-muted-foreground">Total de Agendamentos</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-primary">{stats.today}</div>
            <p className="text-xs text-muted-foreground">Hoje</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-amber-500">{stats.pending}</div>
            <p className="text-xs text-muted-foreground">Pendentes</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-emerald-500">{stats.emitidos}</div>
            <p className="text-xs text-muted-foreground">Emitidos</p>
          </CardContent>
        </Card>
      </div>
      
      {/* Solicitações pendentes (apenas supervisor) */}
      {user?.role === 'supervisor' && stats.pending_requests > 0 && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <p className="font-medium text-foreground">{stats.pending_requests} solicitação(ões) pendente(s)</p>
                  <p className="text-xs text-muted-foreground">Aguardando sua aprovação</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Card principal */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Meus Agendamentos
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">{getRoleDescription()}</p>
            </div>
            
            {/* Navegação de data */}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={handlePrevDay} data-testid="my-apt-prev-day">
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <div className="px-4 py-2 bg-muted rounded-lg min-w-[180px] text-center">
                <span className="font-medium text-foreground">
                  {format(currentDate, "dd 'de' MMM, yyyy", { locale: ptBR })}
                </span>
              </div>
              <Button variant="outline" size="icon" onClick={handleNextDay} data-testid="my-apt-next-day">
                <ChevronRight className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={handleToday}>
                Hoje
              </Button>
              <Button variant="ghost" size="icon" onClick={fetchData} title="Atualizar">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {/* Filtros */}
          <div className="flex items-center gap-3 mt-4 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por nome ou protocolo..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9"
                data-testid="my-apt-search"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-10 px-3 rounded-lg border border-border bg-background text-sm focus:ring-2 focus:ring-primary/20"
              data-testid="my-apt-status-filter"
            >
              <option value="all">Todos os status</option>
              <option value="pendente_atribuicao">Pendentes</option>
              <option value="confirmado">Confirmados</option>
              <option value="emitido">Emitidos</option>
              <option value="reagendar">Reagendar</option>
              <option value="cancelado">Cancelados</option>
            </select>
          </div>
        </CardHeader>
        
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : filteredAppointments.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="w-12 h-12 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-muted-foreground">
                {searchTerm || statusFilter !== 'all' 
                  ? 'Nenhum agendamento encontrado com os filtros aplicados'
                  : 'Nenhum agendamento para esta data'
                }
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence mode="popLayout">
                {filteredAppointments.map(apt => (
                  <AppointmentCard
                    key={apt.id}
                    appointment={apt}
                    onEdit={handleEdit}
                    onCancel={handleCancel}
                    userRole={user?.role}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Modal de edição/cancelamento (unificado) */}
      <AppointmentModal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); setModalInitialData(null); }}
        appointment={selectedAppointment}
        initialData={modalInitialData}
        user={user}
        userRole={user?.role}
        onSave={fetchData}
        onSubmitOverride={
          user?.role === 'supervisor'
            ? undefined
            : async (formData, ctx) => {
                if (!ctx?.appointment) {
                  toast.error('Agendamento não encontrado');
                  throw new Error('Agendamento não encontrado');
                }
                // Só permite reagendar agendamentos do próprio agente
                if (ctx.appointment.user_id !== ctx.user.id) {
                  toast.error('Você só pode reagendar agendamentos atribuídos a você.');
                  return;
                }
                // Se status for reagendar, aplica regras
                if (ctx.statusData.status === 'reagendar') {
                  await appointmentsAPI.update(ctx.appointment.id, {
                    date: formData.date,
                    time_slot: formData.time_slot,
                    status: 'pendente_atribuicao',
                    user_id: null,
                    reschedule_reason: formData.reschedule_reason || ctx.rescheduleReason,
                    history: {
                      previous_date: ctx.appointment.date,
                      previous_time_slot: ctx.appointment.time_slot,
                      new_date: formData.date,
                      new_time_slot: formData.time_slot,
                      changed_by: ctx.user.id,
                      reason: formData.reschedule_reason || ctx.rescheduleReason
                    }
                  });
                  toast.success('Agendamento reagendado e pendente de atribuição!');
                  setIsModalOpen(false);
                  fetchData();
                  return;
                }
                // Edição normal
                await appointmentsAPI.createChangeRequest({
                  appointment_id: ctx.appointment.id,
                  request_type: 'edit',
                  reason: formData.reason || 'Solicitação de alteração via painel',
                  new_first_name: formData.first_name,
                  new_last_name: formData.last_name,
                  new_protocol_number: formData.protocol_number,
                  new_additional_protocols: formData.additional_protocols,
                  new_date: formData.date,
                  new_time_slot: formData.time_slot,
                  new_notes: formData.notes,
                });
              }
        }
      />
    </div>
  );
};

export default MyAppointments;
