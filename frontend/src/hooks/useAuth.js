import { useState, useEffect } from 'react';
import { authApi } from '../api/auth';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const email = authApi.getCurrentUser();
    if (email) {
      setIsAuthenticated(true);
      setUser({ email });
    }
    setIsLoading(false);
  }, []);

  const logout = () => {
    authApi.logout();
    setIsAuthenticated(false);
    setUser(null);
  };

  return { isAuthenticated, isLoading, user, logout };
}

export default useAuth;
