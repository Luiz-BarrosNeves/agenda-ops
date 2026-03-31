import React from 'react';
import { format, startOfWeek, addDays, parseISO, isSameDay } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { AppointmentCard } from './AppointmentCard';

export const WeeklyView = ({ users, appointments, currentWeek, onEditAppointment, onDeleteAppointment }) => {
  const weekStart = startOfWeek(currentWeek, { locale: ptBR });
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const getAppointmentsForUserAndDay = (userId, day) => {
    return appointments.filter(apt => {
      const aptDate = parseISO(apt.start_time);
      return apt.user_id === userId && isSameDay(aptDate, day);
    }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  };

  return (
    <div className="bg-card rounded-lg border border-border shadow-sm overflow-hidden" data-testid="weekly-view">
      <div className="grid" style={{ gridTemplateColumns: `200px repeat(${weekDays.length}, 1fr)` }}>
        <div className="bg-slate-50 border-b border-r border-slate-200 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Profissional</p>
        </div>
        {weekDays.map(day => (
          <div key={day.toISOString()} className="bg-slate-50 border-b border-slate-200 p-4 text-center">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              {format(day, 'EEE', { locale: ptBR })}
            </p>
            <p className="text-lg font-semibold text-slate-900 mt-1">
              {format(day, 'dd', { locale: ptBR })}
            </p>
          </div>
        ))}

        {users.map(user => (
          <React.Fragment key={user.id}>
            <div className="border-b border-r border-slate-200 p-4 bg-white" data-testid={`user-column-${user.id}`}>
              <div className="flex items-center gap-3">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.name} className="w-10 h-10 rounded-full object-cover" />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-slate-300 flex items-center justify-center text-white font-medium">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{user.name}</p>
                  <p className="text-xs text-slate-500 capitalize">{user.role}</p>
                </div>
              </div>
            </div>

            {weekDays.map(day => {
              const dayAppointments = getAppointmentsForUserAndDay(user.id, day);
              return (
                <div
                  key={`${user.id}-${day.toISOString()}`}
                  className="border-b border-slate-200 p-2 min-h-[120px] bg-white hover:bg-slate-50 transition-colors"
                  data-testid={`cell-${user.id}-${format(day, 'yyyy-MM-dd')}`}
                >
                  <div className="space-y-2">
                    {dayAppointments.map(apt => (
                      <AppointmentCard
                        key={apt.id}
                        appointment={apt}
                        onEdit={() => onEditAppointment(apt)}
                        onDelete={() => onDeleteAppointment(apt.id)}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
