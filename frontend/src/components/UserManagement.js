import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { usersAPI } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Switch } from './ui/switch';
import { ArrowLeft, CheckCircle, XCircle, Trash2, UserCog, Search, Users, Loader2, Shield, ShieldCheck, Eye, KeyRound } from 'lucide-react';
import { ResetPasswordModal } from './ResetPasswordModal';
import { toast } from 'sonner';
import { UserListSkeleton } from './ui/loading-states';
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

const UserManagement = () => {
  const [resetUserId, setResetUserId] = useState(null);
  const { user: currentUser } = useAuth();
  const isReadOnly = currentUser?.role === 'admin'; // Admin apenas visualiza
  
  const [users, setUsers] = useState([]);
  const [pendingUsers, setPendingUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [updatingPermission, setUpdatingPermission] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const [allUsers, pending] = await Promise.all([
        usersAPI.getAll({}),
        usersAPI.getAll({ pending_approval: true })
      ]);
      setUsers(allUsers.data.filter(u => u.approved));
      setPendingUsers(pending.data);
    } catch (error) {
      toast.error('Erro ao carregar usuários');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = useMemo(() => {
    if (!searchTerm) return users;
    const search = searchTerm.toLowerCase();
    return users.filter(u => 
      u.name?.toLowerCase().includes(search) ||
      u.email?.toLowerCase().includes(search) ||
      u.role?.toLowerCase().includes(search)
    );
  }, [users, searchTerm]);

  const filteredPending = useMemo(() => {
    if (!searchTerm) return pendingUsers;
    const search = searchTerm.toLowerCase();
    return pendingUsers.filter(u => 
      u.name?.toLowerCase().includes(search) ||
      u.email?.toLowerCase().includes(search)
    );
  }, [pendingUsers, searchTerm]);

  const handleApprove = async (userId) => {
    try {
      await usersAPI.approve(userId);
      toast.success('Usuário aprovado com sucesso!');
      await loadUsers();
    } catch (error) {
      toast.error('Erro ao aprovar usuário');
    }
  };

  const handleRoleChange = async (userId, newRole) => {
    try {
      await usersAPI.updateRole(userId, newRole);
      toast.success('Cargo atualizado com sucesso!');
      await loadUsers();
    } catch (error) {
      toast.error('Erro ao atualizar cargo');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    
    try {
      await usersAPI.delete(deleteConfirm);
      toast.success('Usuário removido com sucesso!');
      setDeleteConfirm(null);
      await loadUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao remover usuário');
    }
  };

  const handlePermissionChange = async (userId, permission, value) => {
    setUpdatingPermission(`${userId}-${permission}`);
    try {
      await usersAPI.updatePermissions(userId, { [permission]: value });
      toast.success('Permissão atualizada!');
      await loadUsers();
    } catch (error) {
      toast.error('Erro ao atualizar permissão');
    } finally {
      setUpdatingPermission(null);
    }
  };

  const roleLabels = {
    admin: 'Administrador',
    supervisor: 'Supervisor',
    agente: 'Agente',
    televendas: 'Televendas',
    comercial: 'Comercial'
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <div className="mb-6">
            <Button
              variant="ghost"
              onClick={() => navigate('/dashboard')}
              className="mb-4"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Voltar
            </Button>
            <h1 className="text-2xl lg:text-3xl font-semibold tracking-tight text-foreground">
              Gerenciamento de Usuários
            </h1>
          </div>
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Carregando usuários...</CardTitle>
            </CardHeader>
            <CardContent>
              <UserListSkeleton count={4} />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background" data-testid="user-management">
      <div className="max-w-7xl mx-auto p-4 lg:p-6">
        <div className="mb-6">
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="mb-4"
            data-testid="back-button"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <h1 className="text-2xl lg:text-3xl font-semibold tracking-tight text-foreground">
            Gerenciamento de Usuários
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {isReadOnly ? 'Modo visualização - Você pode acompanhar os usuários mas não fazer alterações' : 'Gerencie permissões e aprove novos usuários'}
          </p>
          {isReadOnly && (
            <div className="mt-2 flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
              <Eye className="w-4 h-4" />
              <span>Acesso somente leitura</span>
            </div>
          )}
        </div>

        {/* Campo de Busca */}
        <div className="mb-6">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Buscar por nome, email ou cargo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
              data-testid="search-users-input"
            />
          </div>
          {searchTerm && (
            <p className="text-sm text-muted-foreground mt-2">
              Mostrando {filteredUsers.length + filteredPending.length} resultado(s) para "{searchTerm}"
            </p>
          )}
        </div>

        {filteredPending.length > 0 && (
          <Card className="mb-6 border-orange-300 dark:border-orange-700">
            <CardHeader>
              <CardTitle className="text-xl text-orange-600 dark:text-orange-400">
                Aguardando Aprovação ({filteredPending.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {filteredPending.map(user => (
                  <div
                    key={user.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-700 rounded-lg"
                    data-testid={`pending-user-${user.id}`}
                  >
                    <div>
                      <p className="font-semibold text-foreground">{user.name}</p>
                      <p className="text-sm text-muted-foreground">{user.email}</p>
                      <p className="text-xs text-muted-foreground mt-1">Cargo solicitado: {roleLabels[user.role]}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleApprove(user.id)}
                        className="bg-green-600 hover:bg-green-700"
                        data-testid={`approve-${user.id}`}
                        disabled={isReadOnly}
                        title={isReadOnly ? 'Modo visualização' : ''}
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Aprovar
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => setDeleteConfirm(user.id)}
                        data-testid={`reject-${user.id}`}
                        disabled={isReadOnly}
                        title={isReadOnly ? 'Modo visualização' : ''}
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Rejeitar
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle className="text-xl flex items-center gap-2">
              <Users className="w-5 h-5" />
              Usuários Ativos ({filteredUsers.length}{searchTerm ? ` de ${users.length}` : ''})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {filteredUsers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>{searchTerm ? `Nenhum usuário encontrado para "${searchTerm}"` : 'Nenhum usuário ativo'}</p>
              </div>
            ) : (
            <div className="space-y-3">
              {filteredUsers.map(user => (
                <div
                  key={user.id}
                  className="p-4 bg-card border border-border rounded-lg hover:border-primary/30 transition-colors"
                  data-testid={`user-${user.id}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-primary/20 flex items-center justify-center text-primary font-medium text-base sm:text-lg flex-shrink-0">
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-foreground truncate">{user.name}</p>
                        <p className="text-sm text-muted-foreground truncate">{user.email}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 sm:gap-3 ml-auto sm:ml-0">
                      <div className="w-36 sm:w-48">
                        <Select
                          value={user.role}
                          onValueChange={(value) => handleRoleChange(user.id, value)}
                          disabled={isReadOnly}
                        >
                          <SelectTrigger data-testid={`role-select-${user.id}`} className="h-9" disabled={isReadOnly}>
                            <div className="flex items-center gap-2">
                              <UserCog className="w-4 h-4 hidden sm:block" />
                              <SelectValue />
                            </div>
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="agente">Agente</SelectItem>
                            <SelectItem value="televendas">Televendas</SelectItem>
                            <SelectItem value="comercial">Comercial</SelectItem>
                            <SelectItem value="supervisor">Supervisor</SelectItem>
                            <SelectItem value="admin">Administrador</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      {!isReadOnly && (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setResetUserId(user.id)}
                            className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                            data-testid={`reset-password-${user.id}`}
                            title="Resetar senha"
                          >
                            <KeyRound className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setDeleteConfirm(user.id)}
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            data-testid={`delete-${user.id}`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </>
                      )}
                      <ResetPasswordModal open={!!resetUserId} onOpenChange={() => setResetUserId(null)} userId={resetUserId} />
                    </div>
                  </div>

                  {/* Permissões Safeweb/Serpro - apenas para Agentes */}
                  {user.role === 'agente' && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <p className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-1">
                        <Shield className="w-3 h-3" />
                        Permissões de Emissão
                      </p>
                      <div className="flex flex-wrap gap-4">
                        <div className="flex items-center gap-2">
                          <Switch
                            id={`safeweb-${user.id}`}
                            checked={user.can_safeweb || false}
                            disabled={isReadOnly || updatingPermission === `${user.id}-can_safeweb`}
                            onCheckedChange={(checked) => handlePermissionChange(user.id, 'can_safeweb', checked)}
                            data-testid={`safeweb-switch-${user.id}`}
                          />
                          <label 
                            htmlFor={`safeweb-${user.id}`}
                            className={`text-sm cursor-pointer flex items-center gap-1 ${user.can_safeweb ? 'text-cyan-600 dark:text-cyan-400 font-medium' : 'text-muted-foreground'}`}
                          >
                            {user.can_safeweb && <ShieldCheck className="w-3.5 h-3.5" />}
                            Safeweb
                          </label>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            id={`serpro-${user.id}`}
                            checked={user.can_serpro || false}
                            disabled={isReadOnly || updatingPermission === `${user.id}-can_serpro`}
                            onCheckedChange={(checked) => handlePermissionChange(user.id, 'can_serpro', checked)}
                            data-testid={`serpro-switch-${user.id}`}
                          />
                          <label 
                            htmlFor={`serpro-${user.id}`}
                            className={`text-sm cursor-pointer flex items-center gap-1 ${user.can_serpro ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-muted-foreground'}`}
                          >
                            {user.can_serpro && <ShieldCheck className="w-3.5 h-3.5" />}
                            Serpro
                          </label>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            )}
          </CardContent>
        </Card>
      </div>

      <AlertDialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Tem certeza?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação não pode ser desfeita. O usuário será permanentemente removido do sistema.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default UserManagement;
