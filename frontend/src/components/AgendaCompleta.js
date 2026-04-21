import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { DndContext, DragOverlay, useSensor, useSensors, PointerSensor, closestCenter } from '@dnd-kit/core';
import { useDraggable, useDroppable } from '@dnd-kit/core';
import { slotsAPI, usersAPI, appointmentsAPI } from '../utils/api';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { useAuth } from '../context/AuthContext';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Clock, User, Plus, ChevronLeft, ChevronRight, Calendar as CalendarIcon, GripVertical, AlertTriangle, History, RepeatIcon } from 'lucide-react';
import { AppointmentHistory } from './AppointmentHistory';
import { RecurringAppointmentModal } from './RecurringAppointmentModal';

// Cores de status modernizadas com gradientes sutis
const statusColors = {
  pendente_atribuicao: 'bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/40 dark:to-amber-900/20 border-amber-200 dark:border-amber-700/50 text-amber-700 dark:text-amber-300',
  confirmado: 'bg-gradient-to-br from-emerald-50 to-emerald-100 dark:from-emerald-900/40 dark:to-emerald-900/20 border-emerald-200 dark:border-emerald-700/50 text-emerald-700 dark:text-emerald-300',
  emitido: 'bg-gradient-to-br from-sky-50 to-sky-100 dark:from-sky-900/40 dark:to-sky-900/20 border-sky-200 dark:border-sky-700/50 text-sky-700 dark:text-sky-300',
  reagendar: 'bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/40 dark:to-orange-900/20 border-orange-200 dark:border-orange-700/50 text-orange-700 dark:text-orange-300',
  presencial: 'bg-gradient-to-br from-violet-50 to-violet-100 dark:from-violet-900/40 dark:to-violet-900/20 border-violet-200 dark:border-violet-700/50 text-violet-700 dark:text-violet-300',
  cancelado: 'bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-800/40 dark:to-slate-800/20 border-slate-200 dark:border-slate-700/50 text-slate-500 dark:text-slate-400 opacity-60',
};

// Cores dos pontos de status (para indicador circular)
const statusDotColors = {
  pendente_atribuicao: 'bg-amber-500',
  confirmado: 'bg-emerald-500',
  emitido: 'bg-sky-500',
  reagendar: 'bg-orange-500',
  presencial: 'bg-violet-500',
  cancelado: 'bg-slate-400',
};

const statusLabels = {
  pendente_atribuicao: 'Pendente',
  confirmado: 'Confirmado',
  emitido: 'Emitido',
  reagendar: 'Reagendar',
  presencial: 'Presencial',
  cancelado: 'Cancelado',
};

