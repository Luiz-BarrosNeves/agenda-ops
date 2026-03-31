import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usersAPI, reportsAPI } from '../utils/api';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { ArrowLeft, Users, Clock, AlertTriangle, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { toast } from 'sonner';
import { ExtraHoursManager } from './ExtraHoursManager';
import { AgentPresenceList } from './AgentPresence';

export const SupervisorDashboard = () => {
  const [stats, setStats] = useState([]);
  const [weeklyHours, setWeeklyHours] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [teamRes, weeklyRes] = await Promise.all([
        usersAPI.getTeamStats(),
        reportsAPI.getWeeklyHours()
      ]);
      setStats(teamRes.data);
      setWeeklyHours(weeklyRes.data);
    } catch (error) {
      toast.error('Erro ao carregar estatísticas');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const overloadedUsers = stats.filter(s => s.status === 'overloaded');
  const availableUsers = stats.filter(s => s.status === 'available');
  const totalAppointments = stats.reduce((acc, s) => acc + (s.total_appointments || 0), 0);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">Carregando...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="supervisor-dashboard">
      <div className="max-w-7xl mx-auto p-6">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="mb-4"
            data-testid="back-to-dashboard-button"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar para Agenda
          </Button>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            Painel do Supervisor
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Visão geral da carga de trabalho da equipe
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Users className="w-4 h-4" />
                Total de Agentes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold text-foreground">{stats.length}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Agendamentos Hoje
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold text-foreground">{totalAppointments}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Sobrecarregados
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold text-red-600 dark:text-red-400">{overloadedUsers.length}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Disponíveis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold text-green-600 dark:text-green-400">{availableUsers.length}</p>
            </CardContent>
          </Card>
        </div>

        {/* Horários Extras */}
        <div className="mb-6">
          <ExtraHoursManager />
        </div>

        {/* Presença de Agentes */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Presença de Agentes</CardTitle>
          </CardHeader>
          <CardContent>
            <AgentPresenceList />
          </CardContent>
        </Card>

        {/* Gráfico de carga */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Agendamentos por Agente (Hoje)</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_appointments" fill="#0F172A" name="Agendamentos" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Saldo Semanal */}
        {weeklyHours && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Saldo Semanal de Horas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {weeklyHours.agents?.map(agent => (
                  <div key={agent.id} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-medium ${agent.is_online ? 'bg-green-500' : 'bg-muted-foreground'}`}>
                        {agent.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-foreground">{agent.name}</p>
                        <p className="text-xs text-muted-foreground">{agent.emitidos} emitidos • {agent.hours_worked}h trabalhadas</p>
                      </div>
                    </div>
                    <div className={`text-right px-3 py-1 rounded ${agent.balance >= 0 ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                      <p className={`text-lg font-semibold ${agent.balance >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {agent.balance >= 0 ? '+' : ''}{agent.balance}h
                      </p>
                      <p className="text-xs text-muted-foreground">Meta: {agent.weekly_target}h</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {overloadedUsers.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-red-600 dark:text-red-400">Agentes Sobrecarregados</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {overloadedUsers.map(user => (
                    <div key={user.user_id} className="flex items-center justify-between p-3 bg-red-500/10 rounded-md" data-testid="overloaded-user">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-red-400 flex items-center justify-center text-white font-medium">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{user.name}</p>
                          <p className="text-xs text-muted-foreground">{user.total_appointments} agendamentos</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {availableUsers.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-green-600 dark:text-green-400">Agentes Disponíveis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {availableUsers.map(user => (
                    <div key={user.user_id} className="flex items-center justify-between p-3 bg-green-500/10 rounded-md" data-testid="available-user">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-400 flex items-center justify-center text-white font-medium">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{user.name}</p>
                          <p className="text-xs text-muted-foreground">{user.total_appointments} agendamentos</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
