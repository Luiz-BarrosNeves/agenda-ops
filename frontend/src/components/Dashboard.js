import React, { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import { Sidebar } from './Sidebar';
import { AgendaCompleta } from './AgendaCompleta';
import { MyAppointments } from './MyAppointments';
import { ChangeRequestsPanel } from './ChangeRequestsPanel';
import { AvailabilityView } from './AvailabilityView';
import { AppointmentModal } from './AppointmentModal';
import { PendingAssignments } from './PendingAssignments';
import { AppointmentFilters } from './AppointmentFilters';
import { NotificationsPanel, NotificationsBell } from './NotificationsPanel';
import { ReportsPanel } from './ReportsPanel';
import { AgentPresenceList } from './AgentPresence';
import { ThemeToggle } from './ThemeToggle';
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts';
import { toast } from 'sonner';
import { appointmentsAPI, statsAPI } from '../utils/api';
import { slotsAPI, presenceAPI } from '../utils/api';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Input } from './ui/input';
import { Calendar } from './ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Plus, Filter, FileText, Calendar as CalendarIcon, ClipboardList, Users, LayoutDashboard, Search, Keyboard, Menu, X, LogOut, CheckSquare, KeyRound } from 'lucide-react';
import { ChangePasswordModal } from './ChangePasswordModal';
import { MetricCardSkeleton } from './ui/loading-states';
import { FadeIn, AnimatedCard } from './ui/animations';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { format, parseISO } from 'date-fns';

// Variantes de animação para views
const viewVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 }
};

const viewTransition = {
  duration: 0.2,
  ease: [0.4, 0, 0.2, 1]
};

