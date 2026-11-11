import { createContext, useCallback, useContext, useEffect, useState } from "react";
import api, { tokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async () => {
    if (!tokens.access) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const { data } = await api.get("/auth/me/");
      setUser(data);
      return data;
    } catch {
      tokens.clear();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
    const onLogout = () => setUser(null);
    window.addEventListener("af:logout", onLogout);
    return () => window.removeEventListener("af:logout", onLogout);
  }, [loadMe]);

  const login = async (username, password) => {
    const { data } = await api.post("/auth/login/", { username, password });
    tokens.set(data);
    return loadMe();
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register/", payload);
    tokens.set(data.tokens);
    return loadMe();
  };

  const logout = () => {
    tokens.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser: loadMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
