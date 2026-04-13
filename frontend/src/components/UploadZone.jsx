import { useCallback, useState } from 'react';
import { Upload, File, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function UploadZone({ 
  accept = '*', 
  onFileSelect, 
  isUploading = false,
  label = 'Drop files here or click to upload',
  description = 'Supports PDF, PNG, JPG files'
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setSelectedFile(files[0]);
      onFileSelect?.(files[0]);
    }
  }, [onFileSelect]);

  const handleFileInput = useCallback((e) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      onFileSelect?.(files[0]);
    }
  }, [onFileSelect]);

  const clearFile = useCallback((e) => {
    e.stopPropagation();
    setSelectedFile(null);
  }, []);

  return (
    <div
      data-testid="upload-zone"
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all',
        'flex flex-col items-center justify-center gap-3',
        isDragging 
          ? 'border-orange-500 bg-orange-50' 
          : 'border-slate-300 bg-slate-50 hover:bg-slate-100 hover:border-orange-400',
        isUploading && 'opacity-50 pointer-events-none'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => document.getElementById('file-input')?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept={accept}
        onChange={handleFileInput}
        className="hidden"
        data-testid="file-input"
      />

      {selectedFile ? (
        <div className="flex items-center gap-3 bg-white rounded-lg px-4 py-3 border border-slate-200">
          <File className="w-8 h-8 text-orange-500" />
          <div className="text-left">
            <p className="text-sm font-medium text-slate-900">{selectedFile.name}</p>
            <p className="text-xs text-slate-500">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <button
            onClick={clearFile}
            className="p-1 hover:bg-slate-100 rounded"
            data-testid="clear-file-btn"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      ) : (
        <>
          <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
            <Upload className="w-6 h-6 text-orange-500" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700">{label}</p>
            <p className="text-xs text-slate-500 mt-1">{description}</p>
          </div>
        </>
      )}

      {isUploading && (
        <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-slate-600">Uploading...</span>
          </div>
        </div>
      )}
    </div>
  );
}
