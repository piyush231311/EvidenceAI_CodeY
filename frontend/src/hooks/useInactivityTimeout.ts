import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes
const WARNING_TIMEOUT_MS = 14 * 60 * 1000;    // 14 minutes (60s before logout)

export const useInactivityTimeout = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showWarning, setShowWarning] = useState<boolean>(false);
  const [countdown, setCountdown] = useState<number>(60);

  const lastActivityRef = useRef<number>(Date.now());
  const warningTimerRef = useRef<number | null>(null);
  const logoutTimerRef = useRef<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);

  const performLogout = useCallback(async () => {
    setShowWarning(false);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    await logout();
    navigate('/login?reason=inactivity');
  }, [logout, navigate]);

  const resetTimer = useCallback(() => {
    lastActivityRef.current = Date.now();
    if (showWarning) {
      setShowWarning(false);
    }
    if (countdownIntervalRef.current) {
      clearInterval(countdownIntervalRef.current);
      countdownIntervalRef.current = null;
    }

    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);

    if (!user) return;

    warningTimerRef.current = window.setTimeout(() => {
      setShowWarning(true);
      setCountdown(60);

      countdownIntervalRef.current = window.setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
            performLogout();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }, WARNING_TIMEOUT_MS);

    logoutTimerRef.current = window.setTimeout(() => {
      performLogout();
    }, INACTIVITY_TIMEOUT_MS);
  }, [user, showWarning, performLogout]);

  useEffect(() => {
    if (!user) {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      setShowWarning(false);
      return;
    }

    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];
    const handleUserActivity = () => {
      // If warning is not visible, user activity resets the timers
      if (!showWarning) {
        // Throttle resetting
        if (Date.now() - lastActivityRef.current > 2000) {
          resetTimer();
        }
      }
    };

    events.forEach((evt) => window.addEventListener(evt, handleUserActivity, { passive: true }));
    resetTimer();

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, handleUserActivity));
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    };
  }, [user, resetTimer, showWarning]);

  const staySignedIn = () => {
    resetTimer();
  };

  return {
    showWarning,
    countdown,
    staySignedIn,
    signOutNow: performLogout
  };
};
