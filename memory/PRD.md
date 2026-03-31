# AgendaHub - Product Requirements Document

## Problema Original
Plataforma de agenda operacional para substituir uma planilha do Google Sheets. Usada por uma equipe que realiza atendimentos presenciais e online.

## Fluxo de Trabalho Principal
1. Equipes de 'Televendas' e 'Comercial' criam agendamentos para clientes
2. NÃO atribuem a um agente específico - especificam nome, protocolos e horário
3. Agendamentos entram em fila de "pendentes" com slot bloqueado
4. Supervisor visualiza fila e atribui a um Agente disponível
5. Se não atribuir em 5 minutos, sistema atribui automaticamente (round-robin)
6. Agentes veem seus agendamentos e atualizam status
7. Sistema detecta agentes ausentes e redistribui automaticamente

## Layout da Aplicação (SaaS)

### Sidebar Fixa (Esquerda)
- Logo AgendaHub
- Botão "Novo Agendamento"
- Dashboard
- Agenda Completa
- Meus Agendamentos
- Pendentes (apenas supervisor/admin)
- Usuários (apenas supervisor/admin)
- Painel Supervisor (apenas supervisor/admin)
- Presença de Agentes (apenas supervisor/admin)
- Info do usuário logado

### Permissões por Role (Atualizado 26/02/2026)
| Recurso | Televendas | Comercial | Agente | Supervisor | Admin |
|---------|:----------:|:---------:|:------:|:----------:|:-----:|
| **ACESSO** ||||||
| Dashboard (visualizar) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agenda Completa | ✅ | ✅ | ✅ | ✅ | ✅ |
| Meus Agendamentos | ✅ | ✅ | ✅ | ✅ | ❌ |
| Métricas/Estatísticas | ❌ | ❌ | ❌ | ✅ | ✅ (leitura) |
| Pendentes (fila) | ❌ | ❌ | ❌ | ✅ | ❌ |
| Gerenciar Usuários | ❌ | ❌ | ❌ | ✅ | ✅ (leitura) |
| Painel Supervisor | ❌ | ❌ | ❌ | ✅ | ✅ (leitura) |
| Solicitações (aprovação) | ❌ | ❌ | ❌ | ✅ | ❌ |
| Relatórios | ❌ | ❌ | ❌ | ✅ | ✅ |
| **AGENDAMENTOS** ||||||
| Criar agendamento | ✅ | ✅ | ❌ | ✅ | ❌ |
| Atribuir a agente | ❌ | ❌ | ❌ | ✅ | ❌ |
| Editar agendamento | Solicita | Solicita | ✅* | ✅ | ❌ |
| Cancelar agendamento | Solicita | Solicita | Solicita | ✅ | ❌ |
| Aprovar solicitações | ❌ | ❌ | ❌ | ✅ | ❌ |
| **CONFIGURAÇÕES** ||||||
| Aprovar novos usuários | ❌ | ❌ | ❌ | ✅ | ❌ |
| Alterar cargo/permissões | ❌ | ❌ | ❌ | ✅ | ❌ |
| Gerenciar horários extras | ❌ | ❌ | ❌ | ✅ | ❌ |
| Criar/usar templates | ✅ | ✅ | ❌ | ✅ | ❌ |

**Notas:**
- **Solicita** = Não pode fazer diretamente, mas pode solicitar aprovação do supervisor
- **✅*** = Agente só pode editar seus próprios agendamentos atribuídos
- **Admin** = Perfil de visualização/acompanhamento, sem poder de alteração

## Horários

### Horários Normais (sempre disponíveis)
08:00, 08:20, 08:40, 09:00, 09:20, 09:40,
10:00, 10:20, 10:40, 11:00, 11:20, 11:40,
12:00, 12:20, 13:00, 13:20, 13:40,
14:00, 14:20, 14:40, 15:00, 15:20, 15:40,
16:00, 16:20, 16:40, 17:00, 17:20, 17:40