// Componente de agendamento arrastável - Design Moderno
const DraggableAppointment = ({ appointment, agents, onEdit, isDragging, onOpenHistory, onOpenRecurring, userRole }) => {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: appointment.id,
    data: { appointment }
  });

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
    zIndex: 1000,
  } : undefined;

  const getAgentName = (appointment) => {
    if (appointment?.agent_name) return appointment.agent_name;
    const agent = agents.find(a => a.id === appointment?.user_id);
    return agent?.name || 'Não atribuído';
  };

  const getAgentInitials = (appointment) => {
    const agentName =
      appointment?.agent_name ||
      agents.find(a => a.id === appointment?.user_id)?.name;

  if (!agentName) return '?';

  const names = agentName.split(' ');
  return names.length > 1
    ? `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase()
    : names[0][0].toUpperCase();
  };

  const canSeeActions = userRole === 'supervisor' || userRole === 'admin';
  
  // Badge de sistema de emissão
  const emissionBadge = appointment.emission_system ? (
    <span 
      className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wide ${
        appointment.emission_system === 'safeweb' 
          ? 'bg-cyan-500/20 text-cyan-600 dark:text-cyan-400' 
          : 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
      }`}
    >
      {appointment.emission_system}
    </span>
  ) : null;

  // Badge de plataforma de chat
  const chatBadge = appointment.has_chat && appointment.chat_platform ? (
    <span 
      className={`text-[9px] px-1.5 py-0.5 rounded-full font-semibold uppercase tracking-wide ${
        appointment.chat_platform === 'blip' 
          ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' 
          : 'bg-green-500/20 text-green-600 dark:text-green-400'
      }`}
    >
      {appointment.chat_platform}
    </span>
  ) : null;

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02, y: -2 }}
      className={`
        group relative p-3 rounded-xl border cursor-grab active:cursor-grabbing 
        transition-all duration-200 backdrop-blur-sm
        ${statusColors[appointment.status]} 
        ${isDragging ? 'opacity-50 scale-105 shadow-xl ring-2 ring-primary/50' : 'hover:shadow-lg hover:border-primary/30'}
      `}
      data-testid={`draggable-apt-${appointment.id}`}
    >
      {/* Indicador de status (bolinha colorida) */}
      <div className={`absolute top-3 right-3 w-2 h-2 rounded-full ${statusDotColors[appointment.status]} ring-2 ring-white dark:ring-slate-800`} />
      
      <div className="flex items-start gap-3">
        {/* Handle de drag */}
        <div
          {...attributes}
          {...listeners}
          className="flex-shrink-0 p-1.5 -ml-1 hover:bg-black/5 dark:hover:bg-white/5 rounded-lg cursor-grab opacity-40 group-hover:opacity-100 transition-opacity"
        >
          <GripVertical className="w-4 h-4" />
        </div>
        
        {/* Avatar do agente */}
        <div className="flex-shrink-0">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-xs font-bold text-primary border-2 border-white dark:border-slate-700 shadow-sm">
            {getAgentInitials(appointment)}
          </div>
        </div>
        
        {/* Conteúdo principal */}
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onEdit(appointment)}>
          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
            <p className="text-sm font-semibold truncate">
              {appointment.first_name} {appointment.last_name}
            </p>
            {chatBadge}
            {emissionBadge}
          </div>
          
          <p className="text-xs text-muted-foreground font-mono truncate mb-1">
            {appointment.protocol_number}
          </p>
          
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/60 dark:bg-black/20 font-medium">
              {statusLabels[appointment.status]}
            </span>
            <span className="text-[10px] text-muted-foreground truncate">
              {getAgentName(appointment)}
            </span>
          </div>
        </div>
      </div>
      
      {/* Botões de ação (aparecem no hover) */}
      {canSeeActions && (
        <div 
          className="absolute bottom-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => onOpenHistory(appointment.id)}
            className="p-1.5 rounded-lg bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700 shadow-sm transition-colors"
            title="Ver histórico"
            data-testid={`history-btn-${appointment.id}`}
          >
            <History className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={() => onOpenRecurring(appointment)}
            className="p-1.5 rounded-lg bg-white/80 dark:bg-slate-800/80 hover:bg-white dark:hover:bg-slate-700 shadow-sm transition-colors"
            title="Reagendar semanal"
            data-testid={`recurring-btn-${appointment.id}`}
          >
            <RepeatIcon className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
        </div>
      )}
    </motion.div>
  );
};

// Componente de slot que pode receber drop
const DroppableSlot = ({ slot, children, isOver }) => {
  const { setNodeRef } = useDroppable({
    id: `slot-${slot.time_slot}`,
    data: { slot }
  });

  return (
    <div
      ref={setNodeRef}
      className={`min-h-[60px] transition-all rounded-lg ${isOver ? 'bg-primary/10 ring-2 ring-primary/30' : ''}`}
    >
      {children}
    </div>
  );
};

