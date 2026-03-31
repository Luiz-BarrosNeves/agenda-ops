import { useCallback, useEffect, useState } from 'react';

export const useBrowserNotifications = () => {
  const [permission, setPermission] = useState('default');
  const [enabled, setEnabled] = useState(() => {
    const saved = localStorage.getItem('browserNotificationsEnabled');
    return saved === 'true';
  });

  // Verificar permissão atual
  useEffect(() => {
    if ('Notification' in window) {
      setPermission(Notification.permission);
    }
  }, []);

  // Salvar preferência
  useEffect(() => {
    localStorage.setItem('browserNotificationsEnabled', enabled.toString());
  }, [enabled]);

  // Solicitar permissão
  const requestPermission = useCallback(async () => {
    if (!('Notification' in window)) {
      console.warn('Browser não suporta notificações');
      return 'denied';
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      if (result === 'granted') {
        setEnabled(true);
      }
      return result;
    } catch (error) {
      console.error('Erro ao solicitar permissão:', error);
      return 'denied';
    }
  }, []);

  // Enviar notificação
  const sendNotification = useCallback((title, options = {}) => {
    if (!enabled || permission !== 'granted') {
      return null;
    }

    try {
      const notification = new Notification(title, {
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        tag: options.tag || 'agendahub-notification',
        renotify: true,
        ...options
      });

      // Auto-fechar após 5 segundos
      setTimeout(() => {
        notification.close();
      }, 5000);

      // Focar na janela quando clicar
      notification.onclick = () => {
        window.focus();
        notification.close();
        options.onClick?.();
      };

      return notification;
    } catch (error) {
      console.error('Erro ao enviar notificação:', error);
      return null;
    }
  }, [enabled, permission]);

  // Notificação de novo agendamento pendente
  const notifyNewPending = useCallback((clientName) => {
    return sendNotification('Novo Agendamento Pendente', {
      body: `${clientName} aguarda atribuição de agente`,
      tag: 'pending-assignment',
      requireInteraction: true,
    });
  }, [sendNotification]);

  // Notificação de agendamento atribuído
  const notifyAssigned = useCallback((clientName, timeSlot) => {
    return sendNotification('Agendamento Atribuído', {
      body: `${clientName} foi atribuído a você às ${timeSlot}`,
      tag: 'appointment-assigned',
    });
  }, [sendNotification]);

  // Toggle ativar/desativar
  const toggleEnabled = useCallback(async () => {
    if (!enabled && permission !== 'granted') {
      const result = await requestPermission();
      return result === 'granted';
    }
    setEnabled(!enabled);
    return !enabled;
  }, [enabled, permission, requestPermission]);

  return {
    permission,
    enabled,
    isSupported: 'Notification' in window,
    requestPermission,
    sendNotification,
    notifyNewPending,
    notifyAssigned,
    toggleEnabled,
    setEnabled
  };
};

export default useBrowserNotifications;