### Horários Extras (hora extra - gerenciados pelo supervisor)
07:40, 12:40, 18:00, 18:20, 18:40

- Por padrão, NENHUM horário extra está ativo
- Supervisor pode ativar/desativar via Painel Supervisor
- Quando ativados, aparecem na Agenda Completa com indicador "EXTRA"

## Funcionalidades Implementadas

### Sprint 1 - CONCLUÍDO
- [x] Autenticação JWT
- [x] Sistema de aprovação de usuários
- [x] Formulário de agendamento completo
- [x] Upload de múltiplos documentos
- [x] Modal de atribuição para supervisor

### Sprint 2 - CONCLUÍDO
- [x] Atribuição automática após 5 minutos (round-robin)
- [x] Filtros avançados (busca, status, agente, datas)
- [x] Notificações melhoradas

### Sprint 3 - CONCLUÍDO
- [x] Sistema de presença (heartbeat automático)
- [x] Redistribuição automática de agentes ausentes
- [x] Relatório diário e saldo semanal de horas

### Sprint 4 - CONCLUÍDO (Refatoração)
- [x] Layout SaaS com sidebar fixa
- [x] Menu baseado em roles
- [x] Agenda Completa por slots
- [x] Navegação por dia (Anterior/Hoje/Próximo)
- [x] Indicador "AGORA" no slot atual
- [x] Botão "Novo" em slots livres (pré-preenche date/time_slot)
- [x] Gerenciamento de Horários Extras no Painel Supervisor
- [x] Remoção do 12:40 dos horários normais
- [x] Dashboard com cards de métricas
- [x] Televendas pode ver Agenda Completa

### Sprint 5 - CONCLUÍDO (Melhorias Avançadas)
- [x] Drag-and-Drop para reagendamento na Agenda Completa
- [x] Atalhos de teclado para ações rápidas
- [x] Filtros em tempo real em "Meus Agendamentos"
- [x] Filtros em tempo real em "Pendentes"
- [x] Busca em tempo real na página de Gerenciamento de Usuários (25/02/2026)

### Sprint 6 - CONCLUÍDO (Polimento Visual)
- [x] Componentes de skeleton para estados de carregamento (loading-states.jsx)
- [x] Estados vazios com ícones e mensagens amigáveis
- [x] Responsividade mobile completa (sidebar colapsável, botão menu)
- [x] Cards de métricas adaptados para mobile
- [x] Layout responsivo na página de usuários

### Sprint 7 - CONCLUÍDO (Notificações)
- [x] Hook useNotificationSound com Web Audio API
- [x] Som de "ding" para notificações normais
- [x] Som de urgência (3 notas) para novos agendamentos pendentes
- [x] Botão de toggle para ativar/desativar sons
- [x] Persistência da preferência no localStorage
- [x] Detecção automática de novas notificações a cada 15s
- [x] Modal de confirmação para reagendamento via drag-and-drop (evita miss-clicks)
- [x] Browser Notifications (notificações do sistema operacional)
- [x] Hook useBrowserNotifications para gerenciar permissões
- [x] Notificações aparecem mesmo com aba em background

### Lógica de Múltiplos Protocolos (JÁ IMPLEMENTADA)
- [x] Backend: reserva automaticamente 2 slots consecutivos quando 3+ protocolos
- [x] Frontend: alerta visual informando sobre os 2 horários
- [x] Agendamentos linkados via campo `linked_appointment`

### Sprint 8 - CONCLUÍDO (Animações e Refatoração)
- [x] Instalação e configuração do framer-motion
- [x] Animações de transição entre views (Dashboard, Agenda, Meus)
- [x] Animações nos cards de métricas com stagger effect
- [x] Transição animada ao navegar entre dias na Agenda Completa
- [x] AnimatePresence para entrada/saída suave de componentes
- [x] Refatoração inicial do backend:
  - [x] Criada estrutura modular em /app/backend/app/
  - [x] Modelos Pydantic em app/models/
  - [x] Utilitários de auth em app/utils/auth.py
  - [x] Serviço de slots em app/services/slot_service.py
  - [x] Configurações centralizadas em app/config.py
  - [x] Documentação de arquitetura em ARCHITECTURE.md

