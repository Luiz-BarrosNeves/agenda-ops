import { useEffect, useCallback } from 'react';

/**
 * Hook para gerenciar atalhos de teclado globais
 * @param {Object} shortcuts - Mapa de atalhos: { 'n': () => {}, 'ArrowLeft': () => {} }
 * @param {boolean} enabled - Se os atalhos estão habilitados
 */
export const useKeyboardShortcuts = (shortcuts, enabled = true) => {
  const handleKeyDown = useCallback((event) => {
    if (!enabled) return;

    // Ignorar se estiver digitando em input, textarea ou contenteditable
    const target = event.target;
    const tagName = target.tagName.toLowerCase();
    const isEditable = target.isContentEditable;
    const isInput = tagName === 'input' || tagName === 'textarea' || tagName === 'select';

    if (isEditable || isInput) return;

    // Construir a key combinada
    let key = event.key;
    
    // Adicionar modificadores
    if (event.ctrlKey) key = `Ctrl+${key}`;
    if (event.altKey) key = `Alt+${key}`;
    if (event.shiftKey && key.length > 1) key = `Shift+${key}`;
    if (event.metaKey) key = `Meta+${key}`;

    // Verificar se existe handler para esta key
    const handler = shortcuts[key] || shortcuts[event.key];
    
    if (handler) {
      event.preventDefault();
      handler(event);
    }
  }, [shortcuts, enabled]);

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown, enabled]);
};

/**
 * Componente para exibir dicas de atalhos
 */
export const ShortcutsHelp = ({ shortcuts }) => {
  return (
    <div className="text-xs text-slate-500 space-y-1">
      <p className="font-medium text-slate-600 mb-2">Atalhos de teclado:</p>
      {Object.entries(shortcuts).map(([key, description]) => (
        <div key={key} className="flex items-center gap-2">
          <kbd className="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded text-[10px] font-mono">
            {key}
          </kbd>
          <span>{description}</span>
        </div>
      ))}
    </div>
  );
};
