import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { X, Paperclip, Loader2, AlertCircle } from 'lucide-react';
import { uploadDocument, listDocuments } from '../../lib/api';
import { useStore } from '../../store';
import type { DocumentUploadPayload } from '../../types';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UploadModal({ isOpen, onClose }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addDocument = useStore((state) => state.addDocument);
  const setDocuments = useStore((state) => state.setDocuments);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const droppedFile = acceptedFiles[0];
      setFile(droppedFile);
      // Auto-fill title from filename (without extension)
      if (!title) {
        const nameWithoutExt = droppedFile.name.replace(/\.[^/.]+$/, '');
        setTitle(nameWithoutExt);
      }
      setError(null);
    }
  }, [title]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: false,
    onDropRejected: (rejections) => {
      const rejection = rejections[0];
      if (rejection.errors[0]?.code === 'file-too-large') {
        setError('File is too large. Maximum size is 10MB.');
      } else if (rejection.errors[0]?.code === 'file-invalid-type') {
        setError('Invalid file type. Only PDF and TXT files are supported.');
      } else {
        setError('File upload failed. Please try again.');
      }
    },
  });

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const payload: DocumentUploadPayload = {
        file,
        title: title || file.name.replace(/\.[^/.]+$/, ''),
        description: description || undefined,
      };

      const uploadedDoc = await uploadDocument(payload);
      addDocument(uploadedDoc);

      // Start polling for status if pending or processing
      if (uploadedDoc.status === 'pending' || uploadedDoc.status === 'processing') {
        pollDocumentStatus(uploadedDoc.id);
      }

      // Reset and close
      resetForm();
      onClose();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      
      if (errorMessage.includes('413') || errorMessage.toLowerCase().includes('too large')) {
        setError('File is too large. Maximum size is 10MB.');
      } else if (errorMessage.includes('422') || errorMessage.toLowerCase().includes('unsupported')) {
        setError('Unsupported file format. Only PDF and TXT files are accepted.');
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const pollDocumentStatus = (docId: string) => {
    const poll = setInterval(async () => {
      try {
        const docs = await listDocuments();
        const doc = docs.find((d) => d.id === docId);
        
        if (doc && (doc.status === 'ready' || doc.status === 'failed')) {
          setDocuments(docs);
          clearInterval(poll);
        } else if (doc) {
          setDocuments(docs);
        }
      } catch (err) {
        console.error('Failed to poll document status:', err);
        clearInterval(poll);
      }
    }, 3000);
  };

  const resetForm = () => {
    setFile(null);
    setTitle('');
    setDescription('');
    setError(null);
    setIsUploading(false);
  };

  const handleClose = () => {
    if (!isUploading) {
      resetForm();
      onClose();
    }
  };

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      resetForm();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          background: 'var(--color-surface)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 'var(--space-6)',
        }}
        onClick={handleClose}
      >
        {/* Modal */}
        <div
          style={{
            background: 'var(--color-surface)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--color-border)',
            width: '100%',
            maxWidth: '500px',
            padding: 'var(--space-6)',
            position: 'relative',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 'var(--space-6)',
            }}
          >
            <h2
              style={{
                fontSize: '18px',
                fontWeight: 600,
                color: 'var(--color-text)',
              }}
            >
              Upload study material
            </h2>
            <button
              onClick={handleClose}
              disabled={isUploading}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: isUploading ? 'not-allowed' : 'pointer',
                padding: 'var(--space-1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'color 0.2s',
              }}
              onMouseEnter={(e) => {
                if (!isUploading) {
                  e.currentTarget.style.color = 'var(--color-text)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--color-text-muted)';
              }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Drop zone */}
          <div
            {...getRootProps()}
            style={{
              border: `2px dashed ${isDragActive ? 'var(--color-accent)' : 'var(--color-border)'}`,
              borderRadius: 'var(--radius-md)',
              padding: 'var(--space-8)',
              textAlign: 'center',
              cursor: isUploading ? 'not-allowed' : 'pointer',
              background: isDragActive ? 'var(--color-accent-dim)' : 'transparent',
              transition: 'all 0.2s',
              marginBottom: 'var(--space-5)',
            }}
          >
            <input {...getInputProps()} disabled={isUploading} />
            <Paperclip
              size={32}
              style={{
                color: 'var(--color-text-muted)',
                marginBottom: 'var(--space-3)',
              }}
            />
            {file ? (
              <>
                <p
                  style={{
                    color: 'var(--color-text)',
                    fontSize: '14px',
                    fontWeight: 500,
                    marginBottom: 'var(--space-1)',
                  }}
                >
                  {file.name}
                </p>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '12px' }}>
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </>
            ) : (
              <>
                <p
                  style={{
                    color: 'var(--color-text)',
                    fontSize: '14px',
                    marginBottom: 'var(--space-2)',
                  }}
                >
                  Drop your PDF or .txt file here
                </p>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '13px' }}>
                  or click to browse
                </p>
                <p
                  style={{
                    color: 'var(--color-text-muted)',
                    fontSize: '11px',
                    marginTop: 'var(--space-3)',
                  }}
                >
                  Maximum file size: 10MB
                </p>
              </>
            )}
          </div>

          {/* Title input */}
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <label
              htmlFor="title"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--color-text)',
                marginBottom: 'var(--space-2)',
              }}
            >
              Title (optional)
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isUploading}
              placeholder="Enter a title for your document"
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-accent)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-border)';
              }}
            />
          </div>

          {/* Description input */}
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <label
              htmlFor="description"
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 500,
                color: 'var(--color-text)',
                marginBottom: 'var(--space-2)',
              }}
            >
              Description (optional)
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isUploading}
              placeholder="Add a brief description"
              rows={3}
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: 'var(--color-bg)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                outline: 'none',
                resize: 'vertical',
                minHeight: '80px',
                transition: 'border-color 0.2s',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-accent)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--color-border)';
              }}
            />
          </div>

          {/* Error message */}
          {error && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-3)',
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-error)',
                borderRadius: 'var(--radius-md)',
                marginBottom: 'var(--space-5)',
              }}
            >
              <AlertCircle size={16} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: '13px',
                  color: 'var(--color-error)',
                }}
              >
                {error}
              </span>
            </div>
          )}

          {/* Upload progress */}
          {isUploading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                padding: 'var(--space-3)',
                background: 'var(--color-surface-2)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                marginBottom: 'var(--space-5)',
              }}
            >
              <Loader2
                size={16}
                style={{
                  color: 'var(--color-accent)',
                  animation: 'spin 1s linear infinite',
                }}
              />
              <span
                style={{
                  fontSize: '13px',
                  color: 'var(--color-text-muted)',
                }}
              >
                Processing your document...
              </span>
            </div>
          )}

          {/* Actions */}
          <div
            style={{
              display: 'flex',
              gap: 'var(--space-3)',
              justifyContent: 'flex-end',
            }}
          >
            <button
              onClick={handleClose}
              disabled={isUploading}
              style={{
                padding: 'var(--space-3) var(--space-5)',
                background: 'transparent',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                fontWeight: 500,
                cursor: isUploading ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => {
                if (!isUploading) {
                  e.currentTarget.style.background = 'var(--color-surface-2)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleUpload}
              disabled={!file || isUploading}
              style={{
                padding: 'var(--space-3) var(--space-5)',
                background:
                  file && !isUploading
                    ? 'var(--color-accent)'
                    : 'var(--color-surface-2)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color:
                  file && !isUploading
                    ? 'var(--color-text)'
                    : 'var(--color-text-muted)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                fontWeight: 500,
                cursor: file && !isUploading ? 'pointer' : 'not-allowed',
                transition: 'opacity 0.2s',
              }}
              onMouseEnter={(e) => {
                if (file && !isUploading) {
                  e.currentTarget.style.opacity = '0.9';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
            >
              Upload
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