### Sprint 10 - CONCLUÍDO (Dashboard Integrado)
- [x] Agenda Completa integrada diretamente no Dashboard principal
- [x] Removida a view "Agenda" separada do menu
- [x] Adicionado seletor de data com calendário popup
- [x] Navegação rápida por setas (← →) e botão "Hoje"
- [x] Componente AgendaCompleta com modo "embedded" para integração
- [x] Dark Mode completo com ThemeContext e ThemeToggle
- [x] Variáveis CSS otimizadas para light/dark em index.css
- [x] Persistência de tema no localStorage
- [x] Botão de toggle grande e visível na sidebar (ThemeToggleLarge)
- [x] Cores otimizadas para todos os componentes (AgendaCompleta, Filters, AgentPresence, etc.)
- [x] PWA (Progressive Web App):
  - [x] manifest.json configurado
  - [x] Service Worker com estratégias cache-first e network-first
  - [x] Suporte offline para assets estáticos
  - [x] Meta tags para iOS e Android
- [x] Sistema de Cache no frontend (useCache hook)
- [x] Suporte a dados paginados (usePaginatedData hook)
- [x] Endpoint de paginação no backend (/api/appointments/paginated)

### Sprint 11 - CONCLUÍDO (Análise e Melhorias Completas) - 25/02/2026
#### Correções de Dark Mode (P0)
- [x] UserManagement.js - todas as classes hardcoded (bg-slate-*, text-slate-*) substituídas por variáveis CSS
- [x] AppointmentModal.js - cores corrigidas para suportar modo escuro
- [x] Login.js - labels e textos com variáveis de tema
- [x] ReportsPanel.js - cards e badges com suporte dark mode
- [x] Dashboard.js - cards de atalhos de teclado com tema correto

#### Exportação CSV (P1)
- [x] Endpoint backend GET /api/reports/daily/csv - exporta relatório diário
- [x] Endpoint backend GET /api/reports/weekly-hours/csv - exporta saldo de horas
- [x] Botão de exportação no ReportsPanel com loading state
- [x] Download automático do arquivo CSV

#### Sistema de Histórico de Alterações (P1)
- [x] Modelo AppointmentHistory no backend
- [x] Função log_appointment_history() para registrar todas alterações
- [x] Histórico registrado em: criação, atualização, mudança de status, atribuição, reagendamento
- [x] Endpoint GET /api/appointments/{id}/history
- [x] Componente AppointmentHistory.js - modal com timeline visual
- [x] Botões de histórico nos cards de agendamento (supervisores)

#### Reagendamento Recorrente/Semanal (P1)
- [x] Modelo RecurringAppointmentCreate exigindo NOVO protocolo
- [x] Endpoint POST /api/appointments/recurring
- [x] Componente RecurringAppointmentModal.js
- [x] Sugere automaticamente data +1 semana
- [x] Referência ao agendamento original preservada
- [x] Botões de reagendamento nos cards de agendamento

#### Templates de Agendamento (P1) - NOVO
- [x] Modelo AppointmentTemplate com campos: name, client_first_name, client_last_name, preferred_time_slot, preferred_day_of_week, has_chat, notes, tags, use_count
- [x] CRUD completo: POST/GET/PUT/DELETE /api/templates
- [x] Endpoint POST /api/templates/{id}/use com sugestão inteligente de data
- [x] Lógica de sugestão: última visita +7 dias OU próximo dia preferido OU amanhã
- [x] Componente TemplateSelector.js com busca, tags, edição, exclusão
- [x] Componente TemplateFormModal.js para criar/editar templates
- [x] Integração no AppointmentModal com botão "Usar Template"
- [x] Botão "Salvar como Template" quando nome/sobrenome preenchidos
- [x] Templates ordenados por uso (mais usados primeiro)
- [x] Contador de uso atualizado em tempo real

