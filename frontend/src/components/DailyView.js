import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { usersAPI } from '../utils/api';
import { AppointmentCard } from './AppointmentCard';

const TIME_SLOTS = [
  '08:00', '08:20', '08:40',
  '09:00', '09:20', '09:40',
  '10:00', '10:20', '10:40',
  '11:00', '11:20', '11:40',
  '12:00', '12:20', '12:40',
  '13:00', '13:20', '13:40',
  '14:00', '14:20', '14:40',
  '15:00', '15:20', '15:40',
  '16:00', '16:20', '16:40',
  '17:00', '17:20', '17:40',
  '18:00', '18:20', '18:40'
];

export const DailyView = ({ appointments, currentDate, onEditAppointment, userRole }) => {
  const [attendants, setAttendants] = useState([]);

  useEffect(() => {
    loadAttendants();
  }, []);

  const loadAttendants = async () => {
    try {
      if (userRole === 'admin' || userRole === 'supervisor') {
        const response = await usersAPI.getAttendants();
        setAttendants(response.data);
      } else if (userRole === 'agente') {
        const response = await usersAPI.getMe();
        setAttendants([response.data]);
      } else {
        setAttendants([]);
      }
    } catch (error) {
      console.error('Erro ao carregar agentes:', error);
      setAttendants([]);
    }
  };

  const handleCardClick = (appointment) => {
    if (userRole === 'admin') {
      return;
    }
    onEditAppointment(appointment);
  };

  const getAppointmentForSlot = (userId, timeSlot) => {
    return appointments.find(apt => 
      apt.user_id === userId && 
      apt.time_slot === timeSlot &&
      apt.status !== 'cancelado'
    );
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden" data-testid="daily-view">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-slate-500 w-24">
                Horário
              </th>
              {attendants.map(attendant => (
                <th key={attendant.id} className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-slate-500 min-w-[200px]">
                  <div className="flex items-center justify-center gap-2">
                    {attendant.avatar_url ? (
                      <img src={attendant.avatar_url} alt={attendant.name} className="w-8 h-8 rounded-full object-cover" />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-slate-300 flex items-center justify-center text-white font-medium text-sm">
                        {attendant.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span>{attendant.name}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TIME_SLOTS.map((slot, idx) => (
              <tr key={slot} className={`border-b border-slate-100 ${idx % 3 === 0 ? 'bg-slate-50/50' : 'bg-white'}`}>
                <td className="px-4 py-2 text-sm font-medium text-slate-700">
                  {slot}
                </td>
                {attendants.map(attendant => {
                  const appointment = getAppointmentForSlot(attendant.id, slot);
                  return (
                    <td key={`${attendant.id}-${slot}`} className="px-2 py-2">
                      {appointment ? (
                        <AppointmentCard
                          appointment={appointment}
                          onEdit={userRole !== 'admin' ? () => handleCardClick(appointment) : null}
                          compact
                        />
                      ) : (
                        <div className="h-16 flex items-center justify-center text-xs text-slate-400">
                          Livre
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
