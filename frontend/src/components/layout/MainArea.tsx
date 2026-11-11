import TopBar from './TopBar';
import MessagesArea from './MessagesArea';
import Composer from './Composer';
import { useVoice } from '../../hooks/useVoice';
import { useStore } from '../../store';

export default function MainArea() {
  const setInput = useStore((state) => state.setPromptInput);

  // Initialize voice hook at parent level to share state
  // Only STT - no TTS functionality
  const voice = useVoice((transcribedText: string) => {
    setInput(transcribedText);
  });

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
      <TopBar />
      <MessagesArea />
      <Composer voiceHook={voice} />
    </main>
  );
}
