import { useAuth } from '../context/AuthContext';
import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Textarea } from './ui/textarea';
import { Switch } from './ui/switch';
import { appointmentsAPI, templatesAPI } from '../utils/api';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { AlertCircle, CheckCircle, Upload, X, Plus, FileText, Download, Bookmark, BookmarkPlus } from 'lucide-react';
import axios from 'axios';
import { TemplateSelector, TemplateFormModal } from './TemplateManager';
import "../styles/date-calendar-dark.css";

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';

export const AppointmentModal = ({ isOpen, onClose, appointment, initialData, onSave, userRole, onSubmitOverride }) => {
    const { user } = useAuth();
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    protocol_number: '',
    additional_protocols: [],
    has_chat: false,
    chat_platform: '',  // 'blip' ou 'chatpro'  
    date: format(new Date(), 'yyyy-MM-dd'),
    time_slot: '',
    notes: '',
    emission_system: null  // 'safeweb', 'serpro', ou null
  });
  const [statusData, setStatusData] = useState({ status: 'confirmado' });
  const [rescheduleReason, setRescheduleReason] = useState('');
  const [availableSlots, setAvailableSlots] = useState([]);
  const [newProtocol, setNewProtocol] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [checking, setChecking] = useState(false);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  
  // Template states
  const [templateSelectorOpen, setTemplateSelectorOpen] = useState(false);
  const [saveTemplateOpen, setSaveTemplateOpen] = useState(false);

  const isAgent = userRole === 'agente';
  const isEditingAssigned = appointment && appointment.user_id;
  const totalProtocols = 1 + formData.additional_protocols.length;
  const needsTwoSlots = totalProtocols >= 3;
  const canUseTemplates = ['televendas', 'comercial', 'supervisor', 'admin'].includes(userRole);

  // Lista padronizada de motivos de reagendamento
  const RESCHEDULE_REASONS = [
    { value: 'cliente_sem_documento', label: 'Cliente sem documento' },
    { value: 'cliente_nao_compareceu', label: 'Cliente não compareceu' },
    { value: 'dados_incorretos', label: 'Dados incorretos' },
    { value: 'problema_biometria', label: 'Problema na biometria' },
    { value: 'instabilidade_sistema', label: 'Instabilidade no sistema' },
    { value: 'solicitacao_cliente', label: 'Solicitação do cliente' },
    { value: 'outros', label: 'Outros' },
  ];

  // Limpar motivo ao mudar status
  useEffect(() => {
    if (statusData.status !== 'reagendar') setRescheduleReason('');
  }, [statusData.status]);
  const handleTemplateSelect = (templateData) => {
    setFormData(prev => ({
      ...prev,
      first_name: templateData.first_name,
      last_name: templateData.last_name,
      has_chat: templateData.has_chat,
      chat_platform: templateData.chat_platform || '',
      notes: templateData.notes || prev.notes,
      date: templateData.suggested_date || prev.date,
      time_slot: templateData.suggested_time_slot || prev.time_slot
    }));
    
    // Se a data mudou, recarregar slots
    if (templateData.suggested_date && templateData.suggested_date !== formData.date) {
      setFormData(prev => ({ ...prev, date: templateData.suggested_date }));
    }
  };

  useEffect(() => {
    if (appointment) {
      setFormData({
        first_name: appointment.first_name,
        last_name: appointment.last_name,
        protocol_number: appointment.protocol_number,
        additional_protocols: appointment.additional_protocols || [],
        has_chat: appointment.has_chat,
        chat_platform: appointment.chat_platform || '',
        date: appointment.date,
        time_slot: appointment.time_slot,
        notes: appointment.notes || ''
      });
      setStatusData({ status: appointment.status });
    } else if (initialData) {
      // Pré-preencher com dados iniciais (quando clica em slot livre)
      setFormData(prev => ({
        ...prev,
        date: initialData.date || format(new Date(), 'yyyy-MM-dd'),
        time_slot: initialData.time_slot || ''
      }));
    } else {
      setFormData({
        first_name: '',
        last_name: '',
        protocol_number: '',
        additional_protocols: [],
        has_chat: false,
        chat_platform: '',
        date: format(new Date(), 'yyyy-MM-dd'),
        time_slot: '',
        notes: ''
      });
    }
  }, [appointment, isOpen, initialData]);


  // Busca slots sempre que modal abre (novo ou edição) e quando data/emission_system mudam
  useEffect(() => {
    if (isOpen && formData.date) {
      fetchAvailableSlots();
    }
  }, [isOpen, formData.date, formData.emission_system]);

  // Busca slots disponíveis e inclui o horário atual do appointment se necessário
  const fetchAvailableSlots = async () => {
    setChecking(true);
    try {
      const response = await appointmentsAPI.getAvailableSlots(formData.date, formData.emission_system);
      let slots = response.data.available_slots || response.data || [];
      // Se estiver editando e o horário atual não está na lista, adiciona manualmente
      if (appointment && appointment.time_slot && !slots.some(s => s.time_slot === appointment.time_slot)) {
        slots = [
          ...slots,
          { time_slot: appointment.time_slot, available_agents: 0 }
        ];
      }
      setAvailableSlots(slots);
      if (slots.length > 0 && !formData.time_slot) {
        setFormData(prev => ({ ...prev, time_slot: slots[0].time_slot }));
      }
    } catch (error) {
      toast.error('Erro ao carregar horários disponíveis');
      setAvailableSlots([]);
    } finally {
      setChecking(false);
    }
  };

  const loadAvailableSlots = async () => {
    setChecking(true);
    try {
      const response = await appointmentsAPI.getAvailableSlots(formData.date, formData.emission_system);
      const slots = response.data.available_slots || response.data || [];
      setAvailableSlots(slots);
      if (slots.length > 0 && !formData.time_slot) {
        setFormData(prev => ({ ...prev, time_slot: slots[0].time_slot }));
      }
    } catch (error) {
      console.error('Erro ao carregar horários:', error);
      setAvailableSlots([]);
    } finally {
      setChecking(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const newFiles = Array.from(e.dataTransfer.files);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setUploadedFiles(prev => [...prev, ...newFiles]);
    }
  };

  const handleRemoveFile = (index) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleAddProtocol = () => {
    if (newProtocol.trim()) {
      setFormData({
        ...formData,
        additional_protocols: [...formData.additional_protocols, newProtocol.trim()]
      });
      setNewProtocol('');
    }
  };

  const handleRemoveProtocol = (index) => {
    setFormData({
      ...formData,
      additional_protocols: formData.additional_protocols.filter((_, i) => i !== index)
    });
  };

  const handleDownload = async (filename) => {
    setDownloading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/appointments/${appointment.id}/download/${filename}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Download iniciado!');
    } catch (error) {
      toast.error('Erro ao baixar documento');
    } finally {
      setDownloading(false);
    }
  };

  const handleSubmit = async (e) => {
    // Se status for reagendar, motivo é obrigatório
    if (statusData.status === 'reagendar' && !rescheduleReason) {
      toast.error('Selecione o motivo do reagendamento');
      return;
    }
    e.preventDefault();

    if (!appointment && availableSlots.length === 0) {
      toast.error('Não há horários disponíveis para esta data!');
      return;
    }

    // Validar plataforma de chat se has_chat estiver ativo
    if (formData.has_chat && !formData.chat_platform) {
      toast.error('Selecione a plataforma de chat (Blip ou ChatPro)');
      return;
    }

    // Fluxo de solicitação (change-request)
    if (onSubmitOverride && appointment) {
      setSaving(true);
      try {
        console.log('[LOG] Chamando onSubmitOverride', formData, { appointment, userRole, user, statusData });
        await onSubmitOverride(formData, { appointment, userRole, user, statusData });
        toast.success('Solicitação enviada para aprovação');
        await onSave?.();
        onClose();
        return;
      } catch (error) {
        console.error('[LOG] Erro onSubmitOverride', error);
        toast.error(error?.response?.data?.detail || 'Erro ao enviar solicitação');
        return;
      } finally {
        setSaving(false);
      }
    }

    // Fluxo normal (supervisor, etc)
    setSaving(true);
    try {
      let appointmentId;

      if (appointment) {
        if (isAgent && isEditingAssigned) {
          await appointmentsAPI.update(appointment.id, {
            ...statusData,
            reschedule_reason: statusData.status === 'reagendar' ? rescheduleReason : undefined
          });
          appointmentId = appointment.id;
        } else {
          await appointmentsAPI.update(appointment.id, {
            ...formData,
            status: statusData.status,
            reschedule_reason: statusData.status === 'reagendar' ? rescheduleReason : undefined
          });
          appointmentId = appointment.id;
        }
      } else {
        const response = await appointmentsAPI.create({
          ...formData,
          status: statusData.status,
          reschedule_reason: statusData.status === 'reagendar' ? rescheduleReason : undefined
        });
        appointmentId = response.data.id;
      }

      if (uploadedFiles.length > 0 && !appointment) {
        await appointmentsAPI.uploadDocuments(appointmentId, uploadedFiles);
      }

      onSave();
      onClose();
      
      if (needsTwoSlots && !appointment) {
        toast.success(`Agendamento criado! Como são ${totalProtocols} protocolos, foram reservados 2 horários consecutivos.`);
      } else {
        toast.success('Agendamento salvo com sucesso!');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar agendamento');
      console.error(error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto" data-testid="appointment-modal">
        <DialogHeader>
          <DialogTitle className="text-2xl font-semibold tracking-tight text-foreground">
            {appointment ? 'Editar/Reagendar Agendamento' : 'Novo Agendamento'}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            {appointment 
                ? isAgent && isEditingAssigned 
                  ? statusData.status === 'reagendar' 
                    ? 'Escolha nova data e horário. O agendamento ficará pendente de atribuição.'
                    : 'Atualize o status do atendimento.'
                  : 'Edite os dados do agendamento.'
                : 'Preencha os dados. O supervisor atribuirá um agente disponível.'}
          </DialogDescription>
        </DialogHeader>

        {/* Botões de Template - só aparecem na criação de novo agendamento */}
        {!appointment && canUseTemplates && (
          <div className="flex items-center gap-2 mt-4 p-3 bg-muted/50 rounded-lg border border-border">
            <Bookmark className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground flex-1">Agilize o preenchimento:</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setTemplateSelectorOpen(true)}
              data-testid="use-template-btn"
            >
              <Bookmark className="w-4 h-4 mr-2" />
              Usar Template
            </Button>
            {formData.first_name && formData.last_name && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setSaveTemplateOpen(true)}
                data-testid="save-template-btn"
              >
                <BookmarkPlus className="w-4 h-4 mr-2" />
                Salvar como Template
              </Button>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6 mt-6">
          {isAgent && isEditingAssigned ? (
            <>
              <div className="space-y-2">
                <Label htmlFor="status" className="text-sm font-medium text-foreground">Status do Atendimento *</Label>
                <Select
                  value={statusData.status}
                  onValueChange={(value) => setStatusData({ status: value })}
                >
                  <SelectTrigger data-testid="modal-status-select" className="h-11">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="confirmado">Confirmado</SelectItem>
                    <SelectItem value="emitido">Emitido</SelectItem>
                    <SelectItem value="reagendar">Reagendar</SelectItem>
                    <SelectItem value="presencial">Presencial</SelectItem>
                    <SelectItem value="cancelado">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
                {statusData.status === 'reagendar' && (
                  <div className="mt-3">
                    <Label htmlFor="reschedule_reason" className="text-sm font-medium text-foreground">Motivo do Reagendamento *</Label>
                    <Select
                      value={rescheduleReason}
                      onValueChange={setRescheduleReason}
                      required
                    >
                      <SelectTrigger className="h-11">
                        <SelectValue placeholder="Selecione o motivo" />
                      </SelectTrigger>
                      <SelectContent>
                        {RESCHEDULE_REASONS.map((reason) => (
                          <SelectItem key={reason.value} value={reason.value}>{reason.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              <div className="p-4 bg-primary/5 rounded-lg border border-primary/20 mt-4">
                <h3 className="font-semibold text-primary mb-3">Informações do Cliente</h3>
                <div className="space-y-2 text-sm text-foreground">
                  <p><strong>Nome:</strong> {appointment.first_name} {appointment.last_name}</p>
                  <p><strong>Protocolo:</strong> {appointment.protocol_number}</p>
                  {appointment.additional_protocols?.length > 0 && (
                    <p><strong>Protocolos Adicionais:</strong> {appointment.additional_protocols.join(', ')}</p>
                  )}
                  <p><strong>Data:</strong> {format(new Date(appointment.date), 'dd/MM/yyyy')}</p>
                  <p><strong>Horário:</strong> {appointment.time_slot}</p>
                  <p><strong>Chat:</strong> {appointment.has_chat ? 'Sim' : 'Não'}</p>
                  {appointment.notes && <p><strong>Obs:</strong> {appointment.notes}</p>}
                </div>
                {appointment.document_urls?.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <p className="text-sm font-medium text-primary">Documentos anexados:</p>
                    {appointment.document_urls.map((filename, idx) => (
                      <Button
                        key={idx}
                        type="button"
                        variant="outline"
                        onClick={() => handleDownload(filename)}
                        disabled={downloading}
                        className="w-full justify-start text-left"
                        size="sm"
                      >
                        <Download className="w-4 h-4 mr-2 flex-shrink-0" />
                        <span className="truncate">{filename}</span>
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name" className="text-sm font-medium text-foreground">Nome *</Label>
                  <Input
                    id="first_name"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    required
                    data-testid="modal-firstname-input"
                    placeholder="Ex: João"
                    className="h-11"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="last_name" className="text-sm font-medium text-foreground">Sobrenome *</Label>
                  <Input
                    id="last_name"
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    required
                    data-testid="modal-lastname-input"
                    placeholder="Ex: Silva"
                    className="h-11"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="protocol_number" className="text-sm font-medium text-foreground">Número do Protocolo *</Label>
                <Input
                  id="protocol_number"
                  value={formData.protocol_number}
                  onChange={(e) => setFormData({ ...formData, protocol_number: e.target.value })}
                  required
                  data-testid="modal-protocol-input"
                  placeholder="Ex: 2025-001234"
                  className="h-11"
                />
              </div>

              {/* Sistema de Emissão (Safeweb/Serpro) */}
              <div className="space-y-2">
                <Label className="text-sm font-medium text-foreground">Sistema de Emissão</Label>
                <Select
                  value={formData.emission_system || 'none'}
                  onValueChange={(value) => {
                    setFormData({ ...formData, emission_system: value === 'none' ? null : value, time_slot: '' });
                  }}
                >
                  <SelectTrigger data-testid="emission-system-select" className="h-11">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Consulti (padrão)</SelectItem>
                    <SelectItem value="safeweb">
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                        Safeweb
                      </span>
                    </SelectItem>
                    <SelectItem value="serpro">
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                        Serpro
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {formData.emission_system 
                    ? `Apenas agentes com permissão ${formData.emission_system.toUpperCase()} podem atender` 
                    : 'Qualquer agente pode atender'}
                </p>
              </div>

              <div className="space-y-3">
                <Label className="text-sm font-medium text-foreground">Protocolos Adicionais</Label>
                <div className="flex gap-2">
                  <Input
                    value={newProtocol}
                    onChange={(e) => setNewProtocol(e.target.value)}
                    placeholder="Digite outro protocolo"
                    onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddProtocol())}
                    className="h-11 dark:border-slate-600 dark:focus-visible:ring-slate-500 dark:focus-visible:border-slate-500 dark:bg-slate-900 dark:text-cyan-100"
                  />
                  <Button
                    type="button"
                    onClick={handleAddProtocol}
                    variant="outline"
                    className="px-4"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                {formData.additional_protocols.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {formData.additional_protocols.map((proto, idx) => (
                      <div key={idx} className="flex items-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm">
                        <span>{proto}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveProtocol(idx)}
                          className="hover:text-primary/80"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {needsTwoSlots && (
                <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-700 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-amber-900 dark:text-amber-200">
                        Atenção: {totalProtocols} protocolos
                      </p>
                      <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                        Este agendamento ocupará 2 horários consecutivos (20min cada)
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date" className="text-sm font-medium text-foreground">Data *</Label>
                  <Input
                    id="date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    min={format(new Date(), 'yyyy-MM-dd')}
                    required
                    data-testid="modal-date-input"
                    className="h-11"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="time_slot" className="text-sm font-medium text-foreground">
                    Horário (20 min) * {checking && '(Carregando...)'}
                  </Label>
                  <Select
                    value={formData.time_slot}
                    onValueChange={(value) => setFormData({ ...formData, time_slot: value })}
                    disabled={
                      checking ||
                      availableSlots.length === 0 ||
                      (isAgent && appointment && appointment.user_id !== user?.id)
                    }
                  >
                    <SelectTrigger data-testid="modal-time-select" className="h-11">
                      <SelectValue placeholder="Selecione" />
                    </SelectTrigger>
                    <SelectContent className="max-h-60">
                      {availableSlots.map(slot => (
                        <SelectItem key={slot.time_slot} value={slot.time_slot}>
                          {slot.time_slot} ({slot.available_agents} agente{slot.available_agents > 1 ? 's' : ''} livre{slot.available_agents > 1 ? 's' : ''})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
                <div>
                  <Label htmlFor="has_chat" className="text-sm font-medium text-foreground cursor-pointer">
                    Cliente tem chat
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">Indica se o cliente está online no chat</p>
                </div>
                <Switch
                  id="has_chat"
                  checked={formData.has_chat}
                  onCheckedChange={(checked) => setFormData({ ...formData, has_chat: checked, chat_platform: checked ? formData.chat_platform : '' })}
                />
              </div>

              {/* Seleção de plataforma de chat (obrigatório quando has_chat = true) */}
              {formData.has_chat && (
                <div className="space-y-2 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
                  <Label className="text-sm font-medium text-foreground">
                    Plataforma de Chat *
                  </Label>
                  <p className="text-xs text-muted-foreground mb-3">
                    Selecione a plataforma onde o cliente está conectado
                  </p>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, chat_platform: 'blip' })}
                      className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                        formData.chat_platform === 'blip'
                          ? 'border-blue-500 bg-blue-100 dark:bg-blue-900/40'
                          : 'border-border hover:border-blue-300 bg-background'
                      }`}
                      data-testid="chat-platform-blip"
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          formData.chat_platform === 'blip' 
                            ? 'bg-blue-500 text-white' 
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          <span className="font-bold text-lg">B</span>
                        </div>
                        <span className={`font-medium ${
                          formData.chat_platform === 'blip' ? 'text-blue-700 dark:text-blue-300' : 'text-foreground'
                        }`}>
                          Blip
                        </span>
                      </div>
                    </button>
                    
                    <button
                      type="button"
                      onClick={() => setFormData({ ...formData, chat_platform: 'chatpro' })}
                      className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                        formData.chat_platform === 'chatpro'
                          ? 'border-green-500 bg-green-100 dark:bg-green-900/40'
                          : 'border-border hover:border-green-300 bg-background'
                      }`}
                      data-testid="chat-platform-chatpro"
                    >
                      <div className="flex flex-col items-center gap-2">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          formData.chat_platform === 'chatpro' 
                            ? 'bg-green-500 text-white' 
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          <span className="font-bold text-lg">C</span>
                        </div>
                        <span className={`font-medium ${
                          formData.chat_platform === 'chatpro' ? 'text-green-700 dark:text-green-300' : 'text-foreground'
                        }`}>
                          ChatPro
                        </span>
                      </div>
                    </button>
                  </div>
                  {formData.has_chat && !formData.chat_platform && (
                    <p className="text-xs text-red-500 dark:text-red-400 mt-2 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      Selecione uma plataforma para continuar
                    </p>
                  )}
                </div>
              )}

              {!appointment && (
                <div className="space-y-2">
                  <Label className="text-sm font-medium text-foreground">Documentos do Cliente *</Label>
                  <div
                    className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                      dragActive ? 'border-primary bg-primary/5' : 'border-border bg-muted/30'
                    }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                  >
                    <Upload className="w-10 h-10 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground mb-2">Arraste os arquivos aqui ou</p>
                    <label className="cursor-pointer">
                      <span
                        className="text-primary hover:text-primary/80 font-medium"
                        onClick={e => {
                          e.preventDefault();
                          document.getElementById('modal-file-input')?.click();
                        }}
                      >clique para selecionar</span>
                      <input
                        id="modal-file-input"
                        type="file"
                        className="hidden"
                        onChange={handleFileChange}
                        accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                        multiple
                        data-testid="modal-file-input"
                      />
                    </label>
                    <p className="text-xs text-muted-foreground mt-2">PDF, DOC, DOCX, JPG, PNG (múltiplos arquivos permitidos)</p>
                  </div>
                  
                  {uploadedFiles.length > 0 && (
                    <div className="space-y-2 mt-3">
                      <p className="text-sm font-medium text-foreground">{uploadedFiles.length} arquivo(s) selecionado(s):</p>
                      {uploadedFiles.map((file, idx) => (
                        <div key={idx} className="flex items-center justify-between bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg px-3 py-2">
                          <div className="flex items-center gap-2">
                            <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
                            <div>
                              <p className="text-sm font-medium text-foreground">{file.name}</p>
                              <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(2)} KB</p>
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveFile(idx)}
                            className="text-destructive hover:text-destructive/80 p-1"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="notes" className="text-sm font-medium text-foreground">Observações</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  data-testid="modal-notes-input"
                  placeholder="Informações adicionais sobre o agendamento"
                  className="resize-none"
                />
              </div>
            </>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={onClose} data-testid="modal-cancel-button" className="px-6">
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving || checking || (!appointment && availableSlots.length === 0) || (!appointment && uploadedFiles.length === 0)}
              className="px-6"
              data-testid="modal-save-button"
            >
              {saving ? 'Salvando...' : 'Salvar'}
            </Button>
          </div>
        </form>
      </DialogContent>

      {/* Modal de Seletor de Templates */}
      <TemplateSelector
        isOpen={templateSelectorOpen}
        onClose={() => setTemplateSelectorOpen(false)}
        onSelect={handleTemplateSelect}
      />

      {/* Modal de Salvar como Template */}
      <TemplateFormModal
        isOpen={saveTemplateOpen}
        onClose={() => setSaveTemplateOpen(false)}
        initialData={{
          first_name: formData.first_name,
          last_name: formData.last_name,
          time_slot: formData.time_slot,
          has_chat: formData.has_chat,
          notes: formData.notes,
          day_of_week: formData.date ? new Date(formData.date).getDay() : null
        }}
        onSuccess={() => toast.success('Template salvo!')}
      />
    </Dialog>
  );
};
