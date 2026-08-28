"use client";

/**
 * 认证状态管理：token 存 localStorage，通过 Context 提供登录态
 */
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { authApi, clearToken, getToken, setToken } from "./api";

interface User {
  id: string;
  email: string;
  name?: string;
  target_role?: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (body: { email: string; password: string; name?: string; target_role?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 启动时恢复登录态
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        clearToken();
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const data = await authApi.login({ email, password });
    setToken(data.access_token);
    const me = await authApi.me();
    setUser(me);
  };

  const register = async (body: { email: string; password: string; name?: string; target_role?: string }) => {
    await authApi.register(body);
    // 注册成功后自动登录
    await login(body.email, body.password);
  };

  const logout = () => {
    clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth 必须在 AuthProvider 内使用");
  return ctx;
}
