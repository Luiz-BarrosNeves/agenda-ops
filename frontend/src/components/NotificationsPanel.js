import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from './ui/button';
import { notificationsAPI } from '../utils/api';
import { toast } from 'sonner';
import { Bell, Check, CheckCheck, Trash2, X, Zap, Volume2, VolumeX, BellRing, BellOff } from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { useNotificationSound } from '../hooks/useNotificationSound';
import { useBrowserNotifications } from '../hooks/useBrowserNotifications';

const notificationTypeIcons = {
  pending_assignment: Bell,
  appointment_assigned: Check,
  auto_assigned: Zap,
  auto_assigned_info: Zap,
  user_approval_pending: Bell,
};

const notificationTypeColors = {
  pending_assignment: 'bg-yellow-500/20 text-yellow-600 dark:text-yellow-400',
  appointment_assigned: 'bg-green-500/20 text-green-600 dark:text-green-400',
  auto_assigned: 'bg-blue-500/20 text-blue-600 dark:text-blue-400',
  auto_assigned_info: 'bg-purple-500/20 text-purple-600 dark:text-purple-400',
  user_approval_pending: 'bg-orange-500/20 text-orange-600 dark:text-orange-400',
};

export const NotificationsPanel = ({ isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, unread

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen, filter]);

  const loadNotifications = async () => {
    setLoading(true);
    try {
      const read = filter === 'unread' ? false : undefined;
      const response = await notificationsAPI.getAll(read);
      setNotifications(response.data);
    } catch (error) {
      console.error('Erro ao carregar notificações:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await notificationsAPI.markRead(id);
      setNotifications(notifications.map(n => 
        n.id === id ? { ...n, read: true } : n
      ));
    } catch (error) {
      toast.error('Erro ao marcar como lida');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllRead();
      setNotifications(notifications.map(n => ({ ...n, read: true })));
      toast.success('Todas as notificações marcadas como lidas');
    } catch (error) {
      toast.error('Erro ao marcar todas como lidas');
    }
  };

  const handleDelete = async (id) => {
    try {
      await notificationsAPI.delete(id);
      setNotifications(notifications.filter(n => n.id !== id));
      toast.success('Notificação excluída');
    } catch (error) {
      toast.error('Erro ao excluir notificação');
    }
  };

  const handleDeleteAllRead = async () => {
    try {
      await notificationsAPI.deleteAllRead();
      setNotifications(notifications.filter(n => !n.read));
      toast.success('Notificações lidas excluídas');
    } catch (error) {
      toast.error('Erro ao excluir notificações');
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" />
      <div 
        className="relative w-full max-w-md bg-card border-l border-border shadow-xl h-full overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
        data-testid="notifications-panel"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-card">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-foreground" />
            <h2 className="text-lg font-semibold text-foreground">Notificações</h2>
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1 hover:bg-muted rounded">
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-4 py-2 bg-muted/50 border-b border-border">
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`text-xs px-2 py-1 rounded transition-colors ${filter === 'all' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
            >
              Todas
            </button>
            <button
              onClick={() => setFilter('unread')}
              className={`text-xs px-2 py-1 rounded transition-colors ${filter === 'unread' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'}`}
            >
              Não lidas
            </button>
          </div>
          <div className="flex gap-1">
            {unreadCount > 0 && (
              <Button variant="ghost" size="sm" onClick={handleMarkAllRead} className="text-xs">
                <CheckCheck className="w-3 h-3 mr-1" />
                Marcar todas
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={handleDeleteAllRead} className="text-xs text-red-600 dark:text-red-400 hover:text-red-700">
              <Trash2 className="w-3 h-3 mr-1" />
              Limpar lidas
            </Button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto bg-background">
          {loading ? (
            <div className="p-8 text-center text-muted-foreground">Carregando...</div>
          ) : notifications.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>Nenhuma notificação</p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {notifications.map((notif) => {
                const Icon = notificationTypeIcons[notif.type] || Bell;
                const colorClass = notificationTypeColors[notif.type] || 'bg-muted text-muted-foreground';
                
                return (
                  <div
                    key={notif.id}
                    className={`p-4 hover:bg-muted/50 transition-colors ${!notif.read ? 'bg-primary/5' : ''}`}
                    data-testid={`notification-${notif.id}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`p-2 rounded-full ${colorClass}`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${!notif.read ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
                          {notif.message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDistanceToNow(parseISO(notif.created_at), { addSuffix: true, locale: ptBR })}
                        </p>
                      </div>
                      <div className="flex items-center gap-1">
                        {!notif.read && (
                          <button
                            onClick={() => handleMarkRead(notif.id)}
                            className="p-1 text-muted-foreground hover:text-green-600 hover:bg-green-500/10 rounded"
                            title="Marcar como lida"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(notif.id)}
                          className="p-1 text-muted-foreground hover:text-red-600 hover:bg-red-500/10 rounded"
                          title="Excluir"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export const NotificationsBell = ({ onClick, onNewPending }) => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(() => {
    const saved = localStorage.getItem('notificationSoundEnabled');
    return saved !== 'false'; // Default: ativado
  });
  const previousCountRef = useRef(0);
  const isFirstLoadRef = useRef(true);
  const { playSound, playUrgentSound, initAudio } = useNotificationSound(soundEnabled);
  const { 
    enabled: browserNotifEnabled, 
    toggleEnabled: toggleBrowserNotif,
    notifyNewPending,
    permission 
  } = useBrowserNotifications();

  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 15000); // Atualizar a cada 15s
    return () => clearInterval(interval);
  }, []);

  // Salvar preferência de som
  useEffect(() => {
    localStorage.setItem('notificationSoundEnabled', soundEnabled.toString());
  }, [soundEnabled]);

  const loadUnreadCount = async () => {
    try {
      const response = await notificationsAPI.getAll(false);
      const newCount = response.data.length;
      
      // Verificar se há novas notificações (ignorar primeira carga)
      if (!isFirstLoadRef.current && newCount > previousCountRef.current) {
        // Verificar se há notificações de pendentes
        const pendingNotification = response.data.find(n => 
          n.type === 'pending_assignment' && 
          new Date(n.created_at) > new Date(Date.now() - 20000) // Últimos 20 segundos
        );
        
        if (pendingNotification) {
          playUrgentSound();
          toast.info(`Novo agendamento pendente de atribuição!`, {
            icon: '🔔',
            duration: 5000,
          });
          
          // Enviar browser notification se a janela não estiver em foco
          if (document.hidden && browserNotifEnabled) {
            // Extrair nome do cliente da mensagem
            const match = pendingNotification.message?.match(/Novo agendamento: (.+?) às/);
            const clientName = match ? match[1] : 'Cliente';
            notifyNewPending(clientName);
          }
          
          onNewPending?.();
        } else {
          playSound();
        }
      }
      
      previousCountRef.current = newCount;
      isFirstLoadRef.current = false;
      setUnreadCount(newCount);
    } catch (error) {
      console.error('Erro ao carregar contagem:', error);
    }
  };

  const toggleSound = (e) => {
    e.stopPropagation();
    setSoundEnabled(!soundEnabled);
    // Inicializar áudio no clique do usuário (necessário para alguns navegadores)
    if (!soundEnabled) {
      initAudio();
    }
    toast.success(soundEnabled ? 'Som de notificações desativado' : 'Som de notificações ativado');
  };

  const handleToggleBrowserNotif = async (e) => {
    e.stopPropagation();
    const result = await toggleBrowserNotif();
    if (permission === 'denied') {
      toast.error('Notificações bloqueadas pelo navegador. Verifique as permissões do site.');
    } else {
      toast.success(result ? 'Notificações do navegador ativadas' : 'Notificações do navegador desativadas');
    }
  };

  return (
    <div className="flex items-center gap-1">
      {/* Toggle Browser Notifications */}
      <button
        onClick={handleToggleBrowserNotif}
        className="p-2 hover:bg-muted rounded-lg transition-colors"
        title={browserNotifEnabled ? 'Desativar notificações do navegador' : 'Ativar notificações do navegador'}
        data-testid="toggle-browser-notifications"
      >
        {browserNotifEnabled ? (
          <BellRing className="w-4 h-4 text-primary" />
        ) : (
          <BellOff className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {/* Toggle Sound */}
      <button
        onClick={toggleSound}
        className="p-2 hover:bg-muted rounded-lg transition-colors"
        title={soundEnabled ? 'Desativar som' : 'Ativar som'}
        data-testid="toggle-notification-sound"
      >
        {soundEnabled ? (
          <Volume2 className="w-4 h-4 text-muted-foreground" />
        ) : (
          <VolumeX className="w-4 h-4 text-muted-foreground/50" />
        )}
      </button>

      {/* Bell */}
      <button
        onClick={onClick}
        className="relative p-2 hover:bg-muted rounded-lg transition-colors"
        data-testid="notifications-bell"
      >
        <Bell className={`w-5 h-5 ${unreadCount > 0 ? 'text-primary animate-pulse' : 'text-muted-foreground'}`} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 flex items-center justify-center rounded-full animate-bounce">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>
    </div>
  );
};
