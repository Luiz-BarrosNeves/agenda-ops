import React, { useState, useEffect } from 'react';
import { presenceAPI } from '../utils/api';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Users, Wifi, WifiOff } from 'lucide-react';

export const AgentPresenceIndicator = ({ agentId, agentName, showLabel = true }) => {
  const [isOnline, setIsOnline] = useState(false);
  const [lastSeen, setLastSeen] = useState(null);

  // Este componente é para exibição individual, os dados vêm do pai

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2.5 h-2.5 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-muted-foreground/30'}`}></span>
      {showLabel && (
        <span className="text-xs text-muted-foreground">
          {isOnline ? 'Online' : lastSeen ? `Visto ${formatDistanceToNow(parseISO(lastSeen), { addSuffix: true, locale: ptBR })}` : 'Offline'}
        </span>
      )}
    </div>
  );
};

export const AgentPresenceList = ({ compact = false }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPresence();
    const interval = setInterval(loadPresence, 30000); // Atualizar a cada 30s
    return () => clearInterval(interval);
  }, []);

  const loadPresence = async () => {
    try {
      const response = await presenceAPI.getAgentsPresence();
      setAgents(response.data);
    } catch (error) {
      console.error('Erro ao carregar presença:', error);
    } finally {
      setLoading(false);
    }
  };

  const onlineCount = agents.filter(a => a.is_online).length;
  const totalCount = agents.length;

  if (loading) {
    return <div className="text-sm text-muted-foreground">Carregando...</div>;
  }

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <Users className="w-4 h-4 text-muted-foreground" />
        <span className="text-green-600 dark:text-green-400 font-medium">{onlineCount}</span>
        <span className="text-muted-foreground/50">/</span>
        <span className="text-foreground">{totalCount}</span>
        <span className="text-muted-foreground">online</span>
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="agent-presence-list">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Users className="w-4 h-4" />
          Agentes
        </h3>
        <span className="text-xs text-muted-foreground">
          {onlineCount} de {totalCount} online
        </span>
      </div>

      <div className="space-y-2">
        {agents.map((agent) => (
          <div 
            key={agent.id} 
            className={`flex items-center justify-between p-2 rounded-lg ${agent.is_online ? 'bg-green-50 dark:bg-green-900/20' : 'bg-muted/50'}`}
            data-testid={`agent-presence-${agent.id}`}
          >
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${agent.is_online ? 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200' : 'bg-muted text-muted-foreground'}`}>
                {agent.name.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{agent.name}</p>
                {agent.last_seen && !agent.is_online && (
                  <p className="text-xs text-muted-foreground">
                    Visto {formatDistanceToNow(parseISO(agent.last_seen), { addSuffix: true, locale: ptBR })}
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1">
              {agent.is_online ? (
                <Wifi className="w-4 h-4 text-green-600 dark:text-green-400" />
              ) : (
                <WifiOff className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
