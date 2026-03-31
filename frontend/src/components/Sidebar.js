import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';
import { Calendar, Users, LogOut, Plus, ClipboardList } from 'lucide-react';
import { appointmentsAPI } from '../utils/api';
import { AgentPresenceList } from './AgentPresence';
import { ThemeToggle } from './ThemeToggle';

export const Sidebar = ({ onCreateAppointment, onShowPending }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    if (user?.role === 'supervisor') {
      loadPendingCount();
      const interval = setInterval(loadPendingCount, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const loadPendingCount = async () => {
    try {
      const response = await appointmentsAPI.getPending();
      setPendingCount(response.data.length);
    } catch (error) {
      console.error('Erro ao carregar pendentes:', error);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isSupervisor = user?.role === 'admin' || user?.role === 'supervisor';

  return (
    <div className="w-64 bg-card border-r border-border shadow-md/10 flex flex-col h-screen" data-testid="sidebar">
      <div className="p-6 border-b border-border">
        <div className="mb-6">
          <div className="flex items-center gap-2 py-1">
            {/* Monograma AO */}
            <span className="bg-primary text-primary-foreground font-bold rounded-full w-6 h-6 flex items-center justify-center text-sm shadow-sm border border-primary/30 flex-shrink-0">AO</span>
            {/* Título */}
            <span className="text-base font-extrabold tracking-tight text-foreground leading-tight ml-1">AgendaOps</span>
            {/* Botão engrenagem */}
            <span className="ml-2 flex items-center"><ThemeToggle /></span>
          </div>
        </div>

        {onCreateAppointment && (
          <Button
            onClick={onCreateAppointment}
            className="w-full bg-primary text-primary-foreground hover:bg-primary/90 h-9 mb-3 py-1.5"
            data-testid="sidebar-create-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Novo Agendamento
          </Button>
        )}

        {onShowPending && (
          <Button
            onClick={onShowPending}
            variant="outline"
            className="w-full h-10 relative"
            data-testid="sidebar-pending-button"
          >
            <ClipboardList className="w-4 h-4 mr-2" />
            Pendentes
            {pendingCount > 0 && (
              <span className="ml-2 bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                {pendingCount}
              </span>
            )}
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div>
          <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">
            Informações
          </h3>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><span className="font-medium text-foreground">Perfil:</span> {user?.role === 'admin' ? 'Administrador' : user?.role === 'supervisor' ? 'Supervisor' : user?.role === 'agente' ? 'Agente' : user?.role === 'televendas' ? 'Televendas' : 'Comercial'}</p>
            <div className="pt-2 border-t border-border">
              <p className="text-xs text-muted-foreground">Horários: 08:00 - 18:40</p>
              <p className="text-xs text-muted-foreground">Sessões: 20 minutos</p>
            </div>
          </div>
        </div>

        {isSupervisor && (
          <AgentPresenceList />
        )}
      </div>

      <div className="p-6 border-t border-border space-y-3">
        {isSupervisor && (
          <>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => navigate('/supervisor')}
              data-testid="supervisor-button"
            >
              <Users className="w-4 h-4 mr-2" />
              Painel Supervisor
            </Button>
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={() => navigate('/users')}
              data-testid="users-management-button"
            >
              <Users className="w-4 h-4 mr-2" />
              Gerenciar Usuários
            </Button>
          </>
        )}

        <div className="flex items-center gap-3 p-3 bg-muted rounded-md">
          <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-medium">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
        </div>

        <Button
          variant="ghost"
          className="w-full justify-start text-muted-foreground hover:text-foreground"
          onClick={handleLogout}
          data-testid="logout-button"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Sair
        </Button>
      </div>
    </div>
  );
};
