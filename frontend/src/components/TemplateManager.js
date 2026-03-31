import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Switch } from './ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Card, CardContent } from './ui/card';
import { templatesAPI } from '../utils/api';
import { toast } from 'sonner';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { 
  BookmarkPlus, 
  Bookmark, 
  Search, 
  Trash2, 
  Edit2, 
  Clock, 
  Calendar,
  User,
  Tag,
  Loader2,
  X,
  ChevronRight,
  Star
} from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from './ui/alert-dialog';

const dayOfWeekLabels = {
  0: 'Segunda-feira',
  1: 'Terça-feira',
  2: 'Quarta-feira',
  3: 'Quinta-feira',
  4: 'Sexta-feira',
  5: 'Sábado',
  6: 'Domingo'
};

// Modal para criar/editar template
export const TemplateFormModal = ({ 
  isOpen, 
  onClose, 
  template = null, // Se passado, é edição
  onSuccess,
  initialData = null // Dados pré-preenchidos (ex: de um agendamento)
}) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    client_first_name: '',
    client_last_name: '',
    preferred_time_slot: '',
    preferred_day_of_week: null,
    has_chat: false,
    notes: '',
    tags: []
  });
  const [tagInput, setTagInput] = useState('');

  useEffect(() => {
    if (isOpen) {
      if (template) {
        setFormData({
          name: template.name || '',
          client_first_name: template.client_first_name || '',
          client_last_name: template.client_last_name || '',
          preferred_time_slot: template.preferred_time_slot || '',
          preferred_day_of_week: template.preferred_day_of_week,
          has_chat: template.has_chat || false,
          notes: template.notes || '',
          tags: template.tags || []
        });
      } else if (initialData) {
        setFormData({
          name: `${initialData.first_name} ${initialData.last_name}`,
          client_first_name: initialData.first_name || '',
          client_last_name: initialData.last_name || '',
          preferred_time_slot: initialData.time_slot || '',
          preferred_day_of_week: initialData.day_of_week ?? null,
          has_chat: initialData.has_chat || false,
          notes: initialData.notes || '',
          tags: []
        });
      } else {
        setFormData({
          name: '',
          client_first_name: '',
          client_last_name: '',
          preferred_time_slot: '',
          preferred_day_of_week: null,
          has_chat: false,
          notes: '',
          tags: []
        });
      }
    }
  }, [isOpen, template, initialData]);

  const handleAddTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData({ ...formData, tags: [...formData.tags, tagInput.trim()] });
      setTagInput('');
    }
  };

  const handleRemoveTag = (idx) => {
    setFormData({ 
      ...formData, 
      tags: formData.tags.filter((_, i) => i !== idx) 
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.client_first_name || !formData.client_last_name) {
      toast.error('Preencha os campos obrigatórios');
      return;
    }
    
    setLoading(true);
    try {
      const payload = {
        ...formData,
        preferred_day_of_week: formData.preferred_day_of_week === '' ? null : formData.preferred_day_of_week
      };
      
      if (template) {
        await templatesAPI.update(template.id, payload);
        toast.success('Template atualizado!');
      } else {
        await templatesAPI.create(payload);
        toast.success('Template criado!');
      }
      onSuccess?.();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao salvar template');
    } finally {
      setLoading(false);
    }
  };

  const timeSlots = [
    '08:00', '08:20', '08:40', '09:00', '09:20', '09:40',
    '10:00', '10:20', '10:40', '11:00', '11:20', '11:40',
    '12:00', '12:20', '13:00', '13:20', '13:40',
    '14:00', '14:20', '14:40', '15:00', '15:20', '15:40',
    '16:00', '16:20', '16:40', '17:00', '17:20', '17:40'
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="template-form-modal">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold tracking-tight flex items-center gap-2 text-foreground">
            <BookmarkPlus className="w-5 h-5" />
            {template ? 'Editar Template' : 'Novo Template'}
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Salve um cliente frequente para agendar rapidamente
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5 mt-4">
          {/* Nome do Template */}
          <div className="space-y-2">
            <Label htmlFor="name" className="text-sm font-medium text-foreground">
              Nome do Template *
            </Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ex: João Silva - Semanal"
              required
              data-testid="template-name-input"
              className="h-11"
            />
          </div>

          {/* Nome do Cliente */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="client_first_name" className="text-sm font-medium text-foreground">
                Nome do Cliente *
              </Label>
              <Input
                id="client_first_name"
                value={formData.client_first_name}
                onChange={(e) => setFormData({ ...formData, client_first_name: e.target.value })}
                placeholder="João"
                required
                className="h-11"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="client_last_name" className="text-sm font-medium text-foreground">
                Sobrenome *
              </Label>
              <Input
                id="client_last_name"
                value={formData.client_last_name}
                onChange={(e) => setFormData({ ...formData, client_last_name: e.target.value })}
                placeholder="Silva"
                required
                className="h-11"
              />
            </div>
          </div>

          {/* Preferências de Horário */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                <Clock className="w-4 h-4 inline mr-1" />
                Horário Preferido
              </Label>
              <Select
                value={formData.preferred_time_slot || 'none'}
                onValueChange={(value) => setFormData({ 
                  ...formData, 
                  preferred_time_slot: value === 'none' ? '' : value 
                })}
              >
                <SelectTrigger className="h-11">
                  <SelectValue placeholder="Qualquer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Qualquer horário</SelectItem>
                  {timeSlots.map((slot) => (
                    <SelectItem key={slot} value={slot}>{slot}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                <Calendar className="w-4 h-4 inline mr-1" />
                Dia Preferido
              </Label>
              <Select
                value={formData.preferred_day_of_week?.toString() || 'none'}
                onValueChange={(value) => setFormData({ 
                  ...formData, 
                  preferred_day_of_week: value === 'none' ? null : parseInt(value) 
                })}
              >
                <SelectTrigger className="h-11">
                  <SelectValue placeholder="Qualquer" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Qualquer dia</SelectItem>
                  {Object.entries(dayOfWeekLabels).map(([value, label]) => (
                    <SelectItem key={value} value={value}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Chat */}
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
            <div>
              <Label htmlFor="has_chat" className="text-sm font-medium text-foreground cursor-pointer">
                Cliente geralmente tem chat
              </Label>
              <p className="text-xs text-muted-foreground mt-1">Será pré-selecionado ao usar o template</p>
            </div>
            <Switch
              id="has_chat"
              checked={formData.has_chat}
              onCheckedChange={(checked) => setFormData({ ...formData, has_chat: checked })}
            />
          </div>

          {/* Tags */}
          <div className="space-y-3">
            <Label className="text-sm font-medium text-foreground">
              <Tag className="w-4 h-4 inline mr-1" />
              Tags
            </Label>
            <div className="flex gap-2">
              <Input
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="Ex: VIP, Urgente"
                className="h-10"
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
              />
              <Button type="button" variant="outline" onClick={handleAddTag} className="px-4">
                +
              </Button>
            </div>
            
            {formData.tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {formData.tags.map((tag, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm">
                    <span>{tag}</span>
                    <button type="button" onClick={() => handleRemoveTag(idx)} className="hover:text-primary/80">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Observações */}
          <div className="space-y-2">
            <Label htmlFor="notes" className="text-sm font-medium text-foreground">Observações</Label>
            <Input
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Observações que serão copiadas para o agendamento..."
              className="h-11"
            />
          </div>

          {/* Botões */}
          <div className="flex justify-end gap-3 pt-4 border-t border-border">
            <Button type="button" variant="outline" onClick={onClose} className="px-6">
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={loading}
              className="px-6"
              data-testid="template-save-btn"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Salvando...
                </>
              ) : (
                <>
                  <BookmarkPlus className="w-4 h-4 mr-2" />
                  {template ? 'Salvar Alterações' : 'Criar Template'}
                </>
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

// Seletor de Template para usar ao criar agendamento
export const TemplateSelector = ({ 
  isOpen, 
  onClose, 
  onSelect // Callback com os dados do template para preencher o form
}) => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [editTemplate, setEditTemplate] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadTemplates();
    }
  }, [isOpen, search]);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const response = await templatesAPI.getAll({ search: search || undefined });
      setTemplates(response.data);
    } catch (error) {
      toast.error('Erro ao carregar templates');
    } finally {
      setLoading(false);
    }
  };

  const handleUseTemplate = async (template) => {
    try {
      const response = await templatesAPI.use(template.id);
      const suggestion = response.data.suggestion;
      
      onSelect({
        first_name: suggestion.first_name,
        last_name: suggestion.last_name,
        has_chat: suggestion.has_chat,
        notes: suggestion.notes,
        suggested_date: suggestion.suggested_date,
        suggested_time_slot: suggestion.suggested_time_slot,
        template_id: template.id
      });
      
      toast.success(`Template "${template.name}" aplicado!`);
      onClose();
    } catch (error) {
      toast.error('Erro ao usar template');
    }
  };

  const handleDelete = async (id) => {
    try {
      await templatesAPI.delete(id);
      toast.success('Template excluído');
      setDeleteConfirm(null);
      loadTemplates();
    } catch (error) {
      toast.error('Erro ao excluir template');
    }
  };

  return (
    <>
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto" data-testid="template-selector">
          <DialogHeader>
            <DialogTitle className="text-xl font-semibold tracking-tight flex items-center gap-2 text-foreground">
              <Bookmark className="w-5 h-5" />
              Templates de Agendamento
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              Selecione um cliente frequente para preencher automaticamente
            </DialogDescription>
          </DialogHeader>

          {/* Busca */}
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar por nome do cliente..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
              data-testid="template-search-input"
            />
          </div>

          {/* Lista de Templates */}
          <div className="mt-4 space-y-3 max-h-[400px] overflow-y-auto scrollbar-custom">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : templates.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Bookmark className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="font-medium">Nenhum template encontrado</p>
                <p className="text-sm mt-1">Crie templates para clientes frequentes</p>
              </div>
            ) : (
              templates.map((template) => (
                <Card 
                  key={template.id} 
                  className="hover:border-primary/50 transition-colors cursor-pointer"
                  data-testid={`template-card-${template.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div 
                        className="flex-1 min-w-0"
                        onClick={() => handleUseTemplate(template)}
                      >
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-foreground truncate">
                            {template.name}
                          </h3>
                          {template.use_count > 5 && (
                            <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          <User className="w-3 h-3 inline mr-1" />
                          {template.client_first_name} {template.client_last_name}
                        </p>
                        <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                          {template.preferred_time_slot && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {template.preferred_time_slot}
                            </span>
                          )}
                          {template.preferred_day_of_week !== null && (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {dayOfWeekLabels[template.preferred_day_of_week]}
                            </span>
                          )}
                          <span>Usado {template.use_count}x</span>
                        </div>
                        {template.tags?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {template.tags.map((tag, idx) => (
                              <span 
                                key={idx} 
                                className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditTemplate(template);
                          }}
                          className="h-8 w-8"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteConfirm(template.id);
                          }}
                          className="h-8 w-8 text-destructive hover:text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleUseTemplate(template)}
                          className="h-8 w-8 text-primary"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>

          <div className="flex justify-end pt-4 border-t border-border mt-4">
            <Button variant="outline" onClick={onClose}>
              Fechar
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Modal de Edição */}
      <TemplateFormModal
        isOpen={!!editTemplate}
        onClose={() => setEditTemplate(null)}
        template={editTemplate}
        onSuccess={loadTemplates}
      />

      {/* Confirmação de Exclusão */}
      <AlertDialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir Template</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este template? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction 
              onClick={() => handleDelete(deleteConfirm)}
              className="bg-destructive hover:bg-destructive/90"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default TemplateSelector;
