import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../hooks/useAuth';
const DEMO_USERS = [
  { username: 'viewer', password: 'viewer123', role: 'viewer', name: 'Viewer User' },
  { username: 'operator', password: 'operator123', role: 'operator', name: 'Operator User' },
  { username: 'admin', password: 'admin123', role: 'admin', name: 'Admin User' },
];

export function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    await new Promise((r) => setTimeout(r, 500));

    const user = DEMO_USERS.find((u) => u.username === username && u.password === password);
    if (user) {
      const token = `demo-token-${user.username}-${Date.now()}`;
      login({ sub: user.username, roles: [user.role], name: user.name }, token);
      navigate('/');
    } else {
      setError('Invalid credentials. Use demo accounts: viewer/viewer123, operator/operator123, admin/admin123');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-100 text-blue-600 mb-4">
              <Shield className="h-8 w-8" aria-hidden="true" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Cloud Security Scanner</h1>
            <p className="text-gray-500 mt-2">Sign in to access your security dashboard</p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3 text-red-700" role="alert">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <p className="text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="username" className="label">Username</label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="input"
                placeholder="Enter username"
                required
                disabled={loading}
              />
            </div>

            <div>
              <label htmlFor="password" className="label">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="Enter password"
                required
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              className="btn-primary w-full py-3"
              disabled={loading}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-8 space-y-3">
            <p className="text-center text-sm text-gray-500">Demo accounts:</p>
            <div className="space-y-2 text-sm">
              {DEMO_USERS.map((u) => (
                <div
                  key={u.username}
                  className="flex items-center justify-between p-3 rounded-lg bg-gray-50 hover:bg-gray-100 cursor-pointer transition-colors"
                  onClick={() => {
                    setUsername(u.username);
                    setPassword(u.password);
                  }}
                >
                  <span className="font-mono">{u.username} / {u.password}</span>
                  <span className="text-gray-500 capitalize">{u.role}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}