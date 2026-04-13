import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { UploadZone, StatusStepper, TableSkeleton, NoInvoices } from '../components';
import { useInvoices } from '../hooks';
import { Calendar, Search, Filter, Eye, X } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const processingSteps = ['Received', 'OCR Extraction', 'AI Analysis', 'Awaiting Approval'];

const statusColors = {
  approved: 'bg-emerald-100 text-emerald-800',
  pending: 'bg-amber-100 text-amber-800',
  processing: 'bg-blue-100 text-blue-800',
  rejected: 'bg-red-100 text-red-800',
};

export default function InvoiceManagerPage() {
  const { invoices, isLoading, uploadInvoice, uploadStatus, clearUploadStatus } = useInvoices();
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [filters, setFilters] = useState({
    status: 'all',
    search: '',
    dateFrom: '',
    dateTo: '',
    amountMin: '',
    amountMax: '',
  });
  const [showFilters, setShowFilters] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileSelect = useCallback(async (file) => {
    if (!file) return;
    
    setIsUploading(true);
    setCurrentStep(0);

    // Simulate step progression
    const stepInterval = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= 3) {
          clearInterval(stepInterval);
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    try {
      await uploadInvoice(file);
      toast.success('Invoice uploaded successfully');
    } catch (error) {
      toast.error('Failed to upload invoice');
    } finally {
      setIsUploading(false);
      setTimeout(() => {
        clearUploadStatus();
        setCurrentStep(0);
      }, 2000);
    }
  }, [uploadInvoice, clearUploadStatus]);

  const filteredInvoices = invoices.filter(invoice => {
    if (filters.status !== 'all' && invoice.status !== filters.status) return false;
    if (filters.search && !invoice.vendor.toLowerCase().includes(filters.search.toLowerCase()) && 
        !invoice.id.toLowerCase().includes(filters.search.toLowerCase())) return false;
    if (filters.amountMin && invoice.amount < parseFloat(filters.amountMin)) return false;
    if (filters.amountMax && invoice.amount > parseFloat(filters.amountMax)) return false;
    return true;
  });

  return (
    <div className="space-y-6" data-testid="invoice-manager-page">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-outfit font-bold text-slate-900">Invoice Manager</h1>
        <p className="text-sm text-slate-500 mt-1">Upload and manage invoices with AI-powered processing.</p>
      </div>

      {/* Upload Section */}
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-lg font-outfit">Upload Invoice</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <UploadZone
            accept=".pdf,.png,.jpg,.jpeg"
            onFileSelect={handleFileSelect}
            isUploading={isUploading}
            label="Drop invoice here or click to upload"
            description="Supports PDF, PNG, JPG files up to 10MB"
          />
          
          {(isUploading || uploadStatus) && (
            <div className="mt-6 p-4 bg-slate-50 rounded-lg">
              <p className="text-sm font-medium text-slate-700 mb-4">Processing Status</p>
              <StatusStepper steps={processingSteps} currentStep={currentStep} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Invoice Log */}
      <Card className="border-slate-200">
        <CardHeader className="border-b border-slate-100">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <CardTitle className="text-lg font-outfit">Invoice Log</CardTitle>
            <div className="flex items-center gap-2">
              <div className="relative flex-1 sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Search invoices..."
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="pl-9"
                  data-testid="search-invoices-input"
                />
              </div>
              <Button 
                variant="outline" 
                size="icon"
                onClick={() => setShowFilters(!showFilters)}
                data-testid="toggle-filters-btn"
              >
                <Filter className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Filter Bar */}
          {showFilters && (
            <div className="flex flex-wrap gap-3 mt-4 pt-4 border-t border-slate-100">
              <Select
                value={filters.status}
                onValueChange={(value) => setFilters({ ...filters, status: value })}
              >
                <SelectTrigger className="w-[140px]" data-testid="status-filter">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  placeholder="Min $"
                  value={filters.amountMin}
                  onChange={(e) => setFilters({ ...filters, amountMin: e.target.value })}
                  className="w-24"
                  data-testid="amount-min-filter"
                />
                <span className="text-slate-400">-</span>
                <Input
                  type="number"
                  placeholder="Max $"
                  value={filters.amountMax}
                  onChange={(e) => setFilters({ ...filters, amountMax: e.target.value })}
                  className="w-24"
                  data-testid="amount-max-filter"
                />
              </div>
              <Button 
                variant="ghost" 
                size="sm"
                onClick={() => setFilters({ status: 'all', search: '', dateFrom: '', dateTo: '', amountMin: '', amountMax: '' })}
              >
                Clear filters
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : filteredInvoices.length === 0 ? (
            <NoInvoices />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50">
                  <TableHead>Date</TableHead>
                  <TableHead>Invoice #</TableHead>
                  <TableHead>Vendor</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredInvoices.map((invoice) => (
                  <TableRow key={invoice.id} data-testid={`invoice-row-${invoice.id}`}>
                    <TableCell className="text-slate-500">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        {format(new Date(invoice.date), 'MMM d, yyyy')}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{invoice.id}</TableCell>
                    <TableCell>{invoice.vendor}</TableCell>
                    <TableCell className="font-medium">
                      ${invoice.amount.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[invoice.status]}>
                        {invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedInvoice(invoice)}
                        data-testid={`view-invoice-btn-${invoice.id}`}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Invoice Details Modal */}
      <Dialog open={!!selectedInvoice} onOpenChange={() => setSelectedInvoice(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="font-outfit">Invoice Details</DialogTitle>
          </DialogHeader>
          {selectedInvoice && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-slate-500">Invoice Number</p>
                  <p className="font-medium">{selectedInvoice.id}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Vendor</p>
                  <p className="font-medium">{selectedInvoice.vendor}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Amount</p>
                  <p className="font-medium text-lg">${selectedInvoice.amount.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Date</p>
                  <p className="font-medium">{format(new Date(selectedInvoice.date), 'MMMM d, yyyy')}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-500">Status</p>
                  <Badge className={statusColors[selectedInvoice.status]}>
                    {selectedInvoice.status.charAt(0).toUpperCase() + selectedInvoice.status.slice(1)}
                  </Badge>
                </div>
              </div>

              {selectedInvoice.extracted_data && (
                <div className="border-t pt-4">
                  <p className="text-sm font-medium text-slate-700 mb-3">Extracted Data</p>
                  <div className="bg-slate-50 rounded-lg p-4">
                    <p className="text-sm text-slate-600 mb-2">
                      <strong>Category:</strong> {selectedInvoice.extracted_data.category || 'General'}
                    </p>
                    {selectedInvoice.extracted_data.line_items && (
                      <div>
                        <p className="text-sm font-medium text-slate-700 mb-2">Line Items:</p>
                        <div className="space-y-1">
                          {selectedInvoice.extracted_data.line_items.map((item, index) => (
                            <div key={index} className="flex justify-between text-sm">
                              <span>{item.description} (x{item.qty})</span>
                              <span className="font-medium">${(item.qty * item.rate).toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