#### Melhorias de UI/UX (P2)
- [x] Micro-animações CSS (btn-animate, card-lift, pulse-notification, fade-in, slide-up)
- [x] Custom scrollbar para dark mode (scrollbar-custom)
- [x] Classes de status badges (status-badge-*)
- [x] Focus ring aprimorado (focus-ring-primary)
- [x] EmptyState com ilustrações SVG (variants: calendar, users, inbox)
- [x] InlineLoader componente

#### Hooks de Persistência (P2)
- [x] usePersistedFilters - salva filtros no localStorage
- [x] useLocalStorage - hook genérico para persistência
- [x] useDateNavigation - histórico de navegação de datas

### Sprint 12 - CONCLUÍDO (Sistemas Safeweb/Serpro) - 25/02/2026
#### Permissões de Usuário
- [x] Campos `can_safeweb` e `can_serpro` no modelo User
- [x] Endpoint PUT /api/users/{id}/permissions para atualizar permissões
- [x] Endpoint GET /api/users/with-permission/{system} para listar agentes com permissão
- [x] Interface de switches no UserManagement (apenas para agentes)
- [x] Visual: toggle ativo em cyan (Safeweb) e emerald (Serpro)

#### Sistema de Emissão em Agendamentos
- [x] Campo `emission_system` no modelo Appointment (null, 'safeweb', 'serpro')
- [x] Seletor "Sistema de Emissão" no modal de novo agendamento
- [x] 3 opções: Normal (Não se aplica), Safeweb, Serpro
- [x] Texto explicativo: "Qualquer agente pode atender" / "Apenas agentes com permissão SAFEWEB podem atender"

#### Lógica Inteligente de Slots
- [x] GET /api/appointments/available-slots aceita parâmetro `emission_system`
- [x] Retorna apenas horários com agentes que tenham permissão quando especificado
- [x] Calcula possibilidade de redistribuição (status: 'redistribution_needed')
- [x] Endpoint POST /api/appointments/redistribute para mover agendamentos comuns
- [x] Endpoint GET /api/appointments/check-redistribution/{id} para verificar possibilidade

#### Validação de Atribuição
- [x] PUT /api/appointments/{id}/assign valida permissão do agente
- [x] Erro claro: "Este agente não tem permissão para atendimentos SAFEWEB"
- [x] Notificações especiais para agendamentos Safeweb/Serpro: "[SAFEWEB] Novo agendamento..."

#### Visualização
- [x] Badge SAFEWEB (cyan) e SERPRO (emerald) nos cards de agendamento
- [x] Badge com borda e fundo semi-transparente para dark mode

#### Correção da Sidebar
- [x] Removido ThemeToggleLarge duplicado
- [x] Mantido apenas ícone sol/lua no header
- [x] Corrigidas cores hardcoded (slate -> variáveis CSS)
- [x] Corrigido bug do mini-calendário na sidebar (25/02/2026)
  - Substituído componente `<Calendar />` do Shadcn UI por `<CalendarIcon />` do Lucide no logo
  - O componente Calendar estava renderizando um calendário completo onde deveria ser apenas um ícone

#### Plataforma de Chat (Blip/ChatPro) - 25/02/2026
- [x] Campo `chat_platform` adicionado nos modelos de Appointment e Template
- [x] Validação no backend: obrigatório selecionar plataforma quando `has_chat=true`
- [x] UI com cards visuais para seleção de Blip ou ChatPro
- [x] Mensagem de erro quando plataforma não selecionada
- [x] Badge de plataforma exibido nos cards de agendamento (BLIP em azul, CHATPRO em verde)

