import React, { useState, useEffect, useCallback } from 'react';
import { format, parseISO, formatDistanceToNow } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle, XCircle, Clock, AlertTriangle, User, Calendar,
  Edit, X, Loader2, RefreshCw, FileText, ChevronDown, ChevronUp
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { Label } from './ui/label';
import { appointmentsAPI } from '../utils/api';
import { toast } from 'sonner';

// Status config
const statusConfig = {
  pending: { label: 'Pendente', color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400', icon: Clock },
  approved: { label: 'Aprovado', color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400', icon: CheckCircle },
  rejected: { label: 'Rejeitado', color: 'bg-red-500/10 text-red-600 dark:text-red-400', icon: XCircle },
  auto_approved: { label: 'Auto-aprovado', color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400', icon: CheckCircle },
};

const requestTypeConfig = {
  edit: { label: 'Edição', color: 'bg-primary/10 text-primary', icon: Edit },
  cancel: { label: 'Cancelamento', color: 'bg-red-500/10 text-red-600 dark:text-red-400', icon: X },
};

// Card de solicitação
const RequestCard = ({ request, onApprove, onReject, isProcessing }) => {
  const [expanded, setExpanded] = useState(false);
  const status = statusConfig[request.status] || statusConfig.pending;
  const type = requestTypeConfig[request.request_type] || requestTypeConfig.edit;
  const StatusIcon = status.icon;
  const TypeIcon = type.icon;
  const isPending = request.status === 'pending';
  
  // Verificar mudanças propostas
  const changes = [];
  if (request.new_first_name) changes.push({ field: 'Nome', value: request.new_first_name });
  if (request.new_last_name) changes.push({ field: 'Sobrenome', value: request.new_last_name });
  if (request.new_protocol_number) changes.push({ field: 'Protocolo', value: request.new_protocol_number });
  if (request.new_additional_protocols?.length > 0) changes.push({ field: 'Protocolos Adicionais', value: request.new_additional_protocols.join(', ') });
  if (request.new_date) changes.push({ field: 'Nova Data', value: format(parseISO(request.new_date), 'dd/MM/yyyy') });
  if (request.new_time_slot) changes.push({ field: 'Novo Horário', value: request.new_time_slot });
  if (request.new_notes) changes.push({ field: 'Observações', value: request.new_notes });
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`
        p-4 rounded-xl border transition-all duration-200
        ${isPending ? 'border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-900/10' : 'border-border bg-card'}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {/* Ícone do tipo */}
          <div className={`p-2 rounded-lg ${type.color}`}>
            <TypeIcon className="w-5 h-5" />
          </div>
          
          <div className="flex-1">
            {/* Info do agendamento */}
            {request.appointment && (
              <div className="mb-2">
                <h3 className="font-semibold text-foreground">
                  {request.appointment.first_name} {request.appointment.last_name}
                </h3>
                <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                  <Calendar className="w-4 h-4" />
                  <span>{format(parseISO(request.appointment.date), 'dd/MM/yyyy')} às {request.appointment.time_slot}</span>
                </div>
              </div>
            )}
            
            {/* Solicitante */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="w-4 h-4" />
              <span>Solicitado por: <span className="font-medium text-foreground">{request.requested_by_name}</span></span>
            </div>
            
            {/* Tempo */}
            <p className="text-xs text-muted-foreground mt-1">
              {formatDistanceToNow(parseISO(request.created_at), { addSuffix: true, locale: ptBR })}
            </p>
          </div>
        </div>
        
        {/* Status badge */}
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${status.color}`}>
          <StatusIcon className="w-3.5 h-3.5" />
          {status.label}
        </div>
      </div>
      
      {/* Motivo */}
      {request.reason && (
        <div className="mt-3 p-3 bg-muted/50 rounded-lg">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Motivo:</span> {request.reason}
          </p>
        </div>
      )}
      
      {/* Mudanças propostas (expandível) */}
      {request.request_type === 'edit' && changes.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 text-sm text-primary hover:underline"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {expanded ? 'Ocultar mudanças' : `Ver ${changes.length} mudança(s) proposta(s)`}
          </button>
          
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="mt-2 p-3 bg-primary/5 rounded-lg border border-primary/20 space-y-2">
                  {changes.map((change, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-muted-foreground min-w-[120px]">{change.field}:</span>
                      <span className="text-foreground">{change.value}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
      
      {/* Review notes (se já processado) */}
      {request.review_notes && (
        <div className="mt-3 p-3 bg-muted/50 rounded-lg">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">Nota da revisão:</span> {request.review_notes}
          </p>
        </div>
      )}
      
      {/* Ações (apenas para pendentes) */}
      {isPending && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onReject(request)}
            disabled={isProcessing}
            className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            <XCircle className="w-4 h-4 mr-1" />
            Rejeitar
          </Button>
          <Button
            size="sm"
            onClick={() => onApprove(request)}
            disabled={isProcessing}
            className="flex-1"
          >
            {isProcessing ? (
              <Loader2 className="w-4 h-4 mr-1 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-1" />
            )}
            Aprovar
          </Button>
        </div>
      )}
    </motion.div>
  );
};

// Modal de confirmação
const ConfirmModal = ({ isOpen, onClose, request, action, onConfirm }) => {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  
  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(request.id, action === 'approve', notes);
      onClose();
      setNotes('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao processar solicitação');
    } finally {
      setLoading(false);
    }
  };
  
  if (!request) return null;
  
  const isApprove = action === 'approve';
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isApprove ? (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-500" />
                Aprovar Solicitação
              </>
            ) : (
              <>
                <XCircle className="w-5 h-5 text-red-500" />
                Rejeitar Solicitação
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            {isApprove 
              ? 'A alteração será aplicada ao agendamento imediatamente.'
              : 'O solicitante será notificado sobre a rejeição.'
            }
          </DialogDescription>
        </DialogHeader>
        
        {/* Info da solicitação */}
        <div className="p-3 bg-muted/50 rounded-lg border border-border">
          <p className="font-medium text-foreground">
            {request.request_type === 'cancel' ? 'Cancelamento' : 'Edição'} de agendamento
          </p>
          {request.appointment && (
            <p className="text-sm text-muted-foreground mt-1">
              {request.appointment.first_name} {request.appointment.last_name} - {format(parseISO(request.appointment.date), 'dd/MM/yyyy')}
            </p>
          )}
          <p className="text-sm text-muted-foreground mt-1">
            Solicitado por: {request.requested_by_name}
          </p>
        </div>
        
        {/* Notas */}
        <div>
          <Label>Observações (opcional)</Label>
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={isApprove ? 'Adicione uma nota à aprovação...' : 'Explique o motivo da rejeição...'}
            className="mt-1"
            rows={3}
          />
        </div>
        
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
          <Button 
            onClick={handleConfirm}
            disabled={loading}
            variant={isApprove ? 'default' : 'destructive'}
          >
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isApprove ? 'Aprovar' : 'Rejeitar'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

// Componente Principal
export const ChangeRequestsPanel = () => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('pending');
  const [processingId, setProcessingId] = useState(null);
  
  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [modalAction, setModalAction] = useState('approve');
  
  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const response = await appointmentsAPI.getChangeRequests(filter === 'all' ? null : filter);
      setRequests(response.data);
    } catch (error) {
      toast.error('Erro ao carregar solicitações');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [filter]);
  
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  // Handlers
  const handleApprove = (request) => {
    setSelectedRequest(request);
    setModalAction('approve');
    setModalOpen(true);
  };
  
  const handleReject = (request) => {
    setSelectedRequest(request);
    setModalAction('reject');
    setModalOpen(true);
  };
  
  const handleConfirm = async (requestId, approved, notes) => {
    setProcessingId(requestId);
    try {
      await appointmentsAPI.reviewChangeRequest(requestId, approved, notes);
      toast.success(approved ? 'Solicitação aprovada!' : 'Solicitação rejeitada');
      fetchData();
    } finally {
      setProcessingId(null);
    }
  };
  
  // Contadores
  const pendingCount = requests.filter(r => r.status === 'pending').length;
  
  return (
    <div className="space-y-6" data-testid="change-requests-panel">
      {/* Header */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Solicitações de Alteração
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Revise e aprove/rejeite solicitações de edição e cancelamento
              </p>
            </div>
            
            <div className="flex items-center gap-3">
              {/* Filtro */}
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="h-10 px-3 rounded-lg border border-border bg-background text-sm focus:ring-2 focus:ring-primary/20"
                data-testid="requests-filter"
              >
                <option value="pending">Pendentes ({pendingCount})</option>
                <option value="approved">Aprovadas</option>
                <option value="rejected">Rejeitadas</option>
                <option value="all">Todas</option>
              </select>
              
              <Button variant="ghost" size="icon" onClick={fetchData} title="Atualizar">
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : requests.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-12 h-12 mx-auto text-muted-foreground/30 mb-3" />
              <p className="text-muted-foreground">
                {filter === 'pending' 
                  ? 'Nenhuma solicitação pendente de aprovação'
                  : 'Nenhuma solicitação encontrada'
                }
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <AnimatePresence mode="popLayout">
                {requests.map(request => (
                  <RequestCard
                    key={request.id}
                    request={request}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    isProcessing={processingId === request.id}
                  />
                ))}
              </AnimatePresence>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Modal de confirmação */}
      <ConfirmModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        request={selectedRequest}
        action={modalAction}
        onConfirm={handleConfirm}
      />
    </div>
  );
};

export default ChangeRequestsPanel;
