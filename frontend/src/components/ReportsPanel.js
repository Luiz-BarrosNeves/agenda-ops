import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { reportsAPI } from '../utils/api';
import { toast } from 'sonner';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { FileText, Clock, Users, TrendingUp, Download, Calendar, BarChart3, Loader2 } from 'lucide-react';
import { ReportSkeleton, EmptyState } from './ui/loading-states';

const statusLabels = {
  pendente_atribuicao: 'Pendentes',
  confirmado: 'Confirmados',
  emitido: 'Emitidos',
  reagendar: 'Reagendar',
  presencial: 'Presencial',
  cancelado: 'Cancelados',
};

const statusColors = {
  pendente_atribuicao: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200',
  confirmado: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200',
  emitido: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200',
  reagendar: 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-200',
  presencial: 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-200',
  cancelado: 'bg-muted text-muted-foreground',
};

export const ReportsPanel = ({ isOpen, onClose }) => {
  const [reportType, setReportType] = useState('daily');
  const [selectedDate, setSelectedDate] = useState(format(new Date(), 'yyyy-MM-dd'));
  const [dailyReport, setDailyReport] = useState(null);
  const [weeklyReport, setWeeklyReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadReport();
    }
  }, [isOpen, reportType, selectedDate]);

  const loadReport = async () => {
    setLoading(true);
    try {
      if (reportType === 'daily') {
        const response = await reportsAPI.getDaily(selectedDate);
        setDailyReport(response.data);
      } else {
        const response = await reportsAPI.getWeeklyHours();
        setWeeklyReport(response.data);
      }
    } catch (error) {
      toast.error('Erro ao carregar relatório');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = async () => {
    setExporting(true);
    try {
      let response;
      let filename;
      
      if (reportType === 'daily') {
        response = await reportsAPI.exportDailyCSV(selectedDate);
        filename = `relatorio_diario_${selectedDate}.csv`;
      } else {
        response = await reportsAPI.exportWeeklyHoursCSV();
        filename = `saldo_horas_semanal.csv`;
      }
      
      // Criar download do blob
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
      URL.revokeObjectURL(link.href);
      
      toast.success('Relatório exportado com sucesso!');
    } catch (error) {
      toast.error('Erro ao exportar relatório');
      console.error(error);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" data-testid="reports-panel">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold tracking-tight flex items-center gap-2 text-foreground">
            <FileText className="w-6 h-6" />
            Relatórios
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Visualize relatórios de atendimentos e horas trabalhadas
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-4 mt-4">
          <div className="flex gap-2">
            <Button
              variant={reportType === 'daily' ? 'default' : 'outline'}
              onClick={() => setReportType('daily')}
              size="sm"
            >
              <Calendar className="w-4 h-4 mr-2" />
              Diário
            </Button>
            <Button
              variant={reportType === 'weekly' ? 'default' : 'outline'}
              onClick={() => setReportType('weekly')}
              size="sm"
            >
              <Clock className="w-4 h-4 mr-2" />
              Saldo Semanal
            </Button>
          </div>

          {reportType === 'daily' && (
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-auto"
            />
          )}

          <Button 
            variant="outline" 
            size="sm" 
            onClick={exportToCSV} 
            className="ml-auto"
            disabled={exporting}
            data-testid="export-csv-btn"
          >
            {exporting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            Exportar CSV
          </Button>
        </div>

        {loading ? (
          <ReportSkeleton />
        ) : reportType === 'daily' && dailyReport ? (
          <div className="space-y-6 mt-6">
            {/* Resumo */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-muted/50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-foreground">{dailyReport.summary.total_appointments}</p>
                <p className="text-sm text-muted-foreground">Total de Agendamentos</p>
              </div>
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-blue-900 dark:text-blue-200">{dailyReport.summary.by_status.emitido || 0}</p>
                <p className="text-sm text-blue-600 dark:text-blue-400">Emitidos</p>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-green-900 dark:text-green-200">{dailyReport.summary.total_hours_worked}h</p>
                <p className="text-sm text-green-600 dark:text-green-400">Horas Trabalhadas</p>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-purple-900 dark:text-purple-200">{dailyReport.summary.auto_assigned}</p>
                <p className="text-sm text-purple-600 dark:text-purple-400">Auto-atribuídos</p>
              </div>
            </div>

            {/* Por Status */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Por Status</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(dailyReport.summary.by_status).map(([status, count]) => (
                  <div key={status} className={`px-3 py-1.5 rounded-full text-sm font-medium ${statusColors[status] || 'bg-muted'}`}>
                    {statusLabels[status] || status}: {count}
                  </div>
                ))}
              </div>
            </div>

            {/* Por Agente */}
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-3">Por Agente</h3>
              <div className="space-y-2">
                {dailyReport.agents.map((agent) => (
                  <div key={agent.id} className="bg-card border border-border rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-semibold text-primary">
                        {agent.name.charAt(0)}
                      </div>
                      <div>
                        <p className="font-medium text-foreground">{agent.name}</p>
                        <p className="text-sm text-muted-foreground">{agent.total} agendamentos</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-sm">
                      <div className="text-center">
                        <p className="font-semibold text-blue-600 dark:text-blue-400">{agent.by_status.emitido || 0}</p>
                        <p className="text-muted-foreground">Emitidos</p>
                      </div>
                      <div className="text-center">
                        <p className="font-semibold text-green-600 dark:text-green-400">{agent.hours_worked}h</p>
                        <p className="text-muted-foreground">Horas</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : reportType === 'weekly' && weeklyReport ? (
          <div className="space-y-6 mt-6">
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground">
                Semana de {format(parseISO(weeklyReport.week_start), "dd 'de' MMMM", { locale: ptBR })} a {format(parseISO(weeklyReport.week_end), "dd 'de' MMMM", { locale: ptBR })}
              </p>
            </div>

            <div className="space-y-3">
              {weeklyReport.agents.map((agent) => {
                const isNegative = agent.balance < 0;
                const isPositive = agent.balance > 0;
                
                return (
                  <div key={agent.id} className="bg-card border border-border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center font-semibold text-primary">
                          {agent.name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{agent.name}</p>
                          <div className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full ${agent.is_online ? 'bg-green-500' : 'bg-muted-foreground/30'}`}></span>
                            <span className="text-xs text-muted-foreground">{agent.is_online ? 'Online' : 'Offline'}</span>
                          </div>
                        </div>
                      </div>
                      <div className={`text-right px-3 py-1 rounded-lg ${isNegative ? 'bg-red-50 dark:bg-red-900/20' : isPositive ? 'bg-green-50 dark:bg-green-900/20' : 'bg-muted/50'}`}>
                        <p className={`text-lg font-bold ${isNegative ? 'text-red-600 dark:text-red-400' : isPositive ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}>
                          {isPositive ? '+' : ''}{agent.balance}h
                        </p>
                        <p className="text-xs text-muted-foreground">Saldo</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-center text-sm">
                      <div>
                        <p className="font-semibold text-foreground">{agent.emitidos}</p>
                        <p className="text-muted-foreground">Emitidos</p>
                      </div>
                      <div>
                        <p className="font-semibold text-foreground">{agent.hours_worked}h</p>
                        <p className="text-muted-foreground">Trabalhadas</p>
                      </div>
                      <div>
                        <p className="font-semibold text-foreground">{agent.weekly_target}h</p>
                        <p className="text-muted-foreground">Meta</p>
                      </div>
                    </div>
                    
                    {/* Barra de progresso */}
                    <div className="mt-3">
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className={`h-full ${agent.hours_worked >= agent.weekly_target ? 'bg-green-500' : 'bg-primary'}`}
                          style={{ width: `${Math.min((agent.hours_worked / agent.weekly_target) * 100, 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <EmptyState 
            icon={BarChart3}
            title="Selecione um tipo de relatório"
            description="Escolha entre relatório diário ou saldo semanal para ver os dados."
          />
        )}

        <div className="flex justify-end pt-4 border-t border-border mt-4">
          <Button variant="outline" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};
