import { useEffect, useRef, useCallback } from 'react';

// Criar um som de notificação usando Web Audio API
const createNotificationSound = () => {
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  
  return () => {
    // Criar um som de "ding" agradável
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    // Configurar o som
    oscillator.frequency.setValueAtTime(880, audioContext.currentTime); // A5
    oscillator.frequency.setValueAtTime(1100, audioContext.currentTime + 0.1); // C#6
    oscillator.type = 'sine';
    
    // Envelope de volume (fade in e fade out)
    gainNode.gain.setValueAtTime(0, audioContext.currentTime);
    gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05);
    gainNode.gain.linearRampToValueAtTime(0, audioContext.currentTime + 0.3);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
  };
};

// Criar um som de urgência (para pendentes)
const createUrgentSound = () => {
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  
  return () => {
    // Tocar duas notas em sequência
    const playNote = (freq, time) => {
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(freq, time);
      oscillator.type = 'sine';
      
      gainNode.gain.setValueAtTime(0, time);
      gainNode.gain.linearRampToValueAtTime(0.25, time + 0.03);
      gainNode.gain.linearRampToValueAtTime(0, time + 0.15);
      
      oscillator.start(time);
      oscillator.stop(time + 0.15);
    };
    
    const now = audioContext.currentTime;
    playNote(784, now);        // G5
    playNote(988, now + 0.15); // B5
    playNote(1175, now + 0.3); // D6
  };
};

export const useNotificationSound = (enabled = true) => {
  const playSoundRef = useRef(null);
  const playUrgentRef = useRef(null);
  const audioInitializedRef = useRef(false);

  // Inicializar áudio no primeiro uso
  const initAudio = useCallback(() => {
    if (!audioInitializedRef.current && enabled) {
      try {
        playSoundRef.current = createNotificationSound();
        playUrgentRef.current = createUrgentSound();
        audioInitializedRef.current = true;
      } catch (error) {
        console.warn('Web Audio API não suportada:', error);
      }
    }
  }, [enabled]);

  // Tocar som normal
  const playSound = useCallback(() => {
    if (!enabled) return;
    initAudio();
    if (playSoundRef.current) {
      try {
        playSoundRef.current();
      } catch (error) {
        console.warn('Erro ao tocar som:', error);
      }
    }
  }, [enabled, initAudio]);

  // Tocar som urgente (para novos pendentes)
  const playUrgentSound = useCallback(() => {
    if (!enabled) return;
    initAudio();
    if (playUrgentRef.current) {
      try {
        playUrgentRef.current();
      } catch (error) {
        console.warn('Erro ao tocar som urgente:', error);
      }
    }
  }, [enabled, initAudio]);

  return { playSound, playUrgentSound, initAudio };
};

export default useNotificationSound;
