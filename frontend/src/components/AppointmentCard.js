import React from 'react';
import { MoreVertical, FileText, MessageCircle } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from './ui/dropdown-menu';

const statusColors = {
  pendente_atribuicao: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  confirmado: 'bg-green-100 text-green-800 border-green-300',
  emitido: 'bg-blue-100 text-blue-800 border-blue-300',
  reagendar: 'bg-orange-100 text-orange-800 border-orange-300',
  presencial: 'bg-purple-100 text-purple-800 border-purple-300',
  cancelado: 'bg-slate-100 text-slate-600 border-slate-300',
};

const statusLabels = {
  pendente_atribuicao: 'Pendente',
  confirmado: 'Confirmado',
  emitido: 'Emitido',
  reagendar: 'Reagendar',
  presencial: 'Presencial',
  cancelado: 'Cancelado',
};

export const AppointmentCard = ({ appointment, onEdit, compact = false }) => {
    // Busca nome do agente igual à visão do supervisor
    const getAgentName = (userId) => {
      if (!userId) return 'Sem agente';
      // Se vier agent_name ou assigned_agent_name, prioriza
      if (appointment.agent_name) return appointment.agent_name;
      if (appointment.assigned_agent_name) return appointment.assigned_agent_name;
      if (appointment.name) return appointment.name;
      // Se vier lista de agentes, buscar por userId
      // (No supervisor, agents é prop/context, aqui não está disponível)
      return 'Sem agente';
    };
  const clientName = `${appointment.first_name} ${appointment.last_name}`;
  const totalProtocols = 1 + (appointment.additional_protocols?.length || 0);
  const hasDocuments = appointment.document_urls?.length > 0;
  
  return (
    <div
      className={`appointment-card rounded-md border-l-4 p-2 cursor-pointer hover:shadow-sm transition-shadow ${statusColors[appointment.status] || statusColors.pendente_atribuicao}`}
      data-testid={`appointment-card-${appointment.id}`}
      onClick={onEdit}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold truncate" data-testid="appointment-client-name">
            {clientName}
          </p>
          <p className="text-xs opacity-75 truncate mt-0.5">
            {appointment.protocol_number}
          </p>
          {!compact && (
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[10px] px-1.5 py-0.5 bg-white/50 rounded capitalize">
                {statusLabels[appointment.status]}
              </span>
              {totalProtocols > 1 && (
                <span className="text-[10px] px-1.5 py-0.5 bg-white/50 rounded">
                  {totalProtocols} prot.
                </span>
              )}
              {hasDocuments && (
                <FileText className="w-3 h-3 opacity-60" />
              )}
              {appointment.has_chat && (
                <MessageCircle className="w-3 h-3 opacity-60" />
              )}
              <span className="text-[10px] text-muted-foreground">
                Agente: {getAgentName(appointment.user_id)}
              </span>
            </div>
          )}
        </div>
        {onEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
              <button className="p-1 hover:bg-white/50 rounded" data-testid="appointment-menu">
                <MoreVertical className="w-4 h-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); onEdit(); }} data-testid="edit-appointment">
                Editar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  );
};
