import { useEffect, useCallback } from 'react';
import { QUICK_EXIT_URL } from '../content/guidance.js';

export const triggerQuickExit = () => {
  try {
    // Replace current history entry so Back button cannot return to app
    window.location.replace(QUICK_EXIT_URL);
  } catch (err) {
    window.location.href = QUICK_EXIT_URL;
  }
};

export const useQuickExit = () => {
  const handleExit = useCallback(() => {
    triggerQuickExit();
  }, []);

  useEffect(() => {
    let lastEscapePress = 0;
    const ESCAPE_THRESHOLD_MS = 500;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const now = Date.now();
        if (now - lastEscapePress <= ESCAPE_THRESHOLD_MS) {
          // Double Escape detected
          e.preventDefault();
          triggerQuickExit();
        } else {
          lastEscapePress = now;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown, true);
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true);
    };
  }, []);

  return { triggerQuickExit: handleExit };
};
