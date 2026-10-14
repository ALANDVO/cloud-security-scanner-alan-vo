import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { Login } from '../pages/Login';
import { useAuthStore } from '../hooks/useAuth';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
};

describe('Login Page', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it('renders login form with demo accounts', () => {
    render(<Login />, { wrapper: createWrapper() });
    expect(screen.getByText('Cloud Security Scanner')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByText('viewer / viewer123')).toBeInTheDocument();
    expect(screen.getByText('operator / operator123')).toBeInTheDocument();
    expect(screen.getByText('admin / admin123')).toBeInTheDocument();
  });

  it('shows error for invalid credentials', async () => {
    render(<Login />, { wrapper: createWrapper() });
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'wrong' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong' } });
    await act(async () => {
      fireEvent.click(screen.getByText('Sign in'));
    });
    await waitFor(() => {
      expect(screen.getByText(/Invalid credentials/)).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('logs in with valid demo credentials', async () => {
    render(<Login />, { wrapper: createWrapper() });
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'viewer' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'viewer123' } });
    await act(async () => {
      fireEvent.click(screen.getByText('Sign in'));
    });
    await waitFor(() => {
      expect(screen.getByText('viewer')).toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

describe('Auth Store', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  });

  it('sets user and token on login', () => {
    const { login } = useAuthStore.getState();
    const user = { sub: 'test', roles: ['viewer'], name: 'Test User' };
    const token = 'test-token';
    login(user, token);
    const state = useAuthStore.getState();
    expect(state.user).toEqual(user);
    expect(state.isAuthenticated).toBe(true);
  });

  it('clears user on logout', () => {
    const { login, logout } = useAuthStore.getState();
    login({ sub: 'test', roles: ['viewer'] }, 'token');
    logout();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});