#### Redesign Visual da Agenda do Dia - 25/02/2026
- [x] **Timeline Visual**: Linha vertical conectando horários com pontos indicadores
- [x] **Indicador "Agora"**: Badge com animação pulse para slot atual
- [x] **Cards de Agendamento Modernos**:
  - Avatar circular com iniciais do agente
  - Gradientes sutis nos backgrounds
  - Indicador de status (bolinha colorida)
  - Badges modernos para Safeweb/Serpro/Chat
  - Animações de hover com elevação
- [x] **Slots Redesenhados**:
  - Header com badge de disponibilidade (verde/amarelo/vermelho)
  - Contador de vagas com ícones
  - Botão "Agendar" estilizado
- [x] **Header Elegante**:
  - Data formatada com linha decorativa
  - Contador de agentes/horários
  - Badge "Arraste para remarcar" com ícone
  - Filtro por agente melhorado

#### Correções Dark Mode e UX - 26/02/2026
- [x] **Botão de Logout**: Adicionado ícone de logout ao lado do perfil do usuário na sidebar
- [x] **SupervisorDashboard**: Corrigidas todas as cores hardcoded (slate-*) para variáveis CSS (foreground, muted-foreground, etc.)
- [x] **NotificationsPanel**: Corrigido fundo branco para usar bg-card e border-border, cores dos badges atualizadas
- [x] **PendingAssignments**: Corrigidas cores de fundo (bg-muted), textos (text-foreground), e badges para dark mode
- [x] **Timeline da Agenda**: Removida a linha vertical bugada, substituída por design simplificado com pontos indicadores inline

#### Aba "Meus Agendamentos" - 26/02/2026
- [x] **Backend - Endpoints**:
  - `GET /api/my-appointments`: Lista agendamentos por role (criados por televendas, atribuídos a agentes, ambos para supervisor)
  - `GET /api/my-appointments/stats`: Estatísticas dos agendamentos do usuário
  - `POST /api/change-requests`: Criar solicitação de edição/cancelamento
  - `GET /api/change-requests`: Listar solicitações
  - `PUT /api/change-requests/{id}/review`: Aprovar/rejeitar solicitação (supervisor)
- [x] **Frontend - Componente MyAppointments**:
  - Cards de estatísticas (Total, Hoje, Pendentes, Emitidos)
  - Navegação por data (setas e botão "Hoje")
  - Filtros (busca por nome/protocolo, dropdown de status)
  - Cards de agendamentos com badges coloridos
  - Botões de Editar/Cancelar em cada card
  - Modal de edição completo com todos os campos:
    - Nome e Sobrenome
    - Protocolo Principal
    - Protocolos Adicionais (com opção de adicionar/remover)
    - Nova Data e Novo Horário
    - Observações
    - Motivo da alteração
  - Agendamentos "emitido" ou "cancelado" não podem ser alterados
- [x] **Acesso por Role**:
  - Televendas: Vê agendamentos que criou
  - Agente: Vê agendamentos atribuídos a ele
  - Supervisor: Vê agendamentos criados OU atribuídos (ambos)
- [x] **Regras de Negócio**:
  - Supervisor: altera diretamente sem aprovação
  - Outros roles: solicitação enviada para aprovação
  - Auto-aprovação quando < 30 minutos do horário
  - Notificações para supervisores e solicitantes
- [x] **Dark Mode Completo**: Todas as cores usando variáveis CSS

#### Tela de Aprovação de Solicitações (Supervisor) - 26/02/2026 ✅ TESTADO
- [x] **Backend - Endpoint de Revisão**:
  - `PUT /api/change-requests/{id}/review?approved=bool&review_notes=str`
  - Valida permissão (apenas supervisor)
  - Aplica alterações no agendamento quando aprovado
  - Cancela agendamento quando solicitação de cancelamento é aprovada
  - Registra histórico de alterações
  - Notifica solicitante sobre resultado
