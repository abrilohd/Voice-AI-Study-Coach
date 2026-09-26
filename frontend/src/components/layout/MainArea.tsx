import TopBar from './TopBar';
import MessagesArea from './MessagesArea';
import Composer from './Composer';

export default function MainArea() {
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
      <Composer />
    </main>
  );
}
