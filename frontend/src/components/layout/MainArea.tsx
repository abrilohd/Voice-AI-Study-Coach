import { useState, useRef, useEffect } from 'react';
import TopBar from './TopBar';
import MessagesArea from './MessagesArea';
import Composer from './Composer';
import { useVoice } from '../../hooks/useVoice';
import { useStore } from '../../store';

export default function MainArea() {
  const [isVoiceMode, setIsVoiceMode] = useState(false);
  const voiceEnabled = useStore((state) => state.voiceEnabled);
  const activeChat = useStore((state) => state.activeChat);
  const setInput = useStore((state) => state.setPromptInput);
  const lastAssistantContentRef = useRef<string>('');

  // Initialize voice hook at parent level to share state
  const voice = useVoice((transcribedText: string) => {
    setInput(transcribedText);
  });

  // Track the last assistant message content
  useEffect(() => {
    if (!activeChat) return;

    const lastMessage = activeChat.messages[activeChat.messages.length - 1];
    if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.isStreaming) {
      const content = lastMessage.content;
      
      // Only speak if this is new content and voice mode is active
      if (
        isVoiceMode &&
        voiceEnabled &&
        content &&
        content !== lastAssistantContentRef.current
      ) {
        lastAssistantContentRef.current = content;
        voice.speak(content);
        setIsVoiceMode(false); // Reset after speaking
      }
    }
  }, [activeChat?.messages, isVoiceMode, voiceEnabled]);

  return (
    <main
      style={{
        flex: 1,
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--color-bg)',
      }}
      className="md:ml-[260px]"
    >
      <TopBar isSpeaking={voice.isSpeaking} onStopSpeaking={voice.stopSpeaking} />
      <MessagesArea />
      <Composer onVoiceModeChange={setIsVoiceMode} voiceHook={voice} />
    </main>
  );
}
