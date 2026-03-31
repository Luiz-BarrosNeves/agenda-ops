# AgendaHub Backend - Arquitetura

## Estrutura de Diretórios

```
backend/
├── server.py              # Arquivo principal (monolito atual)
├── requirements.txt       # Dependências Python
├── uploads/              # Diretório de uploads de documentos
├── .env                  # Variáveis de ambiente
└── app/                  # Módulos refatorados
    ├── __init__.py
    ├── config.py         # Configurações centralizadas
    ├── models/
    │   └── __init__.py   # Modelos Pydantic
    ├── routes/           # Rotas organizadas por domínio
    │   └── __init__.py
    ├── services/         # Lógica de negócio
    │   ├── __init__.py
    │   └── slot_service.py
    └── utils/
        ├── __init__.py
        ├── auth.py       # Utilitários de autenticação
        └── database.py   # Conexão com MongoDB
```

## Módulos Disponíveis

### config.py
- `DEFAULT_TIME_SLOTS`: Lista de horários padrão de atendimento
- `EXTRA_TIME_SLOTS`: Horários extras (07:40, 18:00)
- `UserRole`: Enum com roles de usuário e métodos de verificação de permissão

### models/
Contém todos os modelos Pydantic:
- `User`, `UserCreate`, `UserLogin`, `UserApprove`, `UserUpdateRole`
- `Appointment`, `AppointmentCreate`, `AppointmentUpdate`, `AppointmentAssign`
- `SlotAvailability`, `ExtraHoursUpdate`
- `Notification`
- `AppointmentFilters`

### utils/auth.py
- `create_token()`: Cria token JWT
- `verify_token()`: Verifica token JWT
- `hash_password()`: Hash de senha com bcrypt
- `verify_password()`: Verifica senha
- `require_roles()`: Decorator para verificação de permissões

### utils/database.py
- `get_database()`: Retorna instância do MongoDB
- `get_collection()`: Retorna coleção específica

### services/slot_service.py
- `SlotService.get_default_slots()`: Retorna slots padrão
- `SlotService.is_slot_current()`: Verifica se slot é atual
- `SlotService.calculate_slot_availability()`: Calcula disponibilidade

## Plano de Migração

A refatoração está sendo feita de forma incremental para não quebrar funcionalidades:

1. ✅ **Fase 1**: Criar estrutura de módulos e mover modelos
2. 🔄 **Fase 2**: Extrair lógica de autenticação
3. ⏳ **Fase 3**: Criar services para lógica de negócio
4. ⏳ **Fase 4**: Migrar rotas para módulos separados
5. ⏳ **Fase 5**: Refatorar server.py para importar dos módulos

## API Endpoints

### Autenticação
- `POST /api/auth/register` - Registro de usuário
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Dados do usuário atual

### Usuários
- `GET /api/users` - Lista usuários
- `PUT /api/users/{id}/approve` - Aprovar usuário
- `PUT /api/users/{id}/role` - Alterar cargo
- `DELETE /api/users/{id}` - Excluir usuário
- `GET /api/users/attendants` - Lista agentes
- `GET /api/users/stats/team` - Estatísticas da equipe

### Agendamentos
- `POST /api/appointments` - Criar agendamento
- `GET /api/appointments` - Listar agendamentos
- `GET /api/appointments/pending` - Agendamentos pendentes
- `GET /api/appointments/filtered` - Busca com filtros
- `PUT /api/appointments/{id}` - Atualizar
- `PUT /api/appointments/{id}/assign` - Atribuir a agente
- `DELETE /api/appointments/{id}` - Excluir
- `POST /api/appointments/{id}/upload` - Upload de documento
- `GET /api/appointments/{id}/download/{filename}` - Download de documento

### Slots e Disponibilidade
- `GET /api/appointments/availability` - Disponibilidade por slot
- `GET /api/appointments/available-slots` - Slots disponíveis
- `GET /api/slots/all` - Todos os slots com agendamentos

### Horários Extras
- `GET /api/extra-hours` - Obter horários extras ativos
- `PUT /api/extra-hours` - Atualizar horários extras

### Presença
- `POST /api/presence/heartbeat` - Heartbeat do agente
- `POST /api/presence/offline` - Marcar offline
- `GET /api/presence/agents` - Status de presença

### Notificações
- `GET /api/notifications` - Listar notificações
- `PUT /api/notifications/{id}/read` - Marcar como lida
- `PUT /api/notifications/read-all` - Marcar todas como lidas
- `DELETE /api/notifications/{id}` - Excluir notificação

### Relatórios
- `GET /api/reports/daily` - Relatório diário
- `GET /api/reports/weekly-hours` - Saldo de horas semanal
- `GET /api/stats/dashboard` - Estatísticas do dashboard
