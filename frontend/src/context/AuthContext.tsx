import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { api, User, AuthResponse } from '../services/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<AuthResponse>;
  register: (username: string, password: string) => Promise<AuthResponse>;
  logout: (allDevices?: boolean) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  recover: (username: string, recoveryCode: string, newPassword: string) => Promise<AuthResponse>;
  regenerateRecoveryCodes: (password: string) => Promise<string[]>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_CHANNEL_NAME = 'evidence_ai_auth';

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Check current auth status via httpOnly cookie on mount
  const checkAuth = useCallback(async () => {
    try {
      const currentUser = await api.auth.getMe();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Cross-tab synchronization via BroadcastChannel
  useEffect(() => {
    let channel: BroadcastChannel | null = null;
    try {
      channel = new BroadcastChannel(AUTH_CHANNEL_NAME);
      channel.onmessage = (event) => {
        if (event.data === 'LOGOUT') {
          setUser(null);
          window.location.replace('/login');
        } else if (event.data === 'LOGIN') {
          checkAuth();
        }
      };
    } catch (e) {
      // Fallback if BroadcastChannel not supported in environment
    }

    // Listen to 401 events dispatched from apiFetch
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener('evidence-ai-unauthorized', handleUnauthorized);

    return () => {
      if (channel) channel.close();
      window.removeEventListener('evidence-ai-unauthorized', handleUnauthorized);
    };
  }, [checkAuth]);

  const broadcastEvent = (action: 'LOGIN' | 'LOGOUT') => {
    try {
      const channel = new BroadcastChannel(AUTH_CHANNEL_NAME);
      channel.postMessage(action);
      channel.close();
    } catch (e) {}
  };

  const login = async (username: string, password: string): Promise<AuthResponse> => {
    const res = await api.auth.login(username, password);
    setUser(res.user);
    broadcastEvent('LOGIN');
    return res;
  };

  const register = async (username: string, password: string): Promise<AuthResponse> => {
    const res = await api.auth.register(username, password);
    setUser(res.user);
    broadcastEvent('LOGIN');
    return res;
  };

  const logout = async (allDevices: boolean = false): Promise<void> => {
    try {
      await api.auth.logout(allDevices);
    } catch (e) {
      // Proceed even if network request fails
    } finally {
      setUser(null);
      broadcastEvent('LOGOUT');
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    await api.auth.changePassword(currentPassword, newPassword);
  };

  const recover = async (username: string, recoveryCode: string, newPassword: string): Promise<AuthResponse> => {
    const res = await api.auth.recover(username, recoveryCode, newPassword);
    setUser(res.user);
    broadcastEvent('LOGIN');
    return res;
  };

  const regenerateRecoveryCodes = async (password: string): Promise<string[]> => {
    return await api.auth.regenerateRecoveryCodes(password);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        changePassword,
        recover,
        regenerateRecoveryCodes,
        checkAuth
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
