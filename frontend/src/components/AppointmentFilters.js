import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { usersAPI } from '../utils/api';
import { Search, Filter, X } from 'lucide-react';

const statusOptions = [
  { value: 'all', label: 'Todos os Status' },
  { value: 'pendente_atribuicao', label: 'Pendente Atribuição' },
  { value: 'confirmado', label: 'Confirmado' },
  { value: 'emitido', label: 'Emitido' },
  { value: 'reagendar', label: 'Reagendar' },
  { value: 'presencial', label: 'Presencial' },
  { value: 'cancelado', label: 'Cancelado' },
];

export const AppointmentFilters = ({ onFilter, userRole }) => {
  const [filters, setFilters] = useState({
    search: '',
    status: 'all',
    agent_id: 'all',
    date_from: '',
    date_to: ''
  });
  const [agents, setAgents] = useState([]);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (userRole === 'supervisor' || userRole === 'admin') {
      loadAgents();
    }
  }, [userRole]);

  const loadAgents = async () => {
    try {
      const response = await usersAPI.getAttendants();
      setAgents(response.data);
    } catch (error) {
      console.error('Erro ao carregar agentes:', error);
      setAgents([]);
    }
  };

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
  };

  const applyFilters = () => {
    const params = {};
    if (filters.search) params.search = filters.search;
    if (filters.status && filters.status !== 'all') params.status = filters.status;
    if (filters.agent_id && filters.agent_id !== 'all') params.agent_id = filters.agent_id;
    if (filters.date_from) params.date_from = filters.date_from;
    if (filters.date_to) params.date_to = filters.date_to;
    onFilter(params);
  };

  const clearFilters = () => {
    const cleared = {
      search: '',
      status: 'all',
      agent_id: 'all',
      date_from: '',
      date_to: ''
    };
    setFilters(cleared);
    onFilter({});
  };

  const hasActiveFilters = filters.search || 
    (filters.status && filters.status !== 'all') || 
    (filters.agent_id && filters.agent_id !== 'all') || 
    filters.date_from || 
    filters.date_to;

  return (
    <div className="bg-card rounded-lg border border-border p-4 mb-4" data-testid="appointment-filters">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium text-foreground hover:text-primary"
        >
          <Filter className="w-4 h-4" />
          Filtros
          {hasActiveFilters && (
            <span className="bg-primary/10 text-primary text-xs px-2 py-0.5 rounded-full">
              Ativos
            </span>
          )}
        </button>
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground">
            <X className="w-4 h-4 mr-1" />
            Limpar
          </Button>
        )}
      </div>

      {/* Busca rápida sempre visível */}
      <div className="flex gap-2 mb-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nome ou protocolo..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && applyFilters()}
            className="pl-10"
            data-testid="filter-search"
          />
        </div>
        <Button onClick={applyFilters} data-testid="filter-apply">
          Buscar
        </Button>
      </div>

      {/* Filtros expandidos */}
      {isExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 pt-3 border-t border-border">
          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Status</Label>
            <Select
              value={filters.status}
              onValueChange={(value) => handleFilterChange('status', value)}
            >
              <SelectTrigger data-testid="filter-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {(userRole === 'supervisor' || userRole === 'admin') && (
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Agente</Label>
              <Select
                value={filters.agent_id}
                onValueChange={(value) => handleFilterChange('agent_id', value)}
              >
                <SelectTrigger data-testid="filter-agent">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os Agentes</SelectItem>
                  {agents.map(agent => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Data Início</Label>
            <Input
              type="date"
              value={filters.date_from}
              onChange={(e) => handleFilterChange('date_from', e.target.value)}
              data-testid="filter-date-from"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Data Fim</Label>
            <Input
              type="date"
              value={filters.date_to}
              onChange={(e) => handleFilterChange('date_to', e.target.value)}
              data-testid="filter-date-to"
            />
          </div>
        </div>
      )}
    </div>
  );
};
