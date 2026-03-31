import { useState, useEffect, useCallback } from 'react';

/**
 * Hook para persistir filtros no localStorage
 * @param {string} key - Chave única para armazenar os filtros
 * @param {object} defaultFilters - Filtros padrão
 * @returns {[object, function, function]} - [filters, setFilter, resetFilters]
 */
export const usePersistedFilters = (key, defaultFilters = {}) => {
  const storageKey = `agendahub_filters_${key}`;
  
  // Inicializa os filtros do localStorage ou usa os padrões
  const [filters, setFilters] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        // Merge com defaults para garantir que novos campos sejam adicionados
        return { ...defaultFilters, ...parsed };
      }
    } catch (error) {
      console.warn('Failed to load persisted filters:', error);
    }
    return defaultFilters;
  });

  // Salvar no localStorage quando os filtros mudarem
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(filters));
    } catch (error) {
      console.warn('Failed to persist filters:', error);
    }
  }, [filters, storageKey]);

  // Função para atualizar um filtro específico
  const setFilter = useCallback((filterKey, value) => {
    setFilters(prev => ({
      ...prev,
      [filterKey]: value
    }));
  }, []);

  // Função para resetar todos os filtros
  const resetFilters = useCallback(() => {
    setFilters(defaultFilters);
  }, [defaultFilters]);

  // Função para atualizar múltiplos filtros de uma vez
  const setMultipleFilters = useCallback((newFilters) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters
    }));
  }, []);

  return {
    filters,
    setFilter,
    setFilters: setMultipleFilters,
    resetFilters,
    hasActiveFilters: JSON.stringify(filters) !== JSON.stringify(defaultFilters)
  };
};

/**
 * Hook para persistir preferências do usuário
 * @param {string} key - Chave única
 * @param {any} defaultValue - Valor padrão
 * @returns {[any, function]} - [value, setValue]
 */
export const useLocalStorage = (key, defaultValue) => {
  const storageKey = `agendahub_${key}`;
  
  const [value, setValue] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored !== null) {
        return JSON.parse(stored);
      }
    } catch (error) {
      console.warn('Failed to load from localStorage:', error);
    }
    return defaultValue;
  });

  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to save to localStorage:', error);
    }
  }, [value, storageKey]);

  return [value, setValue];
};

/**
 * Hook para gerenciar histórico de navegação de datas
 * @param {Date} initialDate - Data inicial
 * @returns {object} - Funções e estado de navegação
 */
export const useDateNavigation = (initialDate = new Date()) => {
  const [currentDate, setCurrentDate] = useState(initialDate);
  const [dateHistory, setDateHistory] = useLocalStorage('date_history', []);

  const goToDate = useCallback((date) => {
    setDateHistory(prev => {
      const newHistory = [currentDate.toISOString(), ...prev.slice(0, 9)];
      return newHistory;
    });
    setCurrentDate(date);
  }, [currentDate, setDateHistory]);

  const goBack = useCallback(() => {
    if (dateHistory.length > 0) {
      const [lastDate, ...rest] = dateHistory;
      setDateHistory(rest);
      setCurrentDate(new Date(lastDate));
    }
  }, [dateHistory, setDateHistory]);

  const goToToday = useCallback(() => {
    goToDate(new Date());
  }, [goToDate]);

  return {
    currentDate,
    setCurrentDate: goToDate,
    goBack,
    goToToday,
    canGoBack: dateHistory.length > 0
  };
};

export default usePersistedFilters;
