/**
 * Guia de Migração para Zustand
 * =============================
 * 
 * Este arquivo documenta como migrar componentes existentes para usar
 * a store Zustand centralizada.
 * 
 * STORES DISPONÍVEIS:
 * - useAppointmentsStore: Gerencia agendamentos
 * - useUsersStore: Gerencia usuários e presença
 * - useNotificationsStore: Gerencia notificações
 * - useDashboardStore: Gerencia estatísticas do dashboard
 * - useUIStore: Gerencia estado da UI (persistido)
 */

// ==================== ANTES (useState + API direto) ====================
/*
import { useState, useEffect } from 'react';
import { appointmentsAPI } from '../utils/api';

const MyComponent = () => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const response = await appointmentsAPI.getAll({});
        setAppointments(response.data);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);
  
  return (
    <div>
      {loading ? 'Carregando...' : appointments.map(apt => ...)}
    </div>
  );
};
*/

// ==================== DEPOIS (Zustand Store) ====================
/*
import { useAppointmentsStore } from '../stores/useAppStore';

const MyComponent = () => {
  const { appointments, loading, fetchAppointments } = useAppointmentsStore();
  
  useEffect(() => {
    fetchAppointments({});
  }, []);
  
  return (
    <div>
      {loading ? 'Carregando...' : appointments.map(apt => ...)}
    </div>
  );
};
*/

// ==================== EXEMPLO COM PAGINAÇÃO ====================
/*
import { useAppointmentsStore } from '../stores/useAppStore';

const PaginatedList = () => {
  const { 
    appointments, 
    loading, 
    pagination,
    fetchAppointmentsPaginated 
  } = useAppointmentsStore();
  
  useEffect(() => {
    fetchAppointmentsPaginated(1, 20);
  }, []);
  
  const loadMore = () => {
    if (pagination.page < pagination.totalPages) {
      fetchAppointmentsPaginated(pagination.page + 1, 20);
    }
  };
  
  return (
    <div>
      {appointments.map(apt => ...)}
      {pagination.page < pagination.totalPages && (
        <button onClick={loadMore}>Carregar mais</button>
      )}
    </div>
  );
};
*/

// ==================== EXEMPLO COM UI STORE (persistido) ====================
/*
import { useUIStore } from '../stores/useAppStore';

const ThemeToggle = () => {
  const { theme, toggleTheme } = useUIStore();
  
  return (
    <button onClick={toggleTheme}>
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
};
*/

// ==================== SELETORES OTIMIZADOS ====================
/*
// Para evitar re-renders desnecessários, use seletores específicos:

// ❌ Isso causa re-render sempre que qualquer parte da store muda
const { appointments, loading, error } = useAppointmentsStore();

// ✅ Isso só causa re-render quando os valores selecionados mudam
const appointments = useAppointmentsStore(state => state.appointments);
const loading = useAppointmentsStore(state => state.loading);
*/

export default function MigrationGuide() {
  return null; // Este arquivo é apenas documentação
}
