import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { appointmentsAPI, usersAPI, notificationsAPI, statsAPI, presenceAPI } from '../utils/api';

// ==================== APPOINTMENTS STORE ====================
export const useAppointmentsStore = create((set, get) => ({
  // State
  appointments: [],
  pendingAppointments: [],
  myAppointments: [],
  selectedDate: new Date().toISOString().split('T')[0],
  loading: false,
  error: null,
  
  // Pagination
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  },
  
  // Actions
  setSelectedDate: (date) => set({ selectedDate: date }),
  
  fetchAppointments: async (params = {}) => {
    set({ loading: true, error: null });
    try {
      const response = await appointmentsAPI.getAll(params);
      set({ appointments: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  fetchAppointmentsPaginated: async (page = 1, pageSize = 20, params = {}) => {
    set({ loading: true, error: null });
    try {
      const response = await appointmentsAPI.getPaginated(page, pageSize, params);
      set({ 
        appointments: response.data.items,
        pagination: {
          page: response.data.page,
          pageSize: response.data.page_size,
          total: response.data.total,
          totalPages: response.data.total_pages,
        },
        loading: false 
      });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  fetchPendingAppointments: async () => {
    set({ loading: true, error: null });
    try {
      const response = await appointmentsAPI.getPending();
      set({ pendingAppointments: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  fetchMyAppointments: async (date) => {
    set({ loading: true, error: null });
    try {
      const response = await appointmentsAPI.getMyAppointments(date);
      set({ myAppointments: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  updateAppointment: async (id, data) => {
    try {
      const response = await appointmentsAPI.update(id, data);
      // Atualizar no estado local
      set((state) => ({
        appointments: state.appointments.map(apt => 
          apt.id === id ? response.data : apt
        ),
        myAppointments: state.myAppointments.map(apt =>
          apt.id === id ? response.data : apt
        ),
      }));
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  assignAppointment: async (id, userId) => {
    try {
      const response = await appointmentsAPI.assign(id, userId);
      // Remover de pendentes e adicionar a appointments
      set((state) => ({
        pendingAppointments: state.pendingAppointments.filter(apt => apt.id !== id),
        appointments: [...state.appointments.filter(apt => apt.id !== id), response.data],
      }));
      return response.data;
    } catch (error) {
      throw error;
    }
  },
  
  // Reset
  reset: () => set({
    appointments: [],
    pendingAppointments: [],
    myAppointments: [],
    loading: false,
    error: null,
    pagination: { page: 1, pageSize: 20, total: 0, totalPages: 0 },
  }),
}));

// ==================== USERS STORE ====================
export const useUsersStore = create((set, get) => ({
  // State
  users: [],
  attendants: [],
  agentsPresence: [],
  loading: false,
  error: null,
  
  // Pagination
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
  },
  
  // Actions
  fetchUsers: async (params = {}) => {
    set({ loading: true, error: null });
    try {
      const response = await usersAPI.getAll(params);
      set({ users: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  fetchAttendants: async () => {
    set({ loading: true, error: null });
    try {
      const response = await usersAPI.getAttendants();
      set({ attendants: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },
  
  fetchAgentsPresence: async () => {
    try {
      const response = await presenceAPI.getAgentsPresence();
      set({ agentsPresence: response.data });
      return response.data;
    } catch (error) {
      console.error('Error fetching presence:', error);
      throw error;
    }
  },
  
  approveUser: async (userId) => {
    try {
      await usersAPI.approve(userId);
      set((state) => ({
        users: state.users.map(user =>
          user.id === userId ? { ...user, approved: true } : user
        ),
      }));
    } catch (error) {
      throw error;
    }
  },
  
  updateUserRole: async (userId, role) => {
    try {
      await usersAPI.updateRole(userId, role);
      set((state) => ({
        users: state.users.map(user =>
          user.id === userId ? { ...user, role } : user
        ),
      }));
    } catch (error) {
      throw error;
    }
  },
  
  updateUserPermissions: async (userId, permissions) => {
    try {
      await usersAPI.updatePermissions(userId, permissions);
      set((state) => ({
        users: state.users.map(user =>
          user.id === userId ? { ...user, ...permissions } : user
        ),
      }));
    } catch (error) {
      throw error;
    }
  },
  
  deleteUser: async (userId) => {
    try {
      await usersAPI.delete(userId);
      set((state) => ({
        users: state.users.filter(user => user.id !== userId),
      }));
    } catch (error) {
      throw error;
    }
  },
  
  reset: () => set({
    users: [],
    attendants: [],
    agentsPresence: [],
    loading: false,
    error: null,
  }),
}));

// ==================== NOTIFICATIONS STORE ====================
export const useNotificationsStore = create((set, get) => ({
  // State
  notifications: [],
  unreadCount: 0,
  loading: false,
  
  // Actions
  fetchNotifications: async () => {
    set({ loading: true });
    try {
      const response = await notificationsAPI.getAll();
      const notifications = response.data;
      const unreadCount = notifications.filter(n => !n.read).length;
      set({ notifications, unreadCount, loading: false });
      return notifications;
    } catch (error) {
      set({ loading: false });
      throw error;
    }
  },
  
  markAsRead: async (notificationId) => {
    try {
      await notificationsAPI.markRead(notificationId);
      set((state) => ({
        notifications: state.notifications.map(n =>
          n.id === notificationId ? { ...n, read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }));
    } catch (error) {
      throw error;
    }
  },
  
  markAllAsRead: async () => {
    try {
      await notificationsAPI.markAllRead();
      set((state) => ({
        notifications: state.notifications.map(n => ({ ...n, read: true })),
        unreadCount: 0,
      }));
    } catch (error) {
      throw error;
    }
  },
  
  deleteNotification: async (notificationId) => {
    try {
      await notificationsAPI.delete(notificationId);
      set((state) => {
        const notification = state.notifications.find(n => n.id === notificationId);
        return {
          notifications: state.notifications.filter(n => n.id !== notificationId),
          unreadCount: notification && !notification.read 
            ? Math.max(0, state.unreadCount - 1) 
            : state.unreadCount,
        };
      });
    } catch (error) {
      throw error;
    }
  },
  
  reset: () => set({
    notifications: [],
    unreadCount: 0,
    loading: false,
  }),
}));

// ==================== DASHBOARD STORE ====================
export const useDashboardStore = create((set, get) => ({
  // State
  stats: null,
  loading: false,
  error: null,
  
  // Actions
  fetchStats: async (date) => {
    set({ loading: true, error: null });
    try {
      const response = await statsAPI.getDashboard(date);
      set({ stats: response.data, loading: false });
      return response.data;
    } catch (error) {
      set({ error: error.message, loading: false });
      // Não lançar erro para permissões
      if (error.response?.status !== 403) {
        throw error;
      }
    }
  },
  
  reset: () => set({
    stats: null,
    loading: false,
    error: null,
  }),
}));

// ==================== UI STORE (persistido) ====================
export const useUIStore = create(
  persist(
    (set) => ({
      // State
      sidebarOpen: true,
      currentView: 'dashboard',
      theme: 'light',
      soundEnabled: true,
      browserNotificationsEnabled: false,
      
      // Actions
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setCurrentView: (view) => set({ currentView: view }),
      setTheme: (theme) => set({ theme }),
      setSoundEnabled: (enabled) => set({ soundEnabled: enabled }),
      setBrowserNotificationsEnabled: (enabled) => set({ browserNotificationsEnabled: enabled }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleTheme: () => set((state) => ({ theme: state.theme === 'light' ? 'dark' : 'light' })),
    }),
    {
      name: 'agendahub-ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        soundEnabled: state.soundEnabled,
        browserNotificationsEnabled: state.browserNotificationsEnabled,
      }),
    }
  )
);

// ==================== COMBINED ACTIONS ====================
export const useGlobalReset = () => {
  const resetAppointments = useAppointmentsStore((state) => state.reset);
  const resetUsers = useUsersStore((state) => state.reset);
  const resetNotifications = useNotificationsStore((state) => state.reset);
  const resetDashboard = useDashboardStore((state) => state.reset);
  
  return () => {
    resetAppointments();
    resetUsers();
    resetNotifications();
    resetDashboard();
  };
};
