import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const API_URL = process.env.REACT_APP_BACKEND_URL + '/api';
const HEARTBEAT_INTERVAL = 60000; // 1 minuto

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const heartbeatRef = useRef(null);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [token]);

  // Heartbeat para manter presença online
  useEffect(() => {
    if (user && token) {
      // Enviar heartbeat imediatamente
      sendHeartbeat();
      
      // Configurar intervalo
      heartbeatRef.current = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
      
      // Cleanup
      return () => {
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
        }
      };
    }
  }, [user, token]);

  const sendHeartbeat = async () => {
    try {
      await axios.post(`${API_URL}/presence/heartbeat`);
    } catch (error) {
      console.error('Heartbeat failed:', error);
    }
  };

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API_URL}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/auth/login`, { email, password });
    const { token: newToken, user: userData } = response.data;
    localStorage.setItem('token', newToken);
    axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
    setToken(newToken);
    setUser(userData);
    return userData;
  };

  const register = async (email, password, name, role) => {
    const response = await axios.post(`${API_URL}/auth/register`, {
      email,
      password,
      name,
      role
    });
    return response.data;
  };

  const logout = async () => {
    // Notificar servidor que está offline
    try {
      if (token) {
        await axios.post(`${API_URL}/presence/offline`);
      }
    } catch (error) {
      console.error('Failed to notify offline:', error);
    }
    
    // Limpar heartbeat
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }
    
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