export const AgendaCompleta = ({ 
  currentDate, 
  onDateChange, 
  onNewAppointment, 
  onEditAppointment,
  userRole,
  embedded = false,  // Quando true, remove o Card wrapper e navegação (já está no Dashboard)
  appointments // opcional: sobrescreve os agendamentos carregados internamente
}) => {
  const { user } = useAuth();
  const dateStr = format(currentDate, 'yyyy-MM-dd');
    // Permissão para solicitar alteração/cancelamento
    const canRequestChange = (apt) => {
      if (user?.role === 'supervisor' || user?.role === 'admin') return true;
      if (user?.role === 'agente') return apt?.user_id === user?.id;
      return apt?.created_by === user?.id;
    };
  const isToday = dateStr === format(new Date(), 'yyyy-MM-dd');
  const isAgent = userRole === 'agente';
  const isAdmin = userRole === 'admin';
  const isCreator = userRole === 'televendas' || userRole === 'comercial';
  const canCreate = isCreator || userRole === 'supervisor';
  const canDragDrop = userRole === 'supervisor' || userRole === 'admin';

  const [slotsData, setSlotsData] = useState(null);
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [activeId, setActiveId] = useState(null);
  const [overId, setOverId] = useState(null);
  const [pendingReschedule, setPendingReschedule] = useState(null); // Para confirmação de reagendamento
  const [slideDirection, setSlideDirection] = useState(0); // -1 = esquerda, 1 = direita
  
  // Estados para modais de histórico e reagendamento recorrente
  const [historyModalOpen, setHistoryModalOpen] = useState(false);
  const [historyAppointmentId, setHistoryAppointmentId] = useState(null);
  const [recurringModalOpen, setRecurringModalOpen] = useState(false);
  const [recurringAppointment, setRecurringAppointment] = useState(null);


  // Handlers para histórico e reagendamento
  const handleOpenHistory = (appointmentId) => {
    setHistoryAppointmentId(appointmentId);
    setHistoryModalOpen(true);
  };

  const handleOpenRecurring = (appointment) => {
    setRecurringAppointment(appointment);
    setRecurringModalOpen(true);
  };

  // Handler de edição/cancelamento com permissão
  const handleEditAppointment = (apt) => {
    if (!canRequestChange(apt)) {
      toast.error('Você só pode alterar/cancelar agendamentos atribuídos a você.');
      return;
    }
    if (typeof onEditAppointment === 'function') {
      onEditAppointment(apt);
    }
  };

  const handleRecurringSuccess = () => {
    loadData();
  };

  // Variantes de animação para transição de dias
  const slideVariants = {
    enter: (direction) => ({
      x: direction > 0 ? 100 : -100,
      opacity: 0
    }),
    center: {
      x: 0,
      opacity: 1
    },
    exit: (direction) => ({
      x: direction < 0 ? 100 : -100,
      opacity: 0
    })
  };

  const slideTransition = {
    x: { type: 'spring', stiffness: 300, damping: 30 },
    opacity: { duration: 0.2 }
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // Mínimo de pixels para iniciar drag
      },
    })
  );


  useEffect(() => {
    if (!appointments) {
      loadData();
    } else {
      setLoading(false);
      // Filtra agendamentos do agente logado
      let filteredAppointments = appointments;
      // Aplica filtro de agente ANTES do agrupamento
      if (userRole === 'agente' && user?.id) {
        filteredAppointments = appointments.filter(a => a.user_id === user.id);
      }
      // Agrupa apenas os agendamentos filtrados
      const grouped = filteredAppointments.reduce((acc, apt) => {
        if (!acc[apt.time_slot]) acc[apt.time_slot] = [];
        acc[apt.time_slot].push(apt);
        return acc;
      }, {});
      const slots = Object.entries(grouped).map(([time_slot, apps]) => ({
        time_slot,
        appointments: apps,
        available: 0, // Não sabemos a disponibilidade filtrada
        occupied: apps.length,
        pending: apps.filter(a => a.status === 'pendente_atribuicao').length,
        is_extra: false // Não sabemos se é extra
      }));
      // Aplica filtro final: agente só vê slots com agendamentos do próprio
      let finalSlots = slots;
      if (userRole === 'agente' && user?.id) {
        finalSlots = slots.filter(slot => slot.appointments.some(a => a.user_id === user.id));
      }
      setSlotsData({ slots: finalSlots });
    }
  }, [dateStr, appointments, userRole, user]);

  const loadData = async () => {
    setLoading(true);
    try {
      const slotsRes = await slotsAPI.getAll(dateStr);
      setSlotsData(slotsRes.data);
      // Só busca agentes se for admin ou supervisor
      if (user?.role === 'admin' || user?.role === 'supervisor') {
        try {
          const agentsRes = await usersAPI.getAttendants();
          setAgents(agentsRes.data);
        } catch (e) {
          console.error('Erro ao carregar agentes:', e);
          setAgents([]);
        }
      } else {
        setAgents([]);
      }
    } catch (error) {
      console.error('Erro ao carregar agenda:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = useCallback((event) => {
    setActiveId(event.active.id);
  }, []);

  const handleDragOver = useCallback((event) => {
    setOverId(event.over?.id || null);
  }, []);

  const handleDragEnd = useCallback(async (event) => {
    const { active, over } = event;
    setActiveId(null);
    setOverId(null);

    if (!over || !active) return;

    const appointment = active.data.current?.appointment;
    const targetSlotId = over.id;

    if (!appointment || !targetSlotId?.startsWith('slot-')) return;

    const newTimeSlot = targetSlotId.replace('slot-', '');
    
    // Se é o mesmo slot, não fazer nada
    if (appointment.time_slot === newTimeSlot) return;

    // Verificar se o slot de destino tem disponibilidade
    const targetSlot = slotsData?.slots?.find(s => s.time_slot === newTimeSlot);
    if (!targetSlot || targetSlot.available <= 0) {
      toast.error('Este horário não tem disponibilidade');
      return;
    }

    // Mostrar modal de confirmação
    setPendingReschedule({
      appointment,
      newTimeSlot,
      oldTimeSlot: appointment.time_slot
    });
  }, [slotsData]);

  // Função para confirmar o reagendamento
  const confirmReschedule = useCallback(async () => {
    if (!pendingReschedule) return;

    const { appointment, newTimeSlot } = pendingReschedule;

    // Otimistic update - atualizar localmente primeiro
    setSlotsData(prev => {
      if (!prev) return prev;
      
      const newSlots = prev.slots.map(slot => {
        // Remover do slot original
        if (slot.time_slot === appointment.time_slot) {
          return {
            ...slot,
            appointments: slot.appointments.filter(a => a.id !== appointment.id),
            occupied: slot.occupied - 1,
            available: slot.available + 1
          };
        }
        // Adicionar ao novo slot
        if (slot.time_slot === newTimeSlot) {
          return {
            ...slot,
            appointments: [...slot.appointments, { ...appointment, time_slot: newTimeSlot }],
            occupied: slot.occupied + 1,
            available: slot.available - 1
          };
        }
        return slot;
      });
      
      return { ...prev, slots: newSlots };
    });

    try {
      // Chamar API para persistir
      await appointmentsAPI.update(appointment.id, {
        date: dateStr,
        time_slot: newTimeSlot
      });
      
      toast.success(`Agendamento movido para ${newTimeSlot}`);
    } catch (error) {
      // Reverter em caso de erro
      toast.error('Erro ao mover agendamento');
      loadData(); // Recarregar dados originais
    } finally {
      setPendingReschedule(null);
    }
  }, [pendingReschedule, dateStr, loadData]);

  // Função para cancelar o reagendamento
  const cancelReschedule = useCallback(() => {
    setPendingReschedule(null);
  }, []);

  const handleDragCancel = useCallback(() => {
    setActiveId(null);
    setOverId(null);
  }, []);

  const handlePrevDay = () => {
    setSlideDirection(-1);
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 1);
    onDateChange(newDate);
  };

  const handleNextDay = () => {
    setSlideDirection(1);
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 1);
    onDateChange(newDate);
  };

  const handleToday = () => {
    const today = new Date();
    const todayStr = format(today, 'yyyy-MM-dd');
    setSlideDirection(todayStr > dateStr ? 1 : todayStr < dateStr ? -1 : 0);
    onDateChange(today);
  };

  const handleNewAtSlot = (slot) => {
    if (canCreate) {
      onNewAppointment({
        date: dateStr,
        time_slot: slot.time_slot
      });
    } else if (isAgent || isAdmin) {
      toast("Seu perfil não tem permissão para criar agendamentos");
    }
  };

  const activeAppointment = useMemo(() => {
    if (!activeId || !slotsData) return null;
    for (const slot of slotsData.slots) {
      const apt = slot.appointments?.find(a => a.id === activeId);
      if (apt) return apt;
    }
    return null;
  }, [activeId, slotsData]);

  const filteredSlots = slotsData?.slots || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="space-y-3 w-full max-w-md">
          <div className="h-4 bg-muted rounded animate-pulse"></div>
          <div className="h-4 bg-muted rounded animate-pulse w-3/4"></div>
          <div className="h-4 bg-muted rounded animate-pulse w-1/2"></div>
        </div>
      </div>
    );
  }

  const getAgentName = (userId, agentName = null) => {
    if (agentName) return agentName;
    const agent = agents.find(a => a.id === userId);
    return agent?.name || 'Não atribuído';
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      {embedded ? (
        // Modo embedded - sem Card, sem navegação (já está no Dashboard)
        <div className="space-y-4">
          {/* Header elegante com filtro */}
          <div className="flex items-center justify-between flex-wrap gap-4 pb-4 border-b border-border/50">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-1 rounded-full bg-gradient-to-b from-primary to-primary/30" />
                <div>
                  <p className="text-base font-semibold text-foreground capitalize">
                    {format(currentDate, "EEEE, dd 'de' MMMM", { locale: ptBR })}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-muted-foreground">
                      {slotsData?.total_agents || 0} agentes
                    </span>
                    <span className="w-1 h-1 rounded-full bg-muted-foreground/30" />
                    <span className="text-xs text-muted-foreground">
                      {filteredSlots.length} horários
                    </span>
                  </div>
                </div>
              </div>
              {canDragDrop && (
                <span className="text-xs text-primary bg-primary/10 px-3 py-1.5 rounded-full font-medium flex items-center gap-1.5">
                  <GripVertical className="w-3 h-3" />
                  Arraste para remarcar
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Filtrar por agente:</span>
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="text-sm border border-border bg-background rounded-lg px-3 py-2 focus:ring-2 focus:ring-primary/20 focus:border-primary/30 transition-all"
                data-testid="agent-filter"
              >
                <option value="all">Todos os agentes</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Slots com Timeline Visual */}
          <AnimatePresence mode="wait" custom={slideDirection}>
            <motion.div 
              key={dateStr}
              custom={slideDirection}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={slideTransition}
              className="relative"
            >
              {filteredSlots.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted/50 flex items-center justify-center">
                    <CalendarIcon className="w-8 h-8 text-muted-foreground/50" />
                  </div>
                  <p className="text-muted-foreground font-medium">Nenhum horário disponível</p>
                  <p className="text-sm text-muted-foreground/70 mt-1">Tente selecionar outra data</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredSlots.map((slot, index) => {
                    const isCurrentSlot = slot.is_current;
                    const isPast = slot.is_past;
                    const isOverSlot = overId === `slot-${slot.time_slot}`;
                    const hasAppointments = slot.appointments?.length > 0;
                    
                    const visibleAppointments = selectedAgent === 'all' 
                      ? slot.appointments 
                      : slot.appointments?.filter(a => a.user_id === selectedAgent);

                    return (
                      <motion.div
                        key={slot.time_slot}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.02, duration: 0.2 }}
                      >
                        <DroppableSlot 
                          slot={slot}
                          isOver={isOverSlot && canDragDrop}
                        >
                          <div className={`
                            rounded-xl border transition-all duration-300
                            ${isCurrentSlot 
                              ? 'border-primary bg-primary/5 ring-2 ring-primary/20' 
                              : isPast 
                                ? 'border-border/50 bg-muted/30 opacity-60' 
                                : isOverSlot && canDragDrop
                                  ? 'border-primary/50 bg-primary/5 ring-2 ring-primary/20'
                                  : 'border-border bg-card hover:bg-accent/40 hover:shadow-sm hover:border-border'
                            }
                          `}>
                            {/* Header do slot - horário e disponibilidade */}
                            <div className="flex items-center justify-between px-4 py-3 border-b border-border/50">
                              <div className="flex items-center gap-4">
                                {/* Horário com indicador */}
                                <div className="flex items-center gap-2">
                                  <div className={`
                                    w-3 h-3 rounded-full transition-all
                                    ${isCurrentSlot 
                                      ? 'bg-primary shadow-lg shadow-primary/50 animate-pulse' 
                                      : hasAppointments 
                                        ? 'bg-emerald-500' 
                                        : 'bg-border'
                                    }
                                  `} />
                                  <span className={`
                                    text-base font-semibold font-mono
                                    ${isCurrentSlot ? 'text-primary' : isPast ? 'text-muted-foreground' : 'text-foreground'}
                                  `}>
                                    {slot.time_slot}
                                  </span>
                                  {isCurrentSlot && (
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary text-primary-foreground font-bold uppercase">
                                      Agora
                                    </span>
                                  )}
                                  {slot.is_extra && (
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-600 dark:text-orange-400 font-semibold">
                                      Extra
                                    </span>
                                  )}
                                </div>
                                
                                {/* Badge de disponibilidade */}
                                <div className={`
                                  flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium
                                  ${slot.available === 0 
                                    ? 'bg-red-500/10 text-red-600 dark:text-red-400' 
                                    : slot.available <= 2
                                      ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                                      : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                  }
                                `}>
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    slot.available === 0 ? 'bg-red-500' : slot.available <= 2 ? 'bg-amber-500' : 'bg-emerald-500'
                                  }`} />
                                  {slot.available === 0 
                                    ? 'Lotado' 
                                    : `${slot.available} vaga${slot.available > 1 ? 's' : ''}`
                                  }
                                </div>
                                
                                {visibleAppointments?.length > 0 && (
                                  <span className="text-xs text-muted-foreground">
                                    {visibleAppointments.length} agendamento{visibleAppointments.length > 1 ? 's' : ''}
                                  </span>
                                )}
                              </div>
                              
                              {/* Botão de novo agendamento */}
                              {slot.available > 0 && !isPast && canCreate && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 px-3 text-xs hover:bg-primary/10 hover:text-primary"
                                  onClick={() => onNewAppointment({ date: dateStr, time_slot: slot.time_slot })}
                                  data-testid={`new-appointment-${slot.time_slot}`}
                                >
                                  <Plus className="w-3.5 h-3.5 mr-1" />
                                  Agendar
                                </Button>
                              )}
                            </div>
                            
                            {/* Agendamentos */}
                            {visibleAppointments?.length > 0 && (
                              <div className="p-3">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                  {visibleAppointments.map((apt) => 
                                    canDragDrop ? (
                                      <DraggableAppointment
                                        key={apt.id}
                                        appointment={apt}
                                        agents={agents}
                                        onEdit={handleEditAppointment}
                                        isDragging={activeId === apt.id}
                                        onOpenHistory={handleOpenHistory}
                                        onOpenRecurring={handleOpenRecurring}
                                        userRole={userRole}
                                      />
                                    ) : (
                                      <motion.div
                                        key={apt.id}
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        whileHover={{ scale: 1.02, y: -2 }}
                                        onClick={() => handleEditAppointment(apt)}
                                        className={`
                                          group relative p-3 rounded-xl border cursor-pointer 
                                          transition-all duration-200 backdrop-blur-sm hover:shadow-lg
                                          ${statusColors[apt.status]}
                                        `}
                                        data-testid={`appointment-${apt.id}`}
                                      >
                                        <div className={`absolute top-3 right-3 w-2 h-2 rounded-full ${statusDotColors[apt.status]} ring-2 ring-white dark:ring-slate-800`} />
                                        <div className="flex items-start gap-3">
                                          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-xs font-bold text-primary border-2 border-white dark:border-slate-700 shadow-sm">
                                            {apt.agent_name
                                              ? apt.agent_name.split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase()
                                              : (apt.user_id ? getAgentName(apt.user_id).split(' ').map(n => n[0]).slice(0, 2).join('').toUpperCase() : '?')}
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold truncate">
                                              {apt.first_name} {apt.last_name}
                                            </p>
                                            <p className="text-xs text-muted-foreground font-mono truncate mb-1">
                                              {apt.protocol_number}
                                            </p>
                                            <div className="flex items-center gap-2">
                                              <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/60 dark:bg-black/20 font-medium">
                                                {statusLabels[apt.status]}
                                              </span>
                                              <span className="text-[10px] text-muted-foreground truncate">
                                                {apt.agent_name ? apt.agent_name : (!apt.user_id ? 'Não atribuído' : apt.user_id)}
                                              </span>
                                            </div>
                                          </div>
                                        </div>
                                      </motion.div>
                                    )
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        </DroppableSlot>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </motion.div>
          </AnimatePresence>

          {/* Modal de confirmação de reagendamento */}
          <AlertDialog open={!!pendingReschedule} onOpenChange={(open) => !open && cancelReschedule()}>
            <AlertDialogContent data-testid="reschedule-confirm-modal">
              <AlertDialogHeader>
                <AlertDialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-500" />
                  Confirmar Reagendamento
                </AlertDialogTitle>
                <AlertDialogDescription asChild>
                  <div className="space-y-3">
                    <p>Você está prestes a reagendar o seguinte atendimento:</p>
                    {pendingReschedule && (
                      <div className="bg-card p-3 rounded-lg border border-border">
                        <p className="font-medium text-foreground">
                          {pendingReschedule.appointment.first_name} {pendingReschedule.appointment.last_name}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Protocolo: {pendingReschedule.appointment.protocol_number}
                        </p>
                        <div className="mt-2 flex items-center gap-2 text-sm">
                          <span className="text-muted-foreground">De:</span>
                          <span className="font-medium text-red-600 dark:text-red-400">{pendingReschedule.oldTimeSlot}</span>
                          <span className="text-muted-foreground">→</span>
                          <span className="font-medium text-green-600 dark:text-green-400">{pendingReschedule.newTimeSlot}</span>
                        </div>
                      </div>
                    )}
                    <p className="text-amber-600 dark:text-amber-400 text-sm">
                      Tem certeza que deseja alterar o horário deste agendamento?
                    </p>
                  </div>
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel data-testid="reschedule-cancel-btn">
                  Cancelar
                </AlertDialogCancel>
                <AlertDialogAction 
                  onClick={confirmReschedule}
                  className="bg-primary hover:bg-primary/90"
                  data-testid="reschedule-confirm-btn"
                >
                  Sim, Reagendar
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      ) : (
      // Modo standalone - com Card e navegação completa
      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-4">
                <CardTitle className="text-lg font-semibold flex items-center gap-2">
                  <CalendarIcon className="w-5 h-5 text-primary" />
                  Agenda Completa
                </CardTitle>
                
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handlePrevDay} data-testid="prev-day">
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant={isToday ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={handleToday}
                    className="min-w-[80px]"
                    data-testid="today-btn"
                  >
                    Hoje
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleNextDay} data-testid="next-day">
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Filtrar:</span>
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="text-sm border border-border bg-background rounded-md px-2 py-1 focus:ring-2 focus:ring-primary/20"
                  data-testid="agent-filter"
                >
                  <option value="all">Todos os agentes</option>
                  {agents.map(agent => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-3 p-3 bg-muted/50 rounded-lg border border-border">
              <p className="text-lg font-semibold text-foreground">
                {format(currentDate, "EEEE, dd 'de' MMMM 'de' yyyy", { locale: ptBR })}
              </p>
              <div className="flex items-center gap-4 mt-1">
                <p className="text-sm text-muted-foreground">
                  {slotsData?.total_agents || 0} agentes • {filteredSlots.length} horários
                </p>
                {canDragDrop && (
                  <p className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded">
                    Arraste para remarcar
                  </p>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="pt-0">
            <AnimatePresence mode="wait" custom={slideDirection}>
              <motion.div 
                key={dateStr}
                custom={slideDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={slideTransition}
                className="space-y-2"
              >
              {filteredSlots.length === 0 ? (
                <div className="text-center py-12">
                  <CalendarIcon className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
                  <p className="text-muted-foreground">Nenhum horário disponível para esta data.</p>
                </div>
              ) : (
                filteredSlots.map((slot, index) => {
                  const isCurrentSlot = slot.is_current;
                  const isPast = slot.is_past;
                  const isOverSlot = overId === `slot-${slot.time_slot}`;
                  
                  const visibleAppointments = selectedAgent === 'all' 
                    ? slot.appointments 
                    : slot.appointments?.filter(a => a.user_id === selectedAgent);

                  return (
                    <motion.div
                      key={slot.time_slot}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.02, duration: 0.2 }}
                    >
                    <DroppableSlot 
                      slot={slot}
                      isOver={isOverSlot && canDragDrop}
                    >
                      <div
                        className={`border rounded-lg p-3 transition-all ${
                          isCurrentSlot 
                            ? 'border-primary bg-primary/5 ring-2 ring-primary/20' 
                            : isPast 
                              ? 'border-border bg-muted/50 opacity-60' 
                              : 'border-border hover:border-primary/30'
                        } ${slot.is_extra ? 'border-l-4 border-l-amber-400' : ''}`}
                        data-testid={`slot-${slot.time_slot}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`flex items-center gap-1.5 ${isCurrentSlot ? 'text-primary font-bold' : 'text-foreground'}`}>
                              <Clock className="w-4 h-4" />
                              <span className="text-sm font-medium">{slot.time_slot}</span>
                              {isCurrentSlot && (
                                <span className="text-xs bg-primary text-white px-1.5 py-0.5 rounded ml-1 animate-pulse">
                                  AGORA
                                </span>
                              )}
                              {slot.is_extra && (
                                <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded ml-1">
                                  EXTRA
                                </span>
                              )}
                            </div>
                            
                            <div className="text-xs text-muted-foreground">
                              {slot.available > 0 ? (
                                <span className="text-green-600">{slot.available} disponível(is)</span>
                              ) : (
                                <span className="text-red-500">Lotado</span>
                              )}
                              {slot.pending > 0 && (
                                <span className="ml-2 text-yellow-600">• {slot.pending} pendente(s)</span>
                              )}
                            </div>
                          </div>

                          {!isPast && slot.available > 0 && (
                            <Button 
                              size="sm" 
                              variant="outline"
                              onClick={() => handleNewAtSlot(slot)}
                              className="h-7 text-xs"
                              data-testid={`new-at-${slot.time_slot}`}
                            >
                              <Plus className="w-3 h-3 mr-1" />
                              Novo
                            </Button>
                          )}
                        </div>

                        {visibleAppointments?.length > 0 && (
                          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2">
                            {visibleAppointments.map((apt) => (
                              canDragDrop && !isPast ? (
                                <DraggableAppointment
                                  key={apt.id}
                                  appointment={apt}
                                  agents={agents}
                                  onEdit={handleEditAppointment}
                                  isDragging={activeId === apt.id}
                                  onOpenHistory={handleOpenHistory}
                                  onOpenRecurring={handleOpenRecurring}
                                  userRole={userRole}
                                />
                              ) : (
                                <div
                                  key={apt.id}
                                  onClick={() => handleEditAppointment(apt)}
                                  className={`p-2 rounded border cursor-pointer hover:shadow-sm transition-shadow ${statusColors[apt.status]}`}
                                  data-testid={`appointment-${apt.id}`}
                                >
                                  <div className="flex items-start justify-between">
                                    <div className="min-w-0 flex-1">
                                      <p className="text-sm font-medium truncate">
                                        {apt.first_name} {apt.last_name}
                                      </p>
                                      <p className="text-xs opacity-75 truncate">{apt.protocol_number}</p>
                                      <div className="flex items-center gap-1 mt-1 text-xs opacity-75">
                                        <User className="w-3 h-3" />
                                        <span className="truncate">{getAgentName(apt.user_id, apt.agent_name)}</span>
                                      </div>
                                    </div>
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/50 whitespace-nowrap">
                                      {statusLabels[apt.status]}
                                    </span>
                                  </div>
                                </div>
                              )
                            ))}
                          </div>
                        )}
                      </div>
                    </DroppableSlot>
                    </motion.div>
                  );
                })
              )}
              </motion.div>
            </AnimatePresence>
          </CardContent>
        </Card>
      </div>
      )}

      {/* Overlay do item sendo arrastado */}
      <DragOverlay>
        {activeAppointment && (
          <div className={`p-2 rounded border shadow-xl ${statusColors[activeAppointment.status]} cursor-grabbing transform scale-105`}>
            <div className="flex items-start gap-2">
              <GripVertical className="w-3 h-3 opacity-50 flex-shrink-0 mt-1" />
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {activeAppointment.first_name} {activeAppointment.last_name}
                </p>
                <p className="text-xs opacity-75">{activeAppointment.protocol_number}</p>
              </div>
            </div>
          </div>
        )}
      </DragOverlay>

      {/* Modal de confirmação de reagendamento - para modo standalone */}
      {!embedded && (
        <AlertDialog open={!!pendingReschedule} onOpenChange={(open) => !open && cancelReschedule()}>
          <AlertDialogContent data-testid="reschedule-confirm-modal">
            <AlertDialogHeader>
              <AlertDialogTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                Confirmar Reagendamento
              </AlertDialogTitle>
              <AlertDialogDescription asChild>
                <div className="space-y-3">
                  <p>Você está prestes a reagendar o seguinte atendimento:</p>
                  {pendingReschedule && (
                    <div className="bg-card p-3 rounded-lg border border-border">
                      <p className="font-medium text-foreground">
                        {pendingReschedule.appointment.first_name} {pendingReschedule.appointment.last_name}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Protocolo: {pendingReschedule.appointment.protocol_number}
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-sm">
                        <span className="text-muted-foreground">De:</span>
                        <span className="font-medium text-red-600 dark:text-red-400">{pendingReschedule.oldTimeSlot}</span>
                        <span className="text-muted-foreground">→</span>
                        <span className="font-medium text-green-600 dark:text-green-400">{pendingReschedule.newTimeSlot}</span>
                      </div>
                    </div>
                  )}
                  <p className="text-amber-600 text-sm">
                    Tem certeza que deseja alterar o horário deste agendamento?
                  </p>
                </div>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel data-testid="reschedule-cancel-btn">
                Cancelar
              </AlertDialogCancel>
              <AlertDialogAction 
                onClick={confirmReschedule}
                className="bg-primary hover:bg-primary/90"
                data-testid="reschedule-confirm-btn"
              >
                Sim, Reagendar
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {/* Modal de Histórico */}
      <AppointmentHistory
        isOpen={historyModalOpen}
        onClose={() => setHistoryModalOpen(false)}
        appointmentId={historyAppointmentId}
      />

      {/* Modal de Reagendamento Recorrente */}
      <RecurringAppointmentModal
        isOpen={recurringModalOpen}
        onClose={() => setRecurringModalOpen(false)}
        originalAppointment={recurringAppointment}
        onSuccess={handleRecurringSuccess}
      />
    </DndContext>
  );
};
