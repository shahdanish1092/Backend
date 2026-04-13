import { useState, useEffect } from 'react';
import { authApi } from '../api/auth';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { useAuth } from '../hooks';
import { Check, ArrowRight, FileText, Mic, Users, Zap } from 'lucide-react';

const features = [
  {
    icon: FileText,
    title: 'Invoice Processing',
    description: 'Upload invoices and let AI extract data, categorize expenses, and route for approval.',
  },
  {
    icon: Mic,
    title: 'Meeting Summaries',
    description: 'Transform meeting recordings into actionable summaries with tasks and follow-ups.',
  },
  {
    icon: Users,
    title: 'HR Integration',
    description: 'Connect your existing HR workflows through customizable webhook integrations.',
  },
  {
    icon: Zap,
    title: 'Smart Automation',
    description: 'AI-powered workflows that learn from your approvals to make smarter suggestions.',
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, login } = useAuth();
  const [showSuccess, setShowSuccess] = useState(false);
  const [connectedEmail, setConnectedEmail] = useState(null);

  // Check for OAuth callback
  useEffect(() => {
    const email = searchParams.get('email');
    const success = searchParams.get('success');
    
    if (success === 'true' && email) {
      login(email);
      setConnectedEmail(email);
      setShowSuccess(true);
    }
  }, [searchParams, login]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !showSuccess) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate, showSuccess]);

  const handleConnectGoogle = () => {
    // Redirect to backend to initiate Google OAuth
    authApi.initiateGoogleAuth();
  };

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-8 pb-8 text-center">
            <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-outfit font-bold text-slate-900 mb-2">
              Successfully Connected!
            </h2>
            <p className="text-slate-600 mb-6">
              You're now signed in as <strong>{connectedEmail}</strong>
            </p>
            <Button 
              onClick={handleGoToDashboard}
              className="bg-orange-500 hover:bg-orange-600"
              data-testid="go-to-dashboard-btn"
            >
              Go to Dashboard
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        {/* Background */}
        <div 
          className="absolute inset-0 bg-cover bg-center"
          style={{ 
            backgroundImage: `url(https://images.unsplash.com/photo-1772001936267-b6058748eff4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1ODB8MHwxfHNlYXJjaHwzfHxtb2Rlcm4lMjBjb3Jwb3JhdGUlMjB3b3Jrc3BhY2UlMjBidWlsZGluZ3xlbnwwfHx8fDE3NzUyODg5MTh8MA&ixlib=rb-4.1.0&q=85)` 
          }}
        />
        <div className="absolute inset-0 bg-slate-900/80" />

        {/* Content */}
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <img 
              src="https://customer-assets.emergentagent.com/job_office-auto-hub/artifacts/k42pj7ep_image.pngb" 
              alt="Spatial+ Logo" 
              className="h-12 w-auto"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>

          {/* Hero Text */}
          <div className="max-w-2xl">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-outfit font-bold text-white tracking-tight mb-6">
              Your AI-powered office, <span className="text-orange-500">automated</span>
            </h1>
            <p className="text-lg sm:text-xl text-slate-300 mb-8 leading-relaxed">
              Streamline your workflows with intelligent invoice processing, meeting summarization, 
              and seamless HR integrations. Let AI handle the routine so you can focus on what matters.
            </p>
            <Button 
              size="lg"
              onClick={handleConnectGoogle}
              className="bg-orange-500 hover:bg-orange-600 text-white text-lg px-8 py-6 h-auto"
              data-testid="connect-google-btn"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path
                  fill="currentColor"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="currentColor"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="currentColor"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="currentColor"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Connect Google Account
            </Button>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-outfit font-bold text-slate-900 mb-4">
            Everything you need to automate your office
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Powerful AI-driven tools that integrate with your existing workflows
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature) => (
            <Card key={feature.title} className="border-slate-200 hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center mb-4">
                  <feature.icon className="w-6 h-6 text-orange-600" />
                </div>
                <h3 className="text-lg font-outfit font-semibold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-slate-600">
                  {feature.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className="text-sm text-slate-500">
            © 2023 Spatial+. Create efficiencies.
          </p>
        </div>
      </footer>
    </div>
  );
}