- [x] **Frontend - ChangeRequestsPanel**:
  - Cards com informações da solicitação (solicitante, data, tipo)
  - Indicador visual de status (Pendente em amarelo)
  - Link para expandir/ver mudanças propostas
  - Botões "Aprovar" e "Rejeitar" em cada card
  - Modal de confirmação com campo de observações opcional
  - Toast de sucesso após ação
  - Lista atualiza automaticamente
- [x] **Menu "Solicitações"**:
  - Visível apenas para supervisores
  - Ícone CheckSquare
  - Acesso via menu lateral
- [x] **Filtros**:
  - Dropdown para filtrar por status: Pendentes, Aprovadas, Rejeitadas, Todas
  - Contador de pendentes no filtro
- [x] **Testes Realizados**:
  - ✅ Backend: Aprovação de edição (nome atualizado)
  - ✅ Backend: Rejeição de cancelamento
  - ✅ Frontend: Visualização de solicitações pendentes
  - ✅ Frontend: Expansão de mudanças propostas
  - ✅ Frontend: Modal de confirmação de aprovação
  - ✅ Frontend: Fluxo completo de aprovação pela UI
  - ✅ Toast de sucesso "Solicitação aprovada!"
  - ✅ Lista atualiza para "Pendentes (0)"

#### Refatoração Técnica - 26/02/2026
- [x] **Zustand Store (Estado Global)**:
  - Criado `/app/frontend/src/stores/useAppStore.js`
  - `useAppointmentsStore`: Gerencia agendamentos com paginação
  - `useUsersStore`: Gerencia usuários e presença de agentes
  - `useNotificationsStore`: Gerencia notificações
  - `useDashboardStore`: Gerencia estatísticas
  - `useUIStore`: Estado da UI persistido (tema, sidebar, preferências)
  - Guia de migração em `/app/frontend/src/stores/MIGRATION_GUIDE.js`
- [x] **Rotas Modulares do Backend**:
  - Criado `/app/backend/app/routes/` com estrutura modular
  - `auth.py`: Registro, login, autenticação
  - `users.py`: CRUD de usuários, permissões, estatísticas
  - `notifications.py`: Notificações do usuário
  - `presence.py`: Sistema de presença (heartbeat)
  - `reports.py`: Relatórios diários/semanais com exportação CSV
  - Utilitários atualizados: `database.py`, `auth.py`
- [x] **Componente PaginatedList**:
  - Criado `/app/frontend/src/components/PaginatedList.js`
  - Suporte a infinite scroll e botão "carregar mais"
  - Hook `usePagination` para gerenciar estado
  - Configurável: gridCols, emptyState, variant

## Backlog - Tarefas Futuras

### P1 - Alta Prioridade
- [ ] Finalizar integração Zustand nos componentes existentes
- [ ] Tour de onboarding para novos usuários

### P2 - Média Prioridade
- [ ] Mover rotas restantes do server.py para estrutura modular (appointments, templates, etc.)
- [ ] Implementar WebSockets para atualizações em tempo real (substituir polling)

### P3 - Baixa Prioridade
- [ ] Integração com Google Calendar
- [ ] Exportação de relatórios em PDF
- [ ] Dashboard de analytics avançado
- [ ] Suporte a múltiplos idiomas (i18n)
- [ ] Rate limiting nas rotas públicas
- [ ] Testes automatizados (pytest/jest)

## Stack Técnico
- **Backend**: FastAPI, Motor, MongoDB
- **Frontend**: React.js, TailwindCSS, Shadcn/UI
- **Auth**: JWT (7 dias)
- **Background Tasks**: asyncio (auto-assign, presence check)

## Credenciais de Teste
- Televendas: tele1@agenda.com / password123
- Supervisor: supervisor2@agenda.com / password123

## Endpoints Principais

### Slots
- GET /api/slots/all?date= - Todos os slots do dia com status
- GET /api/extra-hours?date= - Horários extras configurados
- PUT /api/extra-hours?date=&slots= - Ativar/desativar horários extras
