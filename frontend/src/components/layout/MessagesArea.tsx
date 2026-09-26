import { useStore } from '../../store';
import EmptyState from './EmptyState';
import MessageList from '../chat/MessageList';

export default function MessagesArea() {
  const activeChat = useStore((state) => state.activeChat);
  const setPromptInput = useStore((state) => state.setPromptInput);

  const handlePromptClick = (prompt: string) => {
    setPromptInput(prompt);
    // Focus the textarea
    const textarea = document.querySelector('textarea');
    if (textarea) {
      textarea.focus();
    }
  };

  // Empty state when no active chat or no messages
  if (!activeChat || activeChat.messages.length === 0) {
    return <EmptyState onPromptClick={handlePromptClick} />;
  }

  return <MessageList />;
}
