import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { hrApi } from '../api';
import { Users, Plug, CheckCircle, XCircle, RefreshCw, Settings, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';

const BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function HRConnectPage() {
  const [hrStatus, setHrStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [config, setConfig] = useState({
    webhookUrl: '',
    inputFormat: 'base64',
    callbackUrl: `${BASE_URL}/api/webhooks/hr/callback`,
    secret: '',
  });
  const userEmail = localStorage.getItem('user_email');

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const data = await hrApi.getHRStatus(userEmail);
      setHrStatus(data);
    } catch (error) {
      console.error('Failed to fetch HR status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, [userEmail]);

  const handleConnect = async () => {
    if (!config.webhookUrl || !config.secret) {
      toast.error('Please fill in all required fields');
      return;
    }
    try {
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/api/hr/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_email: userEmail,
          document_source: 'trigger://webhook_setup',
          file_base64: '',
          filename: 'hr-connection',
          mime_type: 'application/json',
          criteria: 'setup',
          top_k: 1
        })
      });
      const result = await response.json();
      setHrStatus({
        connected: true,
        last_sync: result.last_sync || new Date().toISOString(),
        webhook_url: config.webhookUrl,
      });
      setShowConfigModal(false);
      toast.success('HR workflow connected successfully');
    } catch (error) {
      toast.error('Failed to connect HR workflow');
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    try {
      const result = await hrApi.testConnection(userEmail);
      toast.success(`Connection test successful (${result.response_time})`);
    } catch (error) {
      toast.error('Connection test failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await hrApi.disconnectHR(userEmail);
      setHrStatus({ connected: false, last_sync: null, webhook_url: null });
      toast.success('HR workflow disconnected');
    } catch (error) {
      toast.error('Failed to disconnect');
    }
  };

  const handleUploadAndRun = async (file) => {
    const toBase64 = (f) => new Promise((res, rej) => {
      const r = new FileReader();
      r.readAsDataURL(f);
      r.onload = () => res(r.result.split(',')[1]);
      r.onerror = rej;
    });

    const base64 = await toBase64(file);
    const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'}/api/hr/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_email: userEmail,
        document_source: 'trigger://document_upload',
        file_base64: base64,
        filename: file.name,
        mime_type: file.type || 'application/pdf',
        criteria: 'minimum 2 years experience',
        top_k: 5
      })
    });
    const data = await response.json();
    toast.success(`HR workflow started. Request ID: ${data.request_id}`);
    return data;
  };

  return (
    <div className="space-y-6" data-testid="hr-connect-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">HR Connect</h1>
        <p className="text-sm text-slate-500 mt-1">Connect and manage your HR workflow integrations.</p>
      </div>

      {/* Connection Status Card */}
      <Card className="border-slate-200">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-lg ${hrStatus?.connected ? 'bg-emerald-100' : 'bg-slate-100'}`}>
                <Users className={`w-6 h-6 ${hrStatus?.connected ? 'text-emerald-600' : 'text-slate-500'}`} />
              </div>
              <div>
                <CardTitle className="text-lg font-outfit">HR Workflow</CardTitle>
                <CardDescription>n8n webhook integration for HR automation</CardDescription>
              </div>
            </div>
            <Badge 
              className={hrStatus?.connected 
                ? 'bg-emerald-100 text-emerald-800' 
                : 'bg-slate-100 text-slate-800'
              }
            >
              {hrStatus?.connected ? (
                <>
                  <CheckCircle className="w-3 h-3 mr-1" />
                  Connected
                </>
              ) : (
                <>
                  <XCircle className="w-3 h-3 mr-1" />
                  Not Connected
                </>
              )}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {hrStatus?.connected ? (
            <>
              <div className="bg-slate-50 rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Webhook URL</span>
                  <span className="font-mono text-slate-700 truncate max-w-xs">
                    {hrStatus.webhook_url || 'Configured'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Last Sync</span>
                  <span className="text-slate-700">
                    {hrStatus.last_sync 
                      ? new Date(hrStatus.last_sync).toLocaleString() 
                      : 'Never'
                    }
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={handleTestConnection}
                  disabled={isTesting}
                  data-testid="test-connection-btn"
                >
                  <RefreshCw className={`w-4 h-4 mr-2 ${isTesting ? 'animate-spin' : ''}`} />
                  Test Connection
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => setShowConfigModal(true)}
                  data-testid="reconfigure-btn"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Reconfigure
                </Button>
                <Button 
                  variant="outline"
                  onClick={handleDisconnect}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  data-testid="disconnect-hr-btn"
                >
                  Disconnect
                </Button>
              </div>
            </>
          ) : (
            <div className="text-center py-6">
              <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Plug className="w-8 h-8 text-slate-400" />
              </div>
              <p className="text-sm text-slate-600 mb-4">
                Connect your existing n8n HR workflow to enable automated employee data sync.
              </p>
              <Button 
                onClick={() => setShowConfigModal(true)}
                className="bg-orange-500 hover:bg-orange-600"
                data-testid="connect-hr-workflow-btn"
              >
                <Plug className="w-4 h-4 mr-2" />
                Connect HR Workflow
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg font-outfit">Process a CV</CardTitle>
          <CardDescription>Upload a candidate resume to start the HR pipeline</CardDescription>
        </CardHeader>
        <CardContent>
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={(e) => e.target.files[0] && handleUploadAndRun(e.target.files[0])}
            className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-orange-50 file:text-orange-700 hover:file:bg-orange-100"
          />
        </CardContent>
      </Card>

      {/* Info Note */}
      <Card className="border-amber-200 bg-amber-50">
        <CardContent className="py-4">
          <div className="flex gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-900">About HR Connect</p>
              <p className="text-sm text-amber-800 mt-1">
                HR automation is managed by your existing n8n workflow. This panel only connects 
                Spatial+ to your webhook endpoint. Ensure your n8n workflow is configured to 
                accept the selected input format.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Modal */}
      <Dialog open={showConfigModal} onOpenChange={setShowConfigModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-outfit">Configure HR Workflow</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium text-slate-700">HR Webhook URL *</label>
              <Input
                value={config.webhookUrl}
                onChange={(e) => setConfig({ ...config, webhookUrl: e.target.value })}
                placeholder="https://your-n8n-instance.com/webhook/..."
                className="mt-1"
                data-testid="hr-webhook-url-input"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Expected Input Format</label>
              <Select
                value={config.inputFormat}
                onValueChange={(value) => setConfig({ ...config, inputFormat: value })}
              >
                <SelectTrigger className="mt-1" data-testid="input-format-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="base64">Base64 PDF</SelectItem>
                  <SelectItem value="url">File URL</SelectItem>
                  <SelectItem value="multipart">Multipart Form</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Callback Webhook URL</label>
              <Input
                value={config.callbackUrl}
                disabled
                className="mt-1 bg-slate-50"
              />
              <p className="text-xs text-slate-500 mt-1">Auto-configured for this instance</p>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Shared Secret *</label>
              <Input
                type="password"
                value={config.secret}
                onChange={(e) => setConfig({ ...config, secret: e.target.value })}
                placeholder="Enter shared secret for authentication"
                className="mt-1"
                data-testid="hr-secret-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowConfigModal(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleConnect}
              className="bg-orange-500 hover:bg-orange-600"
              data-testid="save-hr-config-btn"
            >
              Save & Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
