import { useEffect } from 'react';
import Sidebar from './components/layout/Sidebar';
import MainArea from './components/layout/MainArea';
import AuthScreen from './components/auth/AuthScreen';
import { useStore } from './store';
import { useDocuments } from './hooks/useDocuments';

function App() {
  const token = useStore((s) => s.token);

  // Show auth screen if not logged in
  if (!token) {
    return <AuthScreen />;
  }

  // User is authenticated, show main workspace
  return <AuthenticatedApp />;
}

function AuthenticatedApp() {
  const { createChat, chats } = useStore();

  // Load documents when user logs in
  useDocuments();

  // Create initial chat if none exists
  useEffect(() => {
    if (chats.length === 0) {
      createChat();
    }
  }, [chats.length, createChat]);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <MainArea />
    </div>
  );
}

export default App;
