import { useEffect } from 'react';
import { useStore } from '../store';
import { listDocuments } from '../lib/api';

/**
 * Hook to load documents on mount (when user logs in).
 * Documents are automatically loaded and stored in global state.
 */
export function useDocuments() {
  const { documents, setDocuments } = useStore();

  useEffect(() => {
    // Load documents on mount (user just logged in)
    listDocuments()
      .then(setDocuments)
      .catch((err) => {
        console.error('Failed to load documents:', err);
      });
  }, [setDocuments]);

  return documents;
}
