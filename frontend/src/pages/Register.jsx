import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button, Input, Card, CardBody } from '../components/ui';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await register(email, password, fullName);
      navigate('/projects');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registrácia zlyhala');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center py-12 px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <svg className="mx-auto h-12 w-12 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <h2 className="mt-4 text-3xl font-bold text-gray-900">Registrácia</h2>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="bg-red-50 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}

              <Input
                label="Meno"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoFocus
              />

              <Input
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />

              <Input
                label="Heslo"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
              />

              <Button type="submit" className="w-full" loading={loading}>
                Registrovať
              </Button>
            </form>

            <p className="mt-4 text-center text-sm text-gray-600">
              Už máte účet?{' '}
              <Link to="/login" className="text-blue-600 hover:text-blue-500 font-medium">
                Prihlásiť sa
              </Link>
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
