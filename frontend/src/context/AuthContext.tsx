'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
} from 'react';
import { AUTH_TOKEN_STORAGE_KEY } from '@/api/client';

type AuthContextValue = {
  /** 已完成从 localStorage 读取（避免 SSR 与客户端不一致闪烁） */
  ready: boolean;
  isAuthenticated: boolean;
  /** 同步登出并通知订阅方 */
  logout: () => void;
  /** 写入 token 并广播（同标签页登录成功后调用） */
  setToken: (token: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_EVENT = 'newhigh-auth-change';

function readTokenSync(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return Boolean(localStorage.getItem(AUTH_TOKEN_STORAGE_KEY)?.trim());
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);

  const readToken = useCallback(() => readTokenSync(), []);

  useLayoutEffect(() => {
    setHasToken(readToken());
    setReady(true);
  }, [readToken]);

  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key === AUTH_TOKEN_STORAGE_KEY || e.key === null) {
        setHasToken(readToken());
      }
    };
    const onAuth = () => setHasToken(readToken());
    window.addEventListener('storage', onStorage);
    window.addEventListener(AUTH_EVENT, onAuth);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener(AUTH_EVENT, onAuth);
    };
  }, [readToken]);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setHasToken(false);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(AUTH_EVENT));
    }
  }, []);

  const setToken = useCallback((token: string) => {
    try {
      localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token.trim());
    } catch {
      /* ignore */
    }
    setHasToken(true);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event(AUTH_EVENT));
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ready,
      isAuthenticated: hasToken,
      logout,
      setToken,
    }),
    [ready, hasToken, logout, setToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}

/** 登录成功后通知 AuthContext（同页已 setItem 时触发） */
export function notifyAuthChanged(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(AUTH_EVENT));
  }
}