export const Dashboard = () => {
  const { user, logout } = useAuth();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [currentView, setCurrentView] = useState('dashboard');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalInitialData, setModalInitialData] = useState(null);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [showPending, setShowPending] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showReports, setShowReports] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [activeFilters, setActiveFilters] = useState({});
  const [filteredAppointments, setFilteredAppointments] = useState([]);
  const [myAppointments, setMyAppointments] = useState([]);
  const [myAppointmentsSearch, setMyAppointmentsSearch] = useState('');
  const [dashboardStats, setDashboardStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const filterInputRef = useRef(null);
  const toastShownRef = useRef(false);
  const [slotsDia, setSlotsDia] = useState([]);

  const isSupervisor = user?.role === 'supervisor';
  const isAdmin = user?.role === 'admin';
  const isAgent = user?.role === 'agente';
  const isCreator = user?.role === 'televendas' || user?.role === 'comercial';
  const canCreate = isCreator || isSupervisor; // Admin não pode criar
  const canSeePending = isSupervisor; // Admin apenas visualiza relatórios
  const canViewReports = isSupervisor || isAdmin; // Admin pode ver relatórios
  const canFilter = true;

  // Atalhos de teclado
  const handlePrevDay = useCallback(() => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 1);
    setCurrentDate(newDate);
  }, [currentDate]);

  const handleNextDay = useCallback(() => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 1);
    setCurrentDate(newDate);
  }, [currentDate]);

  // Cálculos derivados antes do return

  const capacidadeDia = slotsDia.length;
  const totalAgendamentosDia = dashboardStats?.total || 0;
  const ocupacaoPercentual = capacidadeDia > 0 ? Math.round((totalAgendamentosDia / capacidadeDia) * 100) : 0;

  let riscoTexto = 'Tranquilo';
  let riscoSubtitulo = 'Agenda sob controle';
  if (ocupacaoPercentual >= 85) {
    riscoTexto = 'Crítico';
    riscoSubtitulo = 'Alta pressão operacional';
  } else if (ocupacaoPercentual >= 70) {
    riscoTexto = 'Atenção';
    riscoSubtitulo = 'Monitorar ocupação';
  }

  // Indicador de Pressão Operacional
  let pressaoTexto = 'Baixa';
  let pressaoSubtexto = 'Fluxo saudável';
  if (ocupacaoPercentual >= 85) {
    pressaoTexto = 'Alta';
    pressaoSubtexto = 'Operação no limite';
  } else if (ocupacaoPercentual >= 60) {
    pressaoTexto = 'Moderada';
    pressaoSubtexto = 'Monitorar demanda';
  }


  const handleOpenNewAppointment = useCallback(() => {
    if (canCreate) {
      setSelectedAppointment(null);
      setModalInitialData(null);
      setIsModalOpen(true);
    }
  }, [canCreate]);

  const handleFocusFilter = useCallback(() => {
    setShowFilters(true);
    setTimeout(() => filterInputRef.current?.focus(), 100);
  }, []);

  useKeyboardShortcuts({
    'n': handleOpenNewAppointment,
    'ArrowLeft': handlePrevDay,
    'ArrowRight': handleNextDay,
    '/': handleFocusFilter,
    'Escape': () => {
      setIsModalOpen(false);
      setShowPending(false);
      setShowNotifications(false);
      setShowReports(false);
      setShowShortcuts(false);
    },
    '?': () => setShowShortcuts(true),
  }, !isModalOpen && !showPending && !showNotifications && !showReports);

  useEffect(() => {
    loadMyAppointments();
    loadDashboardStats();
    loadPendingCount();
    // Carregar slots do dia
    const fetchSlots = async () => {
      try {
        const dateStr = format(currentDate, 'yyyy-MM-dd');
        const response = await slotsAPI.getAll(dateStr);
        console.log('[Dashboard] resposta slotsAPI.getAll:', response);
        console.log('[Dashboard] response?.data:', response?.data);
        console.log('[Dashboard] response?.data?.slots:', response?.data?.slots);
        setSlotsDia(response?.data?.slots || response?.slots || []);
      } catch (error) {
        setSlotsDia([]);
      }
    };
    fetchSlots();
    const interval = setInterval(() => {
      loadDashboardStats();
      loadPendingCount();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [currentDate, user]);

  const loadMyAppointments = async () => {
    try {
      const response = await appointmentsAPI.getAll({});
      const myCreated = response.data.filter(apt => apt.created_by === user?.id);
      setMyAppointments(myCreated);
    } catch (error) {
      console.error('Erro ao carregar meus agendamentos:', error);
    }
  };

  const loadDashboardStats = async () => {
    if (!canSeePending) {
      setStatsLoading(false);
      return;
    }
    try {
      const dateStr = format(currentDate, 'yyyy-MM-dd');
      const response = await statsAPI.getDashboard(dateStr);
      setDashboardStats(response.data);
    } catch (error) {
      // Ignorar erros de permissão silenciosamente
      if (error.response?.status !== 403) {
        console.error('Erro ao carregar estatísticas:', error);
      }
    } finally {
      setStatsLoading(false);
    }
  };

  const loadPendingCount = async () => {
    if (!canSeePending) return;
    try {
      const response = await appointmentsAPI.getPending();
      setPendingCount(response.data.length);
    } catch (error) {
      console.error('Erro ao carregar pendentes:', error);
    }
  };

  const handleFilter = async (filters) => {
    setActiveFilters(filters);
    
    if (Object.keys(filters).length === 0) {
      setFilteredAppointments([]);
      return;
    }
    
    try {
      const response = await appointmentsAPI.getFiltered(filters);
      setFilteredAppointments(response.data);
      toast.success(`${response.data.length} agendamento(s) encontrado(s)`);
    } catch (error) {
      toast.error('Erro ao filtrar agendamentos');
    }
  };

  const handleCreateAppointment = (initialData = null) => {
    setSelectedAppointment(null);
    setModalInitialData(initialData);
    setIsModalOpen(true);
  };

  const handleEditAppointment = (appointment) => {
    setSelectedAppointment(appointment);
    setModalInitialData(null);
    setIsModalOpen(true);
  };

  const handleSaveAppointment = async () => {
    setIsModalOpen(false);
    setModalInitialData(null);
    await loadMyAppointments();
    await loadDashboardStats();
    await loadPendingCount();
    if (typeof fetchSlots === 'function') {
      await fetchSlots();
    }
    // Toast já é mostrado pelo AppointmentModal, não duplicar aqui
  };

  const hasActiveFilters = Object.keys(activeFilters).length > 0;

  // Menu items baseado no role - Agenda agora está integrada no Dashboard
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, show: true },
    { id: 'meus', label: 'Meus Agendamentos', icon: ClipboardList, show: isCreator || isAgent || isSupervisor },
    { id: 'requests', label: 'Solicitações', icon: CheckSquare, show: isSupervisor },
  ];

  // Admin só tem acesso ao Dashboard (visualização) e relatórios - não pode criar/editar nada
  const isReadOnly = isAdmin;

  // State para o calendário popover
  const [calendarOpen, setCalendarOpen] = useState(false);

  // Expor handler global para AvailabilityView
  window.handleCreateAppointment = (initialData) => {
    if (!isAdmin) handleCreateAppointment(initialData);
  };
  return (
    <div className="flex h-screen overflow-hidden bg-background" data-testid="dashboard">
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:relative inset-y-0 left-0 z-50
        w-64 bg-card border-r border-border flex flex-col h-screen flex-shrink-0
        transform transition-transform duration-200 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex flex-col items-start gap-1">
              <div className="flex items-center gap-2 py-1">
                <span className="bg-primary text-primary-foreground font-bold rounded-full w-6 h-6 flex items-center justify-center text-sm shadow-sm border border-primary/30 flex-shrink-0">AO</span>
                <span className="text-base font-extrabold tracking-tight text-foreground leading-tight ml-1">AgendaOps</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <button 
              className="lg:hidden p-1 hover:bg-muted rounded"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Botão Novo Agendamento */}
        {canCreate && (
          <div className="p-4 border-b border-border">
            <Button
              onClick={() => handleCreateAppointment()}
              className="w-full"
              data-testid="new-appointment-btn"
            >
              <Plus className="w-4 h-4 mr-2" />
              Novo Agendamento
            </Button>
          </div>
        )}

        {/* Menu */}
        <nav className="flex-1 p-4 space-y-1">
          {menuItems.filter(item => item.show).map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentView(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                currentView === item.id
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
              data-testid={`menu-${item.id}`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </button>
          ))}

          {/* Pendentes - apenas supervisor/admin */}
          {canSeePending && (
            <button
              onClick={() => setShowPending(true)}
              className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg text-left text-muted-foreground hover:bg-muted"
              data-testid="menu-pendentes"
            >
              <div className="flex items-center gap-3">
                <ClipboardList className="w-5 h-5" />
                Pendentes
              </div>
              {pendingCount > 0 && (
                <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {pendingCount}
                </span>
              )}
            </button>
          )}

          {/* Usuários - apenas supervisor */}
          {(isSupervisor || isAdmin) && (
            <a
              href="/users"
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:bg-muted"
              data-testid="menu-usuarios"
            >
              <Users className="w-5 h-5" />
              Usuários
            </a>
          )}

          {/* Painel Supervisor */}
          {(isSupervisor || isAdmin) && (
            <a
              href="/supervisor"
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-muted-foreground hover:bg-muted"
              data-testid="menu-supervisor"
            >
              <LayoutDashboard className="w-5 h-5" />
              Painel Supervisor
            </a>
          )}
        </nav>

        {/* Presença de agentes - supervisor/admin */}
        {(isSupervisor || isAdmin) && (
          <div className="p-4 border-t border-border">
            <AgentPresenceList compact />
          </div>
        )}

        {/* User info com botão logout */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold">
              {user?.name?.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user?.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              className="p-2 hover:bg-destructive/10 rounded-lg transition-colors group"
              title="Sair da conta"
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 text-muted-foreground group-hover:text-destructive" />
            </button>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="w-full mt-3 flex items-center gap-2 justify-start"
            onClick={() => setShowChangePassword(true)}
            data-testid="change-password-btn"
          >
            <KeyRound className="w-4 h-4 mr-2" />
            Alterar senha
          </Button>
        </div>
        {/* Modal de alterar senha */}
        <ChangePasswordModal open={showChangePassword} onOpenChange={setShowChangePassword} />
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-card border-b border-border px-4 lg:px-6 py-4 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            <button
              className="lg:hidden p-2 hover:bg-muted rounded-lg"
              onClick={() => setSidebarOpen(true)}
              data-testid="mobile-menu-btn"
            >
              <Menu className="w-5 h-5 text-muted-foreground" />
            </button>
            <div>
              <h2 className="text-lg lg:text-xl font-semibold text-foreground">
                {currentView === 'dashboard' && 'Dashboard'}
                {currentView === 'meus' && 'Meus Agendamentos'}
                {currentView === 'requests' && 'Solicitações de Alteração'}
              </h2>
              {currentView === 'dashboard' && (
                <p className="text-sm text-muted-foreground mt-1 font-normal">Visão geral operacional em tempo real</p>
              )}
              {hasActiveFilters && (
                <p className="text-sm text-muted-foreground mt-1 hidden sm:block">
                  {filteredAppointments.length} resultado(s) • 
                  {activeFilters.date_from && ` De ${format(parseISO(activeFilters.date_from), 'dd/MM/yyyy')}`}
                  {activeFilters.date_to && ` até ${format(parseISO(activeFilters.date_to), 'dd/MM/yyyy')}`}
                  {activeFilters.status && ` • Status: ${activeFilters.status}`}
                  <Button
                    variant="link"
                    size="sm"
                    className="ml-2 h-auto p-0 text-primary"
                    onClick={() => { setActiveFilters({}); setFilteredAppointments([]); }}
                  >
                    Limpar filtros
                  </Button>
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 lg:gap-3">
            <Button
              variant={showFilters ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              data-testid="toggle-filters"
              className="hidden sm:flex"
            >
              <Filter className="w-4 h-4 mr-2" />
              Filtros
            </Button>
            <Button
              variant={showFilters ? 'secondary' : 'outline'}
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="sm:hidden"
            >
              <Filter className="w-4 h-4" />
            </Button>

            {(isSupervisor || isAdmin) && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowReports(true)}
                  data-testid="reports-button"
                  className="hidden sm:flex"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Relatórios
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowReports(true)}
                  className="sm:hidden"
                >
                  <FileText className="w-4 h-4" />
                </Button>
              </>
            )}

            <NotificationsBell 
              onClick={() => setShowNotifications(true)} 
              onNewPending={() => loadPendingCount()}
            />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          {/* Filtros */}
          <AnimatePresence>
            {showFilters && (
              <motion.div 
                className="mb-4"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
              >
                <AppointmentFilters onFilter={handleFilter} userRole={user?.role} />
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
          {/* Dashboard View */}
          {currentView === 'dashboard' && (
            <motion.div 
              key="dashboard"
              className="space-y-6"
              variants={viewVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={viewTransition}
            >
              {/* Novo card: Capacidade do dia */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 xl:gap-4 mb-3">
                <AnimatedCard delay={0}>
                  <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-normal text-muted-foreground">Capacidade do dia</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">{slotsDia.length}</p>
                      <p className="text-xs text-muted-foreground mt-1">slots disponíveis no dia</p>
                    </CardContent>
                  </Card>
                </AnimatedCard>
                <AnimatedCard delay={0.05}>
                  <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-normal text-muted-foreground">Ocupação do dia</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-4xl font-bold text-green-600 dark:text-green-400">{totalAgendamentosDia} / {capacidadeDia}</p>
                      <p className="text-xs text-muted-foreground mt-1">{ocupacaoPercentual}% de ocupação</p>
                    </CardContent>
                  </Card>
                </AnimatedCard>
                <AnimatedCard delay={0.1}>
                  <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-normal text-muted-foreground">Risco do dia</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p
                        className={
                          `text-4xl font-bold ` +
                          (riscoTexto === 'Crítico'
                            ? 'text-red-600 dark:text-red-400'
                            : riscoTexto === 'Atenção'
                              ? 'text-yellow-600 dark:text-yellow-400'
                              : 'text-green-600 dark:text-green-400')
                        }
                      >
                        {riscoTexto}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">{riscoSubtitulo}</p>
                    </CardContent>
                  </Card>
                </AnimatedCard>
                <AnimatedCard delay={0.15}>
                  <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-normal text-muted-foreground">Pressão Operacional</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-4xl font-bold text-blue-600 dark:text-blue-400">{pressaoTexto}</p>
                      <p className="text-xs text-muted-foreground mt-1">{pressaoSubtexto}</p>
                    </CardContent>
                  </Card>
                </AnimatedCard>
              </div>
              {/* Cards de métricas */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
                {statsLoading ? (
                  <>
                    <MetricCardSkeleton />
                    <MetricCardSkeleton />
                    <MetricCardSkeleton />
                    <MetricCardSkeleton />
                  </>
                ) : (
                  <>
                    <AnimatedCard delay={0}>
                      <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-normal text-muted-foreground">Total Agendamentos</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {dashboardStats?.total === 0 ? (
                            <>
                              <p className="text-2xl font-semibold text-muted-foreground">Nenhum agendamento hoje</p>
                              <p className="text-xs text-muted-foreground mt-2 italic">Acompanhe os agendamentos em tempo real</p>
                            </>
                          ) : (
                            <>
                              <p className="text-4xl font-bold text-foreground">{dashboardStats?.total}</p>
                              <p className="text-xs text-muted-foreground mt-1">Hoje</p>
                            </>
                          )}
                        </CardContent>
                      </Card>
                    </AnimatedCard>

                    {canSeePending && (
                      <AnimatedCard delay={0.05}>
                        <Card className={pendingCount > 0 ? 'p-6 shadow-xl bg-yellow-50/80 dark:bg-yellow-900/30 border-yellow-300/30 dark:border-yellow-700/30 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200' : 'p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200'}>
                          <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-normal text-muted-foreground">Pendentes</CardTitle>
                          </CardHeader>
                          <CardContent>
                            {pendingCount === 0 ? (
                              <>
                                <p className="text-2xl font-semibold text-muted-foreground">Nenhum pendente</p>
                                <p className="text-xs text-muted-foreground mt-2 italic">Todos os agendamentos atribuídos</p>
                              </>
                            ) : (
                              <>
                                <p className="text-4xl font-bold text-yellow-600 dark:text-yellow-400">{pendingCount}</p>
                                <p className="text-xs text-muted-foreground mt-1">Aguardando atribuição</p>
                              </>
                            )}
                          </CardContent>
                        </Card>
                      </AnimatedCard>
                    )}

                    <AnimatedCard delay={0.1}>
                      <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-normal text-muted-foreground">Emitidos</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {dashboardStats?.by_status?.emitidos === 0 ? (
                            <>
                              <p className="text-2xl font-semibold text-muted-foreground">Nenhum emitido</p>
                              <p className="text-xs text-muted-foreground mt-2 italic">Aguardando emissões</p>
                            </>
                          ) : (
                            <>
                              <p className="text-4xl font-bold text-green-600 dark:text-green-400">{dashboardStats?.by_status?.emitidos}</p>
                              <p className="text-xs text-muted-foreground mt-1">Concluídos hoje</p>
                            </>
                          )}
                        </CardContent>
                      </Card>
                    </AnimatedCard>

                    <AnimatedCard delay={0.15}>
                      <Card className="p-6 shadow-xl bg-white/98 dark:bg-zinc-900/90 border border-border/40 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200">
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-normal text-muted-foreground">Auto-atribuídos</CardTitle>
                        </CardHeader>
                        <CardContent>
                          {dashboardStats?.auto_assigned === 0 ? (
                            <>
                              <p className="text-2xl font-semibold text-muted-foreground">Nenhum auto-atribuído</p>
                              <p className="text-xs text-muted-foreground mt-2 italic">Aguardando atribuições automáticas</p>
                            </>
                          ) : (
                            <>
                              <p className="text-4xl font-bold text-purple-600 dark:text-purple-400">{dashboardStats?.auto_assigned}</p>
                              <p className="text-xs text-muted-foreground mt-1">Pelo sistema</p>
                            </>
                          )}
                        </CardContent>
                      </Card>
                    </AnimatedCard>
                  </>
                )}
              </div>

              {/* Horários disponíveis */}
              <FadeIn delay={0.2}>
                <div className="mt-6">
                  <AvailabilityView date={format(currentDate, 'yyyy-MM-dd')} secondary />
                </div>
              </FadeIn>

              {/* AGENDA COMPLETA - Integrada no Dashboard */}
              <FadeIn delay={0.25}>
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <CalendarIcon className="w-5 h-5" />
                        Agenda do Dia
                      </CardTitle>
                      
                      {/* Seletor de Data com Calendário */}
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handlePrevDay}
                          data-testid="prev-day-btn"
                        >
                          ←
                        </Button>
                        
                        <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              className="min-w-[180px] justify-start text-left font-normal"
                              data-testid="date-picker-btn"
                            >
                              <CalendarIcon className="mr-2 h-4 w-4" />
                              {format(currentDate, "dd 'de' MMM, yyyy", { locale: ptBR })}
                            </Button>
                          </PopoverTrigger>
                          <PopoverContent className="w-auto p-0" align="center">
                            <Calendar
                              mode="single"
                              selected={currentDate}
                              onSelect={(date) => {
                                if (date) {
                                  setCurrentDate(date);
                                  setCalendarOpen(false);
                                }
                              }}
                              locale={ptBR}
                              initialFocus
                            />
                          </PopoverContent>
                        </Popover>
                        
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleNextDay}
                          data-testid="next-day-btn"
                        >
                          →
                        </Button>
                        
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setCurrentDate(new Date())}
                          className="text-primary"
                          data-testid="today-btn"
                        >
                          Hoje
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <AgendaCompleta
                      currentDate={currentDate}
                      onDateChange={setCurrentDate}
                      onNewAppointment={handleCreateAppointment}
                      onEditAppointment={handleEditAppointment}
                      userRole={user?.role}
                      embedded={true}
                      appointments={hasActiveFilters ? filteredAppointments : undefined}
                    />
                  </CardContent>
                </Card>
              </FadeIn>

              {/* Presença de agentes - para supervisor */}
              {(isSupervisor || isAdmin) && (
                <FadeIn delay={0.3}>
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Horários e Agentes</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <AgentPresenceList />
                    </CardContent>
                  </Card>
                </FadeIn>
              )}
            </motion.div>
          )}

          {/* Meus Agendamentos View */}
          {currentView === 'meus' && (
            <motion.div 
              key="meus"
              className="space-y-4"
              variants={viewVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={viewTransition}
            >
              <MyAppointments />
            </motion.div>
          )}

          {/* Solicitações View (Supervisor) */}
          {currentView === 'requests' && (
            <motion.div 
              key="requests"
              className="space-y-4"
              variants={viewVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              transition={viewTransition}
            >
              <ChangeRequestsPanel />
            </motion.div>
          )}
          </AnimatePresence>
        </main>
      </div>

      {/* Modals */}
      {isModalOpen && (
        <AppointmentModal
          isOpen={isModalOpen}
          onClose={() => { setIsModalOpen(false); setModalInitialData(null); }}
          appointment={selectedAppointment}
          initialData={modalInitialData}
          onSave={handleSaveAppointment}
          userRole={user?.role}
          user={user}
          onSubmitOverride={
            user?.role === 'supervisor'
              ? undefined
              : async (formData, ctx) => {
                  // a) valida ctx.appointment existe
                  if (!ctx?.appointment) {
                    toast.error('Agendamento não encontrado');
                    throw new Error('Agendamento não encontrado');
                  }
                  // b) valida criador
                  if (ctx.appointment.created_by !== ctx.user.id) {
                    toast.error('Você só pode solicitar alteração de agendamentos criados por você.');
                    console.log('[LOG] Bloqueado: user', ctx.user.id, 'appointment.created_by', ctx.appointment.created_by);
                    throw new Error('Permissão negada');
                  }
                  // c) monta payload e faz POST
                  const payload = {
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
                  };
                  console.log('[LOG] Enviando POST /change-requests', payload);
                  await appointmentsAPI.createChangeRequest(payload);
                }
          }
        />
      )}

      {showPending && (
        <PendingAssignments
          isOpen={showPending}
          onClose={() => setShowPending(false)}
          onAssigned={() => { loadPendingCount(); loadDashboardStats(); }}
        />
      )}

      <NotificationsPanel 
        isOpen={showNotifications} 
        onClose={() => setShowNotifications(false)} 
      />

      <ReportsPanel
        isOpen={showReports}
        onClose={() => setShowReports(false)}
      />

      {/* Modal de atalhos */}
      {showShortcuts && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowShortcuts(false)}
        >
          <Card className="w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Keyboard className="w-5 h-5" />
                Atalhos de Teclado
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Novo agendamento</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">N</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Dia anterior</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">←</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Próximo dia</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">→</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Focar filtros</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">/</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Fechar modais</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">ESC</kbd>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Este menu</span>
                <kbd className="px-2 py-1 bg-muted border border-border rounded text-xs font-mono">?</kbd>
              </div>
              <Button 
                variant="outline" 
                className="w-full mt-4" 
                onClick={() => setShowShortcuts(false)}
              >
                Fechar
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